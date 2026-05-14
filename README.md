# Hermes Music Composer Skill

This repository contains a Hermes-compatible skill for generating short MIDI songs from a title. It is for actual MIDI/instrumental artifacts, not lyrics or Suno prompts.

The skill asks for or uses a title, chooses a genre, time signature, key, chords, sectional form, instruments, and a single main melody owner, then generates a roughly one-minute MIDI file that ends on a resolving tonic chord. It also includes multi-candidate generation, a composition JSON, a deterministic critic, optional WAV rendering, and conversational preference memory.

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

For reliable skill selection, invoke it directly:

```text
/music-composer Make a song titled Rain on the Desk.
```

Good prompts:

```text
/music-composer make a 1-minute MIDI song titled Rain on the Desk with 6 candidates
/music-composer make the chords stranger than last time
/music-composer make a gentler version and remember my feedback
```

If you ask Hermes "can you write me a song?" without naming this skill, Hermes may choose its bundled lyric/Suno songwriting skill instead. Ask for a MIDI song or use `/music-composer` when you want this generator.

The generator can also be run directly:

```bash
python3 ~/.hermes/skills/music-composer/scripts/generate_song.py "Rain on the Desk" --out ./out --candidates 3
```

It writes a `.mid` file, a `.json` manifest, and a `.composition.json` plan describing the musical choices, including the song form.

Critique a generated manifest:

```bash
python3 ~/.hermes/skills/music-composer/scripts/critique_song.py ./out/rain-on-the-desk.json
```

Record feedback:

```bash
python3 ~/.hermes/skills/music-composer/scripts/record_preference.py ./out/rain-on-the-desk.json --opinion "4/5, liked the sparse coda but wanted stranger chords"
```

In normal Hermes use, the agent should ask for your opinion after it generates a song and run this command for you.

## Research Harness

For skill improvement experiments:

```bash
python3 research/run_experiment.py --candidates 6 --label "baseline" --write-baseline
python3 research/run_experiment.py --candidates 6 --label "new-idea"
```

The harness evaluates a fixed title set, writes reports under `research/runs/`, and appends summaries to `research/experiments.jsonl`.
