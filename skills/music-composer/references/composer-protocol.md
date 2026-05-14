# Composer Protocol

## Title To Musical World

Treat the title as the seed for the whole song. The song should feel like it belongs to that title, not like a generic backing track.

Use these title cues:

- Soft, reflective, intimate words: ambient, chamber folk, lo-fi, major7/add9/sus chords, sparse drums.
- Bright, active, social words: indie pop, clean synth pop, 4/4, clear bass motion, simple memorable motif.
- Night, neon, machine, city words: synthwave, minor key, steady pulse, arpeggios, bright lead synth.
- Memory, rain, room, letter words: lo-fi, electric piano, gentle percussion, warm seventh chords.
- Ocean, sky, garden, light words: ambient web, slow harmonic rhythm, airy pads, add9 chords.
- Dance, fire, chase, launch words: faster tempo, stronger rhythm, simpler harmony.

## Song Constraints

- Target duration: 55-65 seconds.
- Always end with a tonic chord in the home key.
- Prefer a tiny but clear form: intro, A theme, B variation, A return, coda, resolution.
- Use one chord language throughout the song. Do not switch genre or harmonic vocabulary mid-song unless asked.
- Avoid too many instruments. Four to six instruments is usually enough.

## Quality Rules

- The main melody should grow from one small motif.
- Bring the motif back after a contrasting section so the listener recognizes it.
- Use smooth chord voicings rather than always stacking chords from root position.
- Vary velocities and timing slightly so the MIDI does not feel fully quantized.
- Let arrangement energy change by section: sparse intro, clear A theme, fuller B variation, recognizable return, cadential coda, calm ending.
- The four bars before the resolution should behave like a coda, not like another repeated loop.

## Critic Pass

After generation, run `scripts/critique_song.py` against the manifest. For higher quality, generate 3-5 candidates and keep the best-scoring one.

The critic checks:

- duration
- expected form
- tonic ending
- main melody ownership
- repetitive final pre-resolution bars

If the critic flags repetition before the resolution, revise the coda before delivering the MIDI.

## Supercharged Workflow

Use this loop for best results:

1. Generate 3-5 candidates.
2. Score each candidate with the deterministic critic and preference memory.
3. Keep the best candidate.
4. Inspect the `.composition.json` to understand motif, form, chords, and arrangement.
5. Render audio only if local tools are available.
6. When the user gives feedback, record it with `record_preference.py`.

This is the skill equivalent of fine-tuning: the model is not retrained, but examples, scoring, and preference memory change future outputs.

Use `references/song-recipes.json` as compact taste examples when the title is ambiguous.

## Conversational Feedback

The user should not have to run JSON commands. After delivering a song, ask:

```text
What did you think: 1-5, and what should I change next time?
```

Record their response with `record_preference.py --opinion`. If the opinion mentions flat chords, repetitive form, busy drums, sparse texture, good coda, or a liked lead instrument, the memory file should preserve those clues for future generations.

## Optional Listener Critic

If Hermes can render or inspect audio in the local environment, add a second model pass after WAV rendering:

- Does the title match the mood?
- Is there a memorable motif?
- Is the arrangement too dense?
- Does the coda make the ending feel earned?
- Does any section sound like filler?

Use that feedback to regenerate candidates or ask the user which direction to prefer.

## Melody Ownership

There is exactly one main melody owner.

Allowed:

- lead instrument plays the main motif
- bass plays roots, fifths, passing tones
- harmony instrument plays chords or arpeggios
- percussion plays beats
- support instrument plays short response phrases when the lead rests

Not allowed:

- two instruments playing the same main melody simultaneously
- accompaniment track shadowing the lead rhythm and pitches
- every instrument competing in the same register

## Resolving Endings

For the final bar:

- use the tonic chord
- put the root in the bass
- let the lead resolve to scale degree 1 or 3
- reduce rhythmic activity
- hold the final harmony long enough to feel finished

## Useful Chord Palettes

Intimate/personal:

- `Iadd9 - V6sus4 - vi7 - IVmaj7 - Iadd9`
- `i9 - bVImaj7 - bIIIadd9 - bVII - i9`

Lo-fi:

- `Imaj7 - iii7 - vi7 - IVmaj7 - Imaj7`
- `i7 - iv9 - bVIIadd9 - bIIImaj7 - i7`

Synthwave:

- `i - bVI - bIII - bVII - i`
- `i - iv - bVI - V7 - i`

Chamber folk:

- `Iadd9 - vi7 - IVmaj7 - Vsus4 - Iadd9`
- `i - bVIIadd9 - bVImaj7 - V7 - i`

Waltz/cinematic:

- `i - iv - bVI - V7 - i`
- `I - vi - ii - V7 - I`
