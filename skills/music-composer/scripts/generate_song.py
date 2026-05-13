#!/usr/bin/env python3
"""Generate a deterministic one-minute MIDI song from a title.

The generator intentionally enforces the first version of the composer protocol:
one stable genre/chord world, one main melody owner, supporting accompaniment,
and a resolving tonic ending.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import struct
from dataclasses import dataclass
from pathlib import Path
from random import Random
from typing import Iterable


PPQ = 480


NOTE_NAMES = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
MAJOR_SCALE = [0, 2, 4, 5, 7, 9, 11]
MINOR_SCALE = [0, 2, 3, 5, 7, 8, 10]


CHORD_QUALITIES = {
    "maj": [0, 4, 7],
    "min": [0, 3, 7],
    "maj7": [0, 4, 7, 11],
    "min7": [0, 3, 7, 10],
    "add9": [0, 4, 7, 14],
    "min9": [0, 3, 7, 10, 14],
    "sus2": [0, 2, 7],
    "sus4": [0, 5, 7],
    "dom7": [0, 4, 7, 10],
}


GM_PROGRAMS = {
    "acoustic grand piano": 0,
    "electric piano": 4,
    "music box": 10,
    "nylon guitar": 24,
    "steel guitar": 25,
    "fingered bass": 33,
    "synth bass": 38,
    "string ensemble": 48,
    "slow strings": 49,
    "choir pad": 52,
    "trumpet": 56,
    "alto sax": 65,
    "flute": 73,
    "lead synth": 80,
    "warm pad": 89,
    "new age pad": 88,
    "brightness": 100,
}


@dataclass(frozen=True)
class Chord:
    symbol: str
    root_offset: int
    quality: str


@dataclass(frozen=True)
class GenreProfile:
    name: str
    mode: str
    tempo_range: tuple[int, int]
    time_signature: tuple[int, int]
    progressions: tuple[tuple[Chord, ...], ...]
    lead_instruments: tuple[str, ...]
    support_instruments: tuple[str, ...]
    bass_instrument: str
    harmony_instrument: str
    uses_drums: bool


PROFILES = [
    GenreProfile(
        name="ambient web miniature",
        mode="major",
        tempo_range=(64, 78),
        time_signature=(4, 4),
        progressions=(
            (
                Chord("Iadd9", 0, "add9"),
                Chord("V6sus4", 7, "sus4"),
                Chord("vi7", 9, "min7"),
                Chord("IVmaj7", 5, "maj7"),
            ),
            (
                Chord("Imaj7", 0, "maj7"),
                Chord("ii7", 2, "min7"),
                Chord("vi7", 9, "min7"),
                Chord("Vsus4", 7, "sus4"),
            ),
        ),
        lead_instruments=("flute", "music box", "electric piano"),
        support_instruments=("new age pad", "warm pad"),
        bass_instrument="fingered bass",
        harmony_instrument="electric piano",
        uses_drums=False,
    ),
    GenreProfile(
        name="lo-fi room theme",
        mode="major",
        tempo_range=(72, 88),
        time_signature=(4, 4),
        progressions=(
            (
                Chord("Imaj7", 0, "maj7"),
                Chord("iii7", 4, "min7"),
                Chord("vi7", 9, "min7"),
                Chord("IVmaj7", 5, "maj7"),
            ),
            (
                Chord("Iadd9", 0, "add9"),
                Chord("vi7", 9, "min7"),
                Chord("ii7", 2, "min7"),
                Chord("V7", 7, "dom7"),
            ),
        ),
        lead_instruments=("electric piano", "flute", "alto sax"),
        support_instruments=("nylon guitar", "warm pad"),
        bass_instrument="fingered bass",
        harmony_instrument="electric piano",
        uses_drums=True,
    ),
    GenreProfile(
        name="synthwave postcard",
        mode="minor",
        tempo_range=(92, 112),
        time_signature=(4, 4),
        progressions=(
            (
                Chord("i", 0, "min"),
                Chord("bVI", 8, "maj"),
                Chord("bIII", 3, "maj"),
                Chord("bVII", 10, "maj"),
            ),
            (
                Chord("i", 0, "min"),
                Chord("iv", 5, "min"),
                Chord("bVI", 8, "maj"),
                Chord("V7", 7, "dom7"),
            ),
        ),
        lead_instruments=("lead synth", "brightness"),
        support_instruments=("warm pad", "new age pad"),
        bass_instrument="synth bass",
        harmony_instrument="warm pad",
        uses_drums=True,
    ),
    GenreProfile(
        name="chamber folk sketch",
        mode="major",
        tempo_range=(78, 94),
        time_signature=(3, 4),
        progressions=(
            (
                Chord("Iadd9", 0, "add9"),
                Chord("vi7", 9, "min7"),
                Chord("IVmaj7", 5, "maj7"),
                Chord("Vsus4", 7, "sus4"),
            ),
            (
                Chord("Imaj7", 0, "maj7"),
                Chord("IVmaj7", 5, "maj7"),
                Chord("ii7", 2, "min7"),
                Chord("V7", 7, "dom7"),
            ),
        ),
        lead_instruments=("flute", "steel guitar"),
        support_instruments=("nylon guitar", "slow strings"),
        bass_instrument="fingered bass",
        harmony_instrument="nylon guitar",
        uses_drums=False,
    ),
    GenreProfile(
        name="cinematic waltz",
        mode="minor",
        tempo_range=(84, 104),
        time_signature=(3, 4),
        progressions=(
            (
                Chord("i", 0, "min"),
                Chord("iv", 5, "min"),
                Chord("bVImaj7", 8, "maj7"),
                Chord("V7", 7, "dom7"),
            ),
            (
                Chord("i9", 0, "min9"),
                Chord("bVIIadd9", 10, "add9"),
                Chord("bVImaj7", 8, "maj7"),
                Chord("V7", 7, "dom7"),
            ),
        ),
        lead_instruments=("flute", "music box", "trumpet"),
        support_instruments=("slow strings", "choir pad"),
        bass_instrument="fingered bass",
        harmony_instrument="string ensemble",
        uses_drums=False,
    ),
]


TITLE_PROFILE_HINTS = {
    "ambient web miniature": {
        "air", "blue", "calm", "cloud", "garden", "glow", "home", "light", "moon", "ocean", "quiet", "sky",
    },
    "lo-fi room theme": {
        "bedroom", "coffee", "desk", "letter", "memory", "rain", "room", "soft", "tape", "window",
    },
    "synthwave postcard": {
        "city", "drive", "electric", "machine", "midnight", "neon", "night", "signal", "star", "street",
    },
    "chamber folk sketch": {
        "field", "forest", "hand", "harbor", "paper", "porch", "river", "thread", "wood",
    },
    "cinematic waltz": {
        "ghost", "mirror", "storm", "velvet", "winter", "waltz", "shadow", "silver",
    },
}


def stable_seed(title: str) -> int:
    digest = hashlib.sha256(title.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "untitled"


def choose_profile(title: str, rng: Random) -> GenreProfile:
    words = set(re.findall(r"[a-zA-Z]+", title.lower()))
    scores = []
    for profile in PROFILES:
        hints = TITLE_PROFILE_HINTS.get(profile.name, set())
        scores.append((len(words & hints), rng.random(), profile))
    scores.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return scores[0][2]


def choose_key(profile: GenreProfile, rng: Random) -> int:
    if profile.mode == "minor":
        candidates = [0, 2, 4, 5, 7, 9]
    else:
        candidates = [0, 2, 3, 5, 7, 8, 10]
    return rng.choice(candidates)


def note_name(semitone: int, mode: str) -> str:
    suffix = " minor" if mode == "minor" else " major"
    return NOTE_NAMES[semitone % 12] + suffix


def chord_notes(key: int, chord: Chord, octave: int) -> list[int]:
    root = 12 * (octave + 1) + key + chord.root_offset
    return [root + interval for interval in CHORD_QUALITIES[chord.quality]]


def scale_pitch(key: int, mode: str, degree: int, octave: int) -> int:
    scale = MINOR_SCALE if mode == "minor" else MAJOR_SCALE
    zero_based = degree - 1
    octave_offset = zero_based // len(scale)
    scale_index = zero_based % len(scale)
    return 12 * (octave + 1 + octave_offset) + key + scale[scale_index]


def vlq(value: int) -> bytes:
    buffer = value & 0x7F
    value >>= 7
    while value:
        buffer <<= 8
        buffer |= ((value & 0x7F) | 0x80)
        value >>= 7
    output = bytearray()
    while True:
        output.append(buffer & 0xFF)
        if buffer & 0x80:
            buffer >>= 8
        else:
            break
    return bytes(output)


class MidiTrack:
    def __init__(self) -> None:
        self.events: list[tuple[int, int, bytes]] = []
        self._order = 0

    def add(self, tick: int, data: bytes) -> None:
        self.events.append((tick, self._order, data))
        self._order += 1

    def note(self, channel: int, pitch: int, start: int, duration: int, velocity: int) -> None:
        self.add(start, bytes([0x90 | channel, pitch, velocity]))
        self.add(start + duration, bytes([0x80 | channel, pitch, 0]))

    def program(self, channel: int, program: int) -> None:
        self.add(0, bytes([0xC0 | channel, program]))

    def meta_text(self, text: str) -> None:
        payload = text.encode("utf-8")
        self.add(0, b"\xFF\x03" + vlq(len(payload)) + payload)

    def render(self) -> bytes:
        body = bytearray()
        last_tick = 0
        for tick, _, data in sorted(self.events, key=lambda item: (item[0], item[1])):
            body.extend(vlq(tick - last_tick))
            body.extend(data)
            last_tick = tick
        body.extend(vlq(0))
        body.extend(b"\xFF\x2F\x00")
        return b"MTrk" + struct.pack(">I", len(body)) + bytes(body)


def meta_track(title: str, tempo: int, time_signature: tuple[int, int]) -> MidiTrack:
    track = MidiTrack()
    track.meta_text(title)
    micros_per_quarter = int(60_000_000 / tempo)
    track.add(0, b"\xFF\x51\x03" + micros_per_quarter.to_bytes(3, "big"))
    numerator, denominator = time_signature
    denominator_power = int(math.log2(denominator))
    track.add(0, bytes([0xFF, 0x58, 0x04, numerator, denominator_power, 24, 8]))
    return track


def track_with_program(name: str, channel: int, instrument: str) -> MidiTrack:
    track = MidiTrack()
    track.meta_text(name)
    track.program(channel, GM_PROGRAMS[instrument])
    return track


def add_harmony(track: MidiTrack, channel: int, key: int, chords: list[Chord], bar_ticks: int, bars: int) -> None:
    for bar in range(bars):
        chord = chords[bar % len(chords)]
        if bar == bars - 1:
            chord = chords[-1]
        start = bar * bar_ticks
        duration = bar_ticks if bar == bars - 1 else int(bar_ticks * 0.92)
        for note in chord_notes(key, chord, 4):
            track.note(channel, note, start, duration, 52)


def add_bass(track: MidiTrack, channel: int, key: int, chords: list[Chord], bar_ticks: int, bars: int) -> None:
    for bar in range(bars):
        chord = chords[bar % len(chords)]
        if bar == bars - 1:
            chord = chords[-1]
        root = 12 * 3 + key + chord.root_offset
        fifth = root + 7
        start = bar * bar_ticks
        if bar == bars - 1:
            track.note(channel, root, start, bar_ticks, 74)
            continue
        track.note(channel, root, start, int(bar_ticks * 0.46), 76)
        track.note(channel, fifth, start + bar_ticks // 2, int(bar_ticks * 0.42), 60)


def add_support(track: MidiTrack, channel: int, key: int, chords: list[Chord], bar_ticks: int, bars: int) -> None:
    step = max(PPQ // 2, bar_ticks // 6)
    for bar in range(bars - 1):
        chord = chords[bar % len(chords)]
        tones = chord_notes(key, chord, 5)
        start = bar * bar_ticks
        for index, offset in enumerate(range(0, bar_ticks, step)):
            if index % 3 == 1:
                continue
            note = tones[index % len(tones)]
            track.note(channel, note, start + offset, int(step * 0.72), 42)


def add_drums(track: MidiTrack, bar_ticks: int, bars: int, time_signature: tuple[int, int]) -> None:
    numerator, denominator = time_signature
    beat_ticks = int(PPQ * 4 / denominator)
    for bar in range(bars - 1):
        start = bar * bar_ticks
        for beat in range(numerator):
            tick = start + beat * beat_ticks
            if beat == 0:
                track.note(9, 36, tick, PPQ // 8, 84)
            if numerator == 4 and beat in (1, 3):
                track.note(9, 38, tick, PPQ // 8, 62)
            if numerator == 3 and beat in (1, 2):
                track.note(9, 38, tick, PPQ // 10, 42)
            track.note(9, 42, tick, PPQ // 12, 36)
            if denominator == 4:
                track.note(9, 42, tick + beat_ticks // 2, PPQ // 12, 28)


def melody_degrees(rng: Random, mode: str) -> list[int]:
    if mode == "minor":
        starts = [[1, 3, 5, 4], [5, 6, 5, 3], [1, 2, 3, 5], [7, 6, 5, 3]]
    else:
        starts = [[1, 2, 3, 5], [3, 5, 6, 5], [5, 3, 2, 1], [6, 5, 3, 2]]
    motif = list(rng.choice(starts))
    if rng.random() > 0.5:
        motif[1], motif[2] = motif[2], motif[1]
    return motif


def add_main_melody(
    track: MidiTrack,
    channel: int,
    key: int,
    mode: str,
    bar_ticks: int,
    bars: int,
    time_signature: tuple[int, int],
    rng: Random,
) -> list[dict[str, int]]:
    motif = melody_degrees(rng, mode)
    numerator, denominator = time_signature
    beat_ticks = int(PPQ * 4 / denominator)
    melody_events = []
    for bar in range(bars):
        start = bar * bar_ticks
        if bar == bars - 1:
            degree = 1 if rng.random() > 0.25 else 3
            pitch = scale_pitch(key, mode, degree, 5)
            track.note(channel, pitch, start, bar_ticks, 82)
            melody_events.append({"bar": bar + 1, "degree": degree, "pitch": pitch, "start_tick": start})
            continue

        phrase = list(motif)
        if bar % 4 == 1:
            phrase = [min(7, degree + 1) for degree in motif]
        elif bar % 4 == 2:
            phrase = list(reversed(motif))
        elif bar % 4 == 3:
            phrase = motif[:2] + [1, 2 if mode == "minor" else 3]

        notes_this_bar = min(len(phrase), numerator if denominator == 4 else 3)
        for index in range(notes_this_bar):
            degree = phrase[index]
            pitch = scale_pitch(key, mode, degree, 5)
            offset = index * beat_ticks
            duration = int(beat_ticks * (0.78 if index < notes_this_bar - 1 else 1.35))
            track.note(channel, pitch, start + offset, min(duration, bar_ticks - offset), 86)
            melody_events.append({"bar": bar + 1, "degree": degree, "pitch": pitch, "start_tick": start + offset})
    return melody_events


def write_midi(path: Path, tracks: Iterable[MidiTrack]) -> None:
    rendered_tracks = [track.render() for track in tracks]
    header = b"MThd" + struct.pack(">IHHH", 6, 1, len(rendered_tracks), PPQ)
    path.write_bytes(header + b"".join(rendered_tracks))


def build_song(title: str, out_dir: Path) -> dict[str, object]:
    seed = stable_seed(title)
    rng = Random(seed)
    profile = choose_profile(title, rng)
    key = choose_key(profile, rng)
    tempo = rng.randint(*profile.tempo_range)
    time_signature = profile.time_signature
    numerator, denominator = time_signature
    bar_quarters = numerator * 4 / denominator
    seconds_per_bar = bar_quarters * 60 / tempo
    progression = list(rng.choice(profile.progressions))
    tonic_quality = "min9" if profile.mode == "minor" else "add9"
    resolving_chord = Chord("i9" if profile.mode == "minor" else "Iadd9", 0, tonic_quality)
    chords = progression + [resolving_chord]

    raw_bars = round(60 / seconds_per_bar)
    loop_size = len(progression)
    bars = max(loop_size * 2 + 1, round((raw_bars - 1) / loop_size) * loop_size + 1)
    duration_seconds = bars * seconds_per_bar
    if duration_seconds < 55:
        bars += loop_size
        duration_seconds = bars * seconds_per_bar
    elif duration_seconds > 65 and bars - loop_size >= loop_size * 2 + 1:
        shorter_bars = bars - loop_size
        shorter_duration = shorter_bars * seconds_per_bar
        if shorter_duration >= 55:
            bars = shorter_bars
            duration_seconds = shorter_duration
    if duration_seconds > 65:
        adjusted_tempo = math.ceil(tempo * duration_seconds / 65)
        if adjusted_tempo <= profile.tempo_range[1]:
            tempo = adjusted_tempo
            seconds_per_bar = bar_quarters * 60 / tempo
            duration_seconds = bars * seconds_per_bar
    bar_ticks = int(PPQ * bar_quarters)

    lead_pool = [
        instrument
        for instrument in profile.lead_instruments
        if instrument not in {profile.harmony_instrument, profile.bass_instrument}
    ]
    lead = rng.choice(lead_pool or profile.lead_instruments)
    occupied = {lead, profile.harmony_instrument, profile.bass_instrument}
    support_pool = [instrument for instrument in profile.support_instruments if instrument not in occupied]
    support = support_pool[0] if support_pool else profile.support_instruments[0]

    tracks = [meta_track(title, tempo, time_signature)]
    harmony = track_with_program("harmony", 0, profile.harmony_instrument)
    bass = track_with_program("bass", 1, profile.bass_instrument)
    lead_track = track_with_program("main melody", 2, lead)
    support_track = track_with_program("supporting figure", 3, support)
    add_harmony(harmony, 0, key, chords, bar_ticks, bars)
    add_bass(bass, 1, key, chords, bar_ticks, bars)
    melody_events = add_main_melody(lead_track, 2, key, profile.mode, bar_ticks, bars, time_signature, rng)
    add_support(support_track, 3, key, chords, bar_ticks, bars)
    tracks.extend([harmony, bass, lead_track, support_track])

    instruments = {
        "main_melody": lead,
        "harmony": profile.harmony_instrument,
        "bass": profile.bass_instrument,
        "supporting_figure": support,
    }
    if profile.uses_drums:
        drums = MidiTrack()
        drums.meta_text("drums")
        add_drums(drums, bar_ticks, bars, time_signature)
        tracks.append(drums)
        instruments["drums"] = "standard drum kit"

    out_dir.mkdir(parents=True, exist_ok=True)
    base = slugify(title)
    midi_path = out_dir / f"{base}.mid"
    manifest_path = out_dir / f"{base}.json"
    write_midi(midi_path, tracks)

    manifest = {
        "title": title,
        "seed": seed,
        "genre": profile.name,
        "tempo_bpm": tempo,
        "time_signature": f"{numerator}/{denominator}",
        "key": note_name(key, profile.mode),
        "duration_seconds": round(duration_seconds, 2),
        "bar_count": bars,
        "chords": [chord.symbol for chord in chords],
        "final_chord": resolving_chord.symbol,
        "resolution": "final bar uses tonic chord with root in bass",
        "instruments": instruments,
        "main_melody_owner": lead,
        "main_melody_policy": "Only the main melody track contains the primary melody; other tracks play harmony, bass, rhythm, or supporting figures.",
        "main_melody_events": melody_events[:16],
        "midi_file": str(midi_path),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a one-minute MIDI song from a title.")
    parser.add_argument("title", help="Song title to use as the deterministic composition seed.")
    parser.add_argument("--out", default="out", help="Output directory for MIDI and manifest files.")
    args = parser.parse_args()

    manifest = build_song(args.title, Path(args.out))
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
