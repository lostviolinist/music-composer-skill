# Music Composer Autoresearch Program

You are improving the `music-composer` Hermes skill.

## Goal

Improve generated MIDI songs through small, measurable changes. Prefer changes that make songs feel less flat, more memorable, and more responsive to user feedback while preserving valid MIDI output.

## Loop

1. Make one focused change.
2. Run:

```bash
python3 research/run_experiment.py --candidates 6 --label "short-description"
```

3. Compare the result against `research/baselines/current.json` if it exists.
4. Keep the change only if:
   - aggregate score improves, or a targeted metric improves without major regression
   - no title fails validation
   - MIDI and manifest files are written
5. Log what changed and what metric moved.

## Allowed Edit Areas

- `skills/music-composer/scripts/generate_song.py`
- `skills/music-composer/scripts/critique_song.py`
- `skills/music-composer/references/composer-protocol.md`
- `skills/music-composer/references/song-recipes.json`
- research scoring scripts

## Metrics To Improve

- harmonic interest
- phrase variety
- coda strength
- melody contour
- genre/title fit
- preference alignment

## Guardrails

- Do not remove tonic resolution.
- Do not let multiple instruments own the main melody.
- Do not optimize only for the numeric score if the generated manifest becomes musically incoherent.
- Do not change the fixed eval titles casually; add separate stress tests instead.
