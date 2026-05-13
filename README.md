# Hermes Music Composer Skill

This repository contains a Hermes-compatible skill for generating short MIDI songs from a title.

The skill asks for or uses a title, chooses a genre, time signature, key, chords, instruments, and a single main melody owner, then generates a roughly one-minute MIDI file that ends on a resolving tonic chord.

## Install

Install the individual skill directly:

```bash
hermes skills install lostviolinist/music-composer-skill/skills/music-composer
```

Or add this repo as a tap and install from it:

```bash
hermes skills tap add lostviolinist/music-composer-skill
hermes skills install lostviolinist/music-composer-skill/music-composer
```

Then start a new Hermes session so the skill is loaded.

## Use

```text
/music-composer Make a song titled Rain on the Desk.
```

The generator can also be run directly:

```bash
python3 ~/.hermes/skills/music-composer/scripts/generate_song.py "Rain on the Desk" --out ./out
```

It writes a `.mid` file and a `.json` manifest describing the musical choices.
