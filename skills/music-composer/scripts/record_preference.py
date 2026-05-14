#!/usr/bin/env python3
"""Record simple user preference memory from generated song manifests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_MEMORY = {
    "liked_genres": [],
    "disliked_genres": [],
    "liked_instruments": [],
    "disliked_instruments": [],
    "notes": [],
    "rated_songs": [],
}


def load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return dict(DEFAULT_MEMORY)
    data = json.loads(path.read_text(encoding="utf-8"))
    merged = dict(DEFAULT_MEMORY)
    merged.update(data)
    return merged


def append_unique(values: list[str], value: str) -> None:
    if value and value not in values:
        values.append(value)


def main() -> None:
    parser = argparse.ArgumentParser(description="Record preference memory for music-composer.")
    parser.add_argument("manifest", type=Path, help="Generated song manifest JSON.")
    parser.add_argument("--memory", type=Path, default=Path.home() / ".hermes" / "music-composer-preferences.json")
    parser.add_argument("--rating", choices=["like", "dislike"], required=True)
    parser.add_argument("--note", default="")
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    memory = load(args.memory)
    genre = str(manifest.get("genre", ""))
    instruments = manifest.get("instruments", {})
    main_melody = str(instruments.get("main_melody", "")) if isinstance(instruments, dict) else ""

    if args.rating == "like":
        append_unique(memory["liked_genres"], genre)
        append_unique(memory["liked_instruments"], main_melody)
    else:
        append_unique(memory["disliked_genres"], genre)
        append_unique(memory["disliked_instruments"], main_melody)

    if args.note:
        memory["notes"].append(args.note)
    memory["rated_songs"].append(
        {
            "title": manifest.get("title"),
            "rating": args.rating,
            "genre": genre,
            "main_melody": main_melody,
            "quality_score": manifest.get("quality_score"),
            "note": args.note,
        }
    )

    args.memory.parent.mkdir(parents=True, exist_ok=True)
    args.memory.write_text(json.dumps(memory, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(memory, indent=2))


if __name__ == "__main__":
    main()
