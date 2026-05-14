# Scene-Wise TTS Fitting

## Purpose

Use this reference when a narrated explainer video has fixed scene durations, but the generated speech does not naturally fit those timing windows.

The goal is not merely to force the narration to fit. The goal is to preserve natural phrasing while keeping scene boundaries, subtitle timing, and final video pacing stable.

## Why scene-wise fitting beats full-track compression

A single global narration track is fragile:
- one pronunciation fix forces regeneration of the whole file
- global time-stretching makes speech sound rushed
- pauses stop lining up with scene cuts
- verification becomes harder because one change affects everything

Scene-wise fitting is better because:
- each scene can be regenerated independently
- short clips can be padded with silence instead of stretched awkwardly
- only mildly long clips need compression
- scene boundaries remain interpretable and easy to debug

## Recommended source-of-truth files

Keep at least these files:

1. `scene_scripts.json`
   - scene id
   - spoken text
   - target duration

2. per-scene raw audio files
   - generated directly by the TTS engine

3. per-scene fitted audio files
   - padded or mildly time-compressed versions

4. merged narration master
   - concatenated fitted scenes

## Default fitting policy

For each scene:

1. Generate raw narration for the scene.
2. Measure actual duration.
3. Compare against target duration.
4. Choose one of the following:
   - **Shorter than target** → pad with silence
   - **Close to target** → keep as-is
   - **Slightly longer** → apply mild `atempo`
   - **Much longer** → rewrite the text instead of crushing the audio

## Practical thresholds

Use thresholds like these as a starting point:

- within ±3%: usually keep as-is
- short by more than ~0.15s: pad with silence
- long by up to ~1.10x to 1.20x: mild compression is usually acceptable
- long by ~1.20x to 1.30x: only accept after listening, preferably scene-wise
- beyond ~1.30x: rewrite the line, simplify wording, or allocate more time

These are not hard laws, but they are good operating defaults for Mandarin explainer narration.

## Strategy for lines that run too long

When a scene is too long, prefer these fixes in order:

1. remove redundant filler words
2. shorten examples
3. reduce parallel structure
4. replace formal wording with more spoken phrasing
5. only then apply mild audio compression

Bad fix:
- aggressive full-track atempo to force everything into the original timeline

Good fix:
- shorten just the overlong scene and regenerate that clip

## Pronunciation repairs

If a specific word is pronounced badly:

1. patch only the affected scene text
2. regenerate only that scene audio
3. re-fit that scene
4. rebuild the merged narration
5. replace the intermediate video audio
6. recheck the exact timestamp where the issue occurred

This is much faster and safer than rebuilding the entire voice pipeline blindly.

## Padding strategy

Silence padding is useful when a scene finishes early.

Benefits:
- preserves natural speaking rate
- keeps the next scene aligned
- avoids unnecessary stretching artifacts

Padding is especially useful when:
- the visual scene has deliberate dwell time
- the viewer needs a beat to read labels or screenshots
- the next transition should still happen on the original cut point

## Compression strategy

When compression is needed, keep it conservative.

Guidelines:
- prefer one mild adjustment over a strong one
- if chaining filters, keep each factor within ffmpeg limits
- listen to the result, do not trust the math alone
- for Chinese narration, overcompression is usually obvious to the ear

## Recommended QA loop

For every fitted scene, verify:
- spoken line matches intended script
- pacing still sounds human
- scene ends near the intended cut point
- no audible artifacting or jitter
- the line still supports readable subtitle chunking

After concatenation, verify:
- cumulative timing still lands correctly at later scenes
- transition points feel intentional
- the final master duration still matches the visual runtime plan

## Common pitfalls

1. **Using a global compression ratio derived from total duration**
   - this ignores where the real timing problems are

2. **Treating small overages as harmless everywhere**
   - several small drifts can accumulate into noticeable late-scene misalignment

3. **Not separating raw and fitted scene files**
   - makes iteration confusing and harder to debug

4. **Accepting ugly speech because the waveform duration is correct**
   - timing is not enough; naturalness matters

5. **Applying pronunciation hacks globally**
   - only patch the scenes that actually contain the issue

## Operating principle

Fit narration per scene, not per project. Preserve natural speech first, and only compress when the scene truly needs it.
