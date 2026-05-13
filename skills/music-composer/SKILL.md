---
name: music-composer
description: Use when the user asks to write, compose, make, or generate a song as an actual MIDI/instrumental artifact rather than lyrics or a Suno prompt. Creates original MIDI songs, melodies, chord progressions, website music, game music, ambient loops, and short title-based compositions.
version: 1.1.0
author: lostviolinist
license: MIT
metadata:
  hermes:
    tags: [music, midi, composition, creative]
    category: creative
---

# Music Composer

## Overview

Create a short original MIDI composition from a title. The skill turns the title into a stable musical world: genre, tempo, time signature, key, chord progression, instruments, sectional form, and one main melody owner.

Use the bundled generator for the first artifact, then revise only within the same musical world unless the user asks for a different direction.

This skill is for producing a `.mid` file and manifest, not for writing lyrics or prompts for external music generators.

## When to Use

- The user asks Hermes to compose, generate, make, or write a song and appears to want an actual generated music file.
- The user wants MIDI music, website music, game music, short instrumental cues, ambient loops, or title-based compositions.
- The user provides a title and expects the agent to choose chords, meter, genre, and instruments.
- The user says "write me a song" and then clarifies they want a MIDI/instrumental composition rather than lyrics.

Do not use this skill for full audio model generation, lyric writing, playlist curation, or music theory explanation unless the user also wants a generated MIDI composition.

If the user only says "write me a song" and does not specify lyrics vs MIDI, ask one short clarification: "Do you want lyrics, or should I generate a MIDI instrumental?" If this skill was explicitly invoked with `/music-composer`, assume MIDI and proceed.

## Core Protocol

When making a song from scratch:

1. Ask the user for a title if they did not provide one.
   - If they gave only a broad theme such as "love", make a simple title from it, such as "Love, Lightly Held", and continue unless they asked to choose the title themselves.
2. Derive one stable musical world from the title:
   - chord progression
   - time signature
   - genre
   - tempo
   - key or mode
3. Choose instruments that fit the title, chords, and genre.
4. Keep the song close to 1 minute unless the user asks otherwise.
5. End on a resolving tonic chord.
6. Assign the main melody to exactly one instrument.
7. Let other instruments provide harmony, bass, rhythm, texture, or supporting responses. They may intertwine with the lead, but they must not double the main melody at the same time.
8. Prefer a miniature form: intro, A theme, B variation, A return, resolution.

## Default Workflow

1. Convert the title into 3-5 mood words.
2. Pick the genre and meter from those mood words.
3. Pick a chord progression before writing any melody.
4. Choose one lead instrument for the main melody.
5. Shape a motif through repetition, contrast, and return.
6. Add accompaniment in this order: harmony, bass, rhythm, texture.
7. Generate MIDI and a manifest using `scripts/generate_song.py`.
8. Check the manifest:
   - duration is roughly 60 seconds
   - form includes intro, A theme, B variation, A return, and resolution
   - final chord resolves to tonic
   - only one instrument owns `main_melody`
   - supporting instruments do not duplicate the main melody
9. Revise if the result feels cluttered, unresolved, or too generic.

## Tool Use

Generate a starter MIDI composition:

```bash
python3 "${HERMES_SKILL_DIR}/scripts/generate_song.py" "Title Goes Here" --out ./out
```

If `${HERMES_SKILL_DIR}` is unavailable, first locate this skill directory under `~/.hermes/skills/music-composer`.

The script writes:

- a `.mid` file
- a `.json` manifest describing title, genre, time signature, key, form, chords, instruments, duration, and melody ownership

For deeper composing guidance, read `references/composer-protocol.md`.

## Common Pitfalls

1. Do not let multiple instruments double the main melody. The manifest must have exactly one `main_melody_owner`.
2. Do not end on a dominant, suspended, or unresolved chord. The final chord should be tonic.
3. Do not switch genre or chord language midway through the piece.
4. Do not treat the generator output as only prose. Return the generated `.mid` path and manifest summary.

## Verification Checklist

- [ ] The song has a title.
- [ ] The generated duration is roughly 55-65 seconds.
- [ ] The manifest includes a clear miniature form.
- [ ] The final chord is tonic.
- [ ] Exactly one instrument owns the main melody.
- [ ] Supporting instruments play harmony, bass, rhythm, texture, or responses rather than the lead melody.
