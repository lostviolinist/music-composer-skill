#!/usr/bin/env python3
"""Generate a deterministic one-minute MIDI song from a title.

The generator enforces the composer protocol: one stable genre/chord world,
one main melody owner, supporting accompaniment, and a resolving tonic ending.
It also gives each song a tiny form so the result feels composed instead of
only looped.
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
from typing import Iterable, Optional


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


@dataclass(frozen=True)
class Section:
    name: str
    start_bar: int
    bar_count: int
    energy: float


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


def chord_for_bar(progression: list[Chord], resolving_chord: Chord, bar: int, bars: int) -> Chord:
    if bar == bars - 1:
        return resolving_chord
    return progression[bar % len(progression)]


def chord_voicing(key: int, chord: Chord, previous: Optional[list[int]] = None) -> list[int]:
    pitch_classes = []
    for note in chord_notes(key, chord, 3):
        pitch_class = note % 12
        if pitch_class not in pitch_classes:
            pitch_classes.append(pitch_class)

    if previous:
        targets = previous[: len(pitch_classes)]
        if len(targets) < len(pitch_classes):
            targets.extend([targets[-1] + 3] * (len(pitch_classes) - len(targets)))
    else:
        targets = [60 + index * 4 for index in range(len(pitch_classes))]

    voicing = []
    for pitch_class, target in zip(pitch_classes, targets):
        candidates = [pitch_class + 12 * octave for octave in range(3, 7)]
        candidates = [pitch for pitch in candidates if 52 <= pitch <= 79]
        voicing.append(min(candidates, key=lambda pitch: abs(pitch - target)))

    voicing.sort()
    return voicing


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
        start = max(0, start)
        duration = max(1, duration)
        velocity = max(1, min(127, velocity))
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


def make_sections(bars: int) -> list[Section]:
    intro = 2 if bars >= 17 else 1
    coda = 4 if bars >= 18 else 2
    resolution = 1
    body = max(8, bars - intro - coda - resolution)
    a_theme = min(8, max(4, body // 2))
    b_variation = min(6, max(3, (body - a_theme) // 2))
    a_return = body - a_theme - b_variation
    while a_return < 2 and a_theme > 4:
        a_theme -= 1
        a_return += 1
    while a_return < 2 and b_variation > 3:
        b_variation -= 1
        a_return += 1
    a_return = max(2, a_return)

    sections = [
        Section("intro", 0, intro, 0.55),
        Section("A theme", intro, a_theme, 0.9),
        Section("B variation", intro + a_theme, b_variation, 1.05),
        Section("A return", intro + a_theme + b_variation, a_return, 0.95),
        Section("coda", intro + a_theme + b_variation + a_return, coda, 0.62),
    ]
    used = sum(section.bar_count for section in sections)
    if used < bars - resolution:
        extra = bars - resolution - used
        a_return_section = sections[-2]
        coda_section = sections[-1]
        sections[-2] = Section(a_return_section.name, a_return_section.start_bar, a_return_section.bar_count + extra, a_return_section.energy)
        sections[-1] = Section(coda_section.name, coda_section.start_bar + extra, coda_section.bar_count, coda_section.energy)
    sections.append(Section("resolution", bars - resolution, resolution, 0.45))
    return sections


def section_for_bar(sections: list[Section], bar: int) -> Section:
    for section in sections:
        if section.start_bar <= bar < section.start_bar + section.bar_count:
            return section
    return sections[-1]


def humanized_note(
    track: MidiTrack,
    channel: int,
    pitch: int,
    start: int,
    duration: int,
    velocity: int,
    rng: Random,
    timing: int = 8,
    velocity_jitter: int = 5,
) -> None:
    track.note(
        channel,
        pitch,
        start + rng.randint(-timing, timing),
        duration + rng.randint(-timing, timing),
        velocity + rng.randint(-velocity_jitter, velocity_jitter),
    )


def add_harmony(
    track: MidiTrack,
    channel: int,
    key: int,
    progression: list[Chord],
    resolving_chord: Chord,
    bar_ticks: int,
    bars: int,
    sections: list[Section],
    rng: Random,
) -> None:
    previous_voicing = None
    for bar in range(bars):
        chord = chord_for_bar(progression, resolving_chord, bar, bars)
        section = section_for_bar(sections, bar)
        start = bar * bar_ticks
        duration = bar_ticks if bar == bars - 1 else int(bar_ticks * 0.92)
        voicing = chord_voicing(key, chord, previous_voicing)
        previous_voicing = voicing
        velocity = int(45 + section.energy * 12)
        for index, note in enumerate(voicing):
            strum = 0 if section.name == "resolution" else index * rng.randint(5, 14)
            humanized_note(track, channel, note, start + strum, duration, velocity, rng, timing=4)


def add_bass(
    track: MidiTrack,
    channel: int,
    key: int,
    progression: list[Chord],
    resolving_chord: Chord,
    bar_ticks: int,
    bars: int,
    sections: list[Section],
    rng: Random,
) -> None:
    for bar in range(bars):
        chord = chord_for_bar(progression, resolving_chord, bar, bars)
        section = section_for_bar(sections, bar)
        root = 12 * 3 + key + chord.root_offset
        fifth = root + 7
        octave = root + 12
        start = bar * bar_ticks
        if bar == bars - 1:
            track.note(channel, root, start, bar_ticks, 74)
            continue
        base_velocity = int(58 + section.energy * 18)
        humanized_note(track, channel, root, start, int(bar_ticks * 0.46), base_velocity, rng, timing=7)
        if section.name in {"B variation", "A return"}:
            humanized_note(track, channel, octave, start + bar_ticks // 4, int(bar_ticks * 0.18), 46, rng, timing=8)
        humanized_note(track, channel, fifth, start + bar_ticks // 2, int(bar_ticks * 0.42), 58, rng, timing=7)


def add_support(
    track: MidiTrack,
    channel: int,
    key: int,
    progression: list[Chord],
    resolving_chord: Chord,
    bar_ticks: int,
    bars: int,
    sections: list[Section],
    rng: Random,
) -> None:
    step = max(PPQ // 2, bar_ticks // 6)
    for bar in range(bars - 1):
        section = section_for_bar(sections, bar)
        if section.name == "intro" and bar % 2 == 0:
            continue
        chord = chord_for_bar(progression, resolving_chord, bar, bars)
        tones = chord_voicing(key, chord)
        tones = [note + 12 for note in tones if note + 12 <= 88]
        start = bar * bar_ticks
        for index, offset in enumerate(range(0, bar_ticks, step)):
            if index % 3 == 1 or (section.name == "A theme" and index % 4 == 3):
                continue
            if section.name == "coda" and index % 2 == 1:
                continue
            note = tones[index % len(tones)]
            velocity = 34 if section.name == "intro" else int(34 + section.energy * 10)
            humanized_note(track, channel, note, start + offset, int(step * 0.62), velocity, rng, timing=10)


def add_drums(
    track: MidiTrack,
    bar_ticks: int,
    bars: int,
    time_signature: tuple[int, int],
    sections: list[Section],
    rng: Random,
) -> None:
    numerator, denominator = time_signature
    beat_ticks = int(PPQ * 4 / denominator)
    for bar in range(bars - 1):
        section = section_for_bar(sections, bar)
        if section.name == "intro" and bar == 0:
            continue
        start = bar * bar_ticks
        for beat in range(numerator):
            tick = start + beat * beat_ticks
            kick_velocity = int(58 + section.energy * 24)
            hat_velocity = int(22 + section.energy * 18)
            if beat == 0:
                humanized_note(track, 9, 36, tick, PPQ // 8, kick_velocity, rng, timing=5)
            if numerator == 4 and beat in (1, 3):
                humanized_note(track, 9, 38, tick, PPQ // 8, 52, rng, timing=5)
            if numerator == 3 and beat in (1, 2):
                humanized_note(track, 9, 38, tick, PPQ // 10, 38, rng, timing=5)
            humanized_note(track, 9, 42, tick, PPQ // 12, hat_velocity, rng, timing=4)
            if denominator == 4 and section.name not in {"intro", "coda"}:
                humanized_note(track, 9, 42, tick + beat_ticks // 2, PPQ // 12, hat_velocity - 8, rng, timing=4)


def melody_degrees(rng: Random, mode: str) -> list[int]:
    if mode == "minor":
        starts = [[1, 3, 5, 4], [5, 6, 5, 3], [1, 2, 3, 5], [7, 6, 5, 3]]
    else:
        starts = [[1, 2, 3, 5], [3, 5, 6, 5], [5, 3, 2, 1], [6, 5, 3, 2]]
    motif = list(rng.choice(starts))
    if rng.random() > 0.5:
        motif[1], motif[2] = motif[2], motif[1]
    return motif


def phrase_for_section(motif: list[int], section: Section, local_bar: int, mode: str) -> list[int]:
    if section.name == "intro":
        return [] if local_bar == 0 else [motif[0], motif[-1]]
    if section.name == "B variation":
        contrast = [5, 6, 4, 2] if mode == "minor" else [6, 5, 3, 2]
        if local_bar % 2 == 1:
            return list(reversed(contrast))
        return contrast
    if section.name == "A return":
        if local_bar % 4 == 3:
            return motif[:2] + [2 if mode == "minor" else 3, 1]
        return motif if local_bar % 2 == 0 else [min(7, degree + 1) for degree in motif]
    if section.name == "coda":
        cadences = (
            [[5, 4, 3], [4, 3, 2], [3, 2, 1], [2, 1]]
            if mode == "major"
            else [[5, 4, 3], [6, 5, 4], [4, 2, 1], [7, 2, 1]]
        )
        return cadences[min(local_bar, len(cadences) - 1)]
    if local_bar % 4 == 1:
        return [min(7, degree + 1) for degree in motif]
    if local_bar % 4 == 2:
        return list(reversed(motif))
    if local_bar % 4 == 3:
        return motif[:2] + [1, 2 if mode == "minor" else 3]
    return motif


def add_main_melody(
    track: MidiTrack,
    channel: int,
    key: int,
    mode: str,
    bar_ticks: int,
    bars: int,
    time_signature: tuple[int, int],
    sections: list[Section],
    rng: Random,
) -> list[dict[str, object]]:
    motif = melody_degrees(rng, mode)
    numerator, denominator = time_signature
    beat_ticks = int(PPQ * 4 / denominator)
    melody_events = []
    for bar in range(bars):
        start = bar * bar_ticks
        section = section_for_bar(sections, bar)
        local_bar = bar - section.start_bar
        if bar == bars - 1:
            degree = 1 if rng.random() > 0.25 else 3
            pitch = scale_pitch(key, mode, degree, 5)
            track.note(channel, pitch, start, bar_ticks, 82)
            melody_events.append({"bar": bar + 1, "section": section.name, "degree": degree, "pitch": pitch, "start_tick": start})
            continue

        phrase = phrase_for_section(motif, section, local_bar, mode)
        if not phrase:
            continue

        notes_this_bar = min(len(phrase), numerator if denominator == 4 else 3)
        for index in range(notes_this_bar):
            degree = phrase[index]
            pitch = scale_pitch(key, mode, degree, 5)
            offset = index * beat_ticks
            duration = int(beat_ticks * (0.78 if index < notes_this_bar - 1 else 1.35))
            velocity = int(72 + section.energy * 14)
            humanized_note(track, channel, pitch, start + offset, min(duration, bar_ticks - offset), velocity, rng, timing=9)
            melody_events.append({"bar": bar + 1, "section": section.name, "degree": degree, "pitch": pitch, "start_tick": start + offset})
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
    sections = make_sections(bars)

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
    add_harmony(harmony, 0, key, progression, resolving_chord, bar_ticks, bars, sections, rng)
    add_bass(bass, 1, key, progression, resolving_chord, bar_ticks, bars, sections, rng)
    melody_events = add_main_melody(lead_track, 2, key, profile.mode, bar_ticks, bars, time_signature, sections, rng)
    add_support(support_track, 3, key, progression, resolving_chord, bar_ticks, bars, sections, rng)
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
        add_drums(drums, bar_ticks, bars, time_signature, sections, rng)
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
        "form": [
            {
                "name": section.name,
                "start_bar": section.start_bar + 1,
                "bar_count": section.bar_count,
                "energy": section.energy,
            }
            for section in sections
        ],
        "chords": [chord.symbol for chord in chords],
        "final_chord": resolving_chord.symbol,
        "resolution": "final bar uses tonic chord with root in bass",
        "instruments": instruments,
        "main_melody_owner": lead,
        "main_melody_policy": "Only the main melody track contains the primary melody; other tracks play harmony, bass, rhythm, or supporting figures.",
        "main_melody_events": melody_events,
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
