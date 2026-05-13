---
name: music-composer
description: Use when creating original MIDI songs, chord progressions, short instrumental pieces, ambient loops, website music, game music, or agent-generated compositions from a title or short prompt.
version: 1.0.0
author: lostviolinist
license: MIT
metadata:
  hermes:
    tags: [music, midi, composition, creative]
    category: creative
---

# Music Composer

## Overview

Create a short original MIDI composition from a title. The skill turns the title into a stable musical world: genre, tempo, time signature, key, chord progression, instruments, and one main melody owner.

Use the bundled generator for the first artifact, then revise only within the same musical world unless the user asks for a different direction.

## When to Use

- The user asks Hermes to compose, generate, or make a song.
- The user wants MIDI music, website music, game music, short instrumental cues, ambient loops, or title-based compositions.
- The user provides a title and expects the agent to choose chords, meter, genre, and instruments.

Do not use this skill for full audio model generation, lyric writing, playlist curation, or music theory explanation unless the user also wants a generated MIDI composition.

## Core Protocol

When making a song from scratch:

1. Ask the user for a title if they did not provide one.
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

## Default Workflow

1. Convert the title into 3-5 mood words.
2. Pick the genre and meter from those mood words.
3. Pick a chord progression before writing any melody.
4. Choose one lead instrument for the main melody.
5. Add accompaniment in this order: harmony, bass, rhythm, texture.
6. Generate MIDI and a manifest using `scripts/generate_song.py`.
7. Check the manifest:
   - duration is roughly 60 seconds
   - final chord resolves to tonic
   - only one instrument owns `main_melody`
   - supporting instruments do not duplicate the main melody
8. Revise if the result feels cluttered, unresolved, or too generic.

## Tool Use

Generate a starter MIDI composition:

```bash
python3 "${HERMES_SKILL_DIR}/scripts/generate_song.py" "Title Goes Here" --out ./out
```

The script writes:

- a `.mid` file
- a `.json` manifest describing title, genre, time signature, key, chords, instruments, duration, and melody ownership

For deeper composing guidance, read `references/composer-protocol.md`.

## Common Pitfalls

1. Do not let multiple instruments double the main melody. The manifest must have exactly one `main_melody_owner`.
2. Do not end on a dominant, suspended, or unresolved chord. The final chord should be tonic.
3. Do not switch genre or chord language midway through the piece.
4. Do not treat the generator output as only prose. Return the generated `.mid` path and manifest summary.

## Verification Checklist

- [ ] The song has a title.
- [ ] The generated duration is roughly 55-65 seconds.
- [ ] The final chord is tonic.
- [ ] Exactly one instrument owns the main melody.
- [ ] Supporting instruments play harmony, bass, rhythm, texture, or responses rather than the lead melody.
