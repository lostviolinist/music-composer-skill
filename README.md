# OpenClaw Music Composer Skill

This repository contains an OpenClaw-compatible skill for generating short MIDI songs from a title.

The skill asks for or uses a title, chooses a genre, time signature, key, chords, instruments, and a single main melody owner, then generates a roughly one-minute MIDI file that ends on a resolving tonic chord.

## Install

```bash
git clone https://github.com/lostviolinist/music-composer-skill.git /tmp/music-composer-skill
mkdir -p ~/.openclaw/skills
cp -R /tmp/music-composer-skill ~/.openclaw/skills/music-composer
openclaw skills list
```

Then start a new OpenClaw session so the skill is loaded.

## Use

```text
Make a song titled Rain on the Desk.
```

The generator can also be run directly:

```bash
python3 ~/.openclaw/skills/music-composer/scripts/generate_song.py "Rain on the Desk" --out ./out
```

It writes a `.mid` file and a `.json` manifest describing the musical choices.
