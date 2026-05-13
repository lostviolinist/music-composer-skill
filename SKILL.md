---
name: music_composer
description: Use when creating original MIDI songs, chord progressions, short instrumental pieces, ambient loops, website music, game music, or agent-generated compositions from a title or short prompt.
---

# Music Composer

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
python3 scripts/generate_song.py "Title Goes Here" --out ./out
```

The script writes:

- a `.mid` file
- a `.json` manifest describing title, genre, time signature, key, chords, instruments, duration, and melody ownership

For deeper composing guidance, read `references/composer-protocol.md`.
