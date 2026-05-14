#!/usr/bin/env python3
"""Run a bounded research evaluation for the music-composer skill.

This borrows the autoresearch idea: fixed eval set, deterministic generation,
repeatable scoring, and JSONL experiment logs. It does not train a model; it
turns skill changes into comparable experiments.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import statistics
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
GENERATOR_PATH = ROOT / "skills" / "music-composer" / "scripts" / "generate_song.py"
CRITIC_PATH = ROOT / "skills" / "music-composer" / "scripts" / "critique_song.py"
EVAL_TITLES_PATH = ROOT / "research" / "eval_titles.json"
BASELINE_PATH = ROOT / "research" / "baselines" / "current.json"
LOG_PATH = ROOT / "research" / "experiments.jsonl"
RUNS_DIR = ROOT / "research" / "runs"


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_eval_titles(path: Path) -> list[dict[str, str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("eval_titles.json must contain a list")
    return data


def phrase_variety(manifest: dict[str, Any]) -> float:
    bars: dict[int, list[int]] = {}
    for event in manifest.get("main_melody_events", []):
        if not isinstance(event, dict):
            continue
        bar = int(event.get("bar", 0))
        degree = int(event.get("degree", 0))
        bars.setdefault(bar, []).append(degree)
    phrases = [tuple(value) for value in bars.values() if value]
    if not phrases:
        return 0.0
    return len(set(phrases)) / len(phrases)


def harmonic_interest(manifest: dict[str, Any]) -> int:
    chords = " ".join(str(chord) for chord in manifest.get("chords", []))
    markers = ["b", "#", "/", "dim", "V/", "iv9", "V7"]
    return min(20, sum(marker in chords for marker in markers) * 4)


def coda_score(manifest: dict[str, Any]) -> int:
    form = manifest.get("form", [])
    coda = next((section for section in form if section.get("name") == "coda"), None)
    resolution = next((section for section in form if section.get("name") == "resolution"), None)
    if not coda or not resolution:
        return 0
    score = 8
    if int(coda.get("bar_count", 0)) >= 4:
        score += 6
    resolution_bar = int(resolution.get("start_bar", 0))
    coda_events = [
        event for event in manifest.get("main_melody_events", [])
        if isinstance(event, dict) and event.get("section") == "coda"
    ]
    if coda_events and int(coda_events[-1].get("degree", 0)) in {1, 2, 3}:
        score += 6
    if resolution_bar and coda_events:
        final_coda_bar = int(coda_events[-1].get("bar", 0))
        if final_coda_bar == resolution_bar - 1:
            score += 4
    return min(24, score)


def melody_contour_score(manifest: dict[str, Any]) -> int:
    degrees = [
        int(event.get("degree", 0))
        for event in manifest.get("main_melody_events", [])
        if isinstance(event, dict) and event.get("degree")
    ]
    if not degrees:
        return 0
    melodic_range = max(degrees) - min(degrees)
    unique_degrees = len(set(degrees))
    score = 0
    if 3 <= melodic_range <= 6:
        score += 10
    if unique_degrees >= 5:
        score += 8
    if degrees[-1] in {1, 3}:
        score += 6
    return score


def composite_score(manifest: dict[str, Any], critic_result: dict[str, Any]) -> dict[str, Any]:
    findings = critic_result.get("findings") or []
    duration_finding = next((str(finding) for finding in findings if str(finding).startswith("Duration")), "")
    validity = 15 if duration_finding else 30
    harmonic = harmonic_interest(manifest)
    phrase = round(phrase_variety(manifest) * 20, 2)
    coda = coda_score(manifest)
    contour = melody_contour_score(manifest)
    internal = min(20, int(manifest.get("quality_score", 0)) / 5)
    total = round(validity + harmonic + phrase + coda + contour + internal, 2)
    return {
        "total": total,
        "validity": validity,
        "harmonic_interest": harmonic,
        "phrase_variety": phrase,
        "coda": coda,
        "melody_contour": contour,
        "internal_quality": internal,
    }


def summarize(results: list[dict[str, Any]]) -> dict[str, Any]:
    totals = [result["scores"]["total"] for result in results]
    strategies = Counter(result["manifest"].get("harmonic_strategy") for result in results)
    failures = [
        result for result in results
        if result["critic"].get("score", 0) < 80 or result["manifest"].get("final_chord") not in {"Iadd9", "i9"}
    ]
    metric_names = ["validity", "harmonic_interest", "phrase_variety", "coda", "melody_contour", "internal_quality"]
    metrics = {
        name: round(statistics.mean(result["scores"][name] for result in results), 2)
        for name in metric_names
    }
    return {
        "aggregate_score": round(statistics.mean(totals), 2),
        "min_score": round(min(totals), 2),
        "max_score": round(max(totals), 2),
        "metric_means": metrics,
        "harmonic_strategies": dict(strategies),
        "failure_count": len(failures),
    }


def compare_to_baseline(summary: dict[str, Any], baseline_path: Path) -> dict[str, Any] | None:
    if not baseline_path.exists():
        return None
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    baseline_summary = baseline.get("summary", baseline)
    delta = round(summary["aggregate_score"] - float(baseline_summary.get("aggregate_score", 0)), 2)
    metric_delta = {}
    for name, value in summary["metric_means"].items():
        old_value = baseline_summary.get("metric_means", {}).get(name, 0)
        metric_delta[name] = round(value - float(old_value), 2)
    return {
        "baseline_label": baseline.get("label"),
        "aggregate_delta": delta,
        "metric_delta": metric_delta,
        "improved": delta > 0 and summary["failure_count"] == 0,
    }


def compact_baseline(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "label": report["label"],
        "run_id": report["run_id"],
        "candidates": report["candidates"],
        "summary": report["summary"],
        "titles": [
            {
                "title": result["title"],
                "total": result["scores"]["total"],
                "harmonic_strategy": result["manifest"].get("harmonic_strategy"),
                "chords": result["manifest"].get("chords"),
                "critic_score": result["critic"].get("score"),
            }
            for result in report["results"]
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run music-composer research evaluation.")
    parser.add_argument("--candidates", type=int, default=6)
    parser.add_argument("--label", default="experiment")
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--preferences", type=Path, default=None)
    parser.add_argument("--write-baseline", action="store_true")
    parser.add_argument("--no-log", action="store_true")
    args = parser.parse_args()

    generator = load_module("music_composer_generator", GENERATOR_PATH)
    critic = load_module("music_composer_critic", CRITIC_PATH)
    eval_titles = load_eval_titles(EVAL_TITLES_PATH)
    run_id = time.strftime("%Y%m%d-%H%M%S")
    out_dir = args.out or (RUNS_DIR / f"{run_id}-{args.label.replace(' ', '-')}")
    out_dir.mkdir(parents=True, exist_ok=True)
    preferences = generator.load_preferences(args.preferences)

    results = []
    for item in eval_titles:
        title = item["title"]
        manifest = generator.generate_best_song(title, out_dir / generator.slugify(title), args.candidates, preferences=preferences)
        critic_result = critic.critique(manifest)
        scores = composite_score(manifest, critic_result)
        results.append(
            {
                "title": title,
                "target": item.get("target", ""),
                "manifest_file": manifest["midi_file"].replace(".mid", ".json"),
                "composition_file": manifest.get("composition_file"),
                "midi_file": manifest.get("midi_file"),
                "manifest": manifest,
                "critic": critic_result,
                "scores": scores,
            }
        )

    summary = summarize(results)
    comparison = compare_to_baseline(summary, BASELINE_PATH)
    report = {
        "label": args.label,
        "run_id": run_id,
        "candidates": args.candidates,
        "summary": summary,
        "comparison": comparison,
        "results": results,
    }

    report_path = out_dir / "report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    if args.write_baseline:
        BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
        BASELINE_PATH.write_text(json.dumps(compact_baseline(report), indent=2) + "\n", encoding="utf-8")

    if not args.no_log:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({
                "label": args.label,
                "run_id": run_id,
                "report_path": str(report_path),
                "summary": summary,
                "comparison": comparison,
            }) + "\n")

    print(json.dumps({
        "report_path": str(report_path),
        "summary": summary,
        "comparison": comparison,
    }, indent=2))


if __name__ == "__main__":
    main()
