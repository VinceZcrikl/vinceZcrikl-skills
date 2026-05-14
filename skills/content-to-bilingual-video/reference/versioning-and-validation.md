# Versioning and Validation

## Purpose

Use this reference during iterative video production, especially when voice fixes, subtitle revisions, and delivery-specific encodes create many near-duplicate files.

The goal is to make iteration history obvious and validation repeatable.

## Why versioning matters

In this workflow, a "new file" is often not cosmetic. It may represent:
- a pronunciation fix
- a regenerated scene narration
- a new merged audio track
- a subtitle layout change
- a delivery-specific encode
- a final faststart pass

Without explicit versioning, it becomes easy to burn subtitles onto the wrong intermediate or validate an outdated file.

## Recommended artifact stages

Use distinct names for distinct production stages.

Example pattern:

1. base visual export
2. voice-replaced intermediate
3. voice-fix iteration
4. subtitle-burned final
5. delivery-specific copy if needed

Example suffixes:
- `-cosyvoice2`
- `-fixedvoice`
- `-fixedvoice-v2`
- `-bilingual-stacked`
- `-telegram`

Name files so the most recent important production change is visible in the filename.

## Golden rule

Whenever you create a new voice-fixed intermediate, make every downstream script point to that newest intermediate before running subtitle burn-in or delivery export.

This avoids a common mistake:
- audio was fixed in `fixedvoice-v2`
- subtitle burn script still used `fixedvoice`
- final output silently contains old audio

## Recommended validation layers

Validation should happen in three layers.

### Layer 1: Container / encoding validation
Check:
- video codec
- audio codec
- resolution
- pixel format
- frame rate
- sample rate
- channel layout
- duration

Typical targets depend on delivery platform. For Telegram-friendly MP4, common targets are:
- H.264
- yuv420p
- AAC
- moov atom near the front

### Layer 2: Compatibility validation
Check:
- MP4 atom order
- faststart behavior
- whether the file should stream inline on the target platform
- whether a new mux step broke previous compatibility

### Layer 3: Content validation
Check actual content, not just metadata:
- correct audio track present
- expected pronunciation fix is audible
- subtitle layout matches latest design
- no black screen or visual corruption
- the user-reported issue is truly fixed

## Suggested verification points

For content validation, sample at least:
- one early timestamp
- one mid-video timestamp
- one timestamp tied to a known bug or fix

Examples of known-fix checks:
- a frame containing the corrected subtitle wording
- a scene where a term was previously mispronounced
- a spot where subtitle overlap used to occur

## What to record mentally for each version

For every iteration, know exactly:
- what changed
- what did not change
- which input file it was derived from
- whether it has been technically validated
- whether it has been visually or audibly spot-checked

If you cannot answer those five questions, the artifact naming is too vague.

## Minimal release checklist

Before presenting a file as the current best version, verify:
- it is derived from the newest intended intermediate
- audio is the intended voice version
- subtitles are the intended subtitle version
- encoding matches delivery constraints
- faststart is intact if required
- at least one known prior bug has been explicitly rechecked

## Common pitfalls

1. **Using `final` too early in filenames**
   - encourages accidental reuse after later fixes are made

2. **Versioning only subtitle changes and not voice changes**
   - hides the most important iteration dimension

3. **Validating only metadata**
   - a file can have correct codecs and still contain the wrong audio

4. **Checking random timestamps instead of bug-linked timestamps**
   - bug-specific verification is more valuable than generic sampling alone

5. **Reusing scripts with stale input paths**
   - one of the most common causes of false confidence in iterative media pipelines

## Operating principle

Every new artifact should make its production history legible, and every claimed fix should be validated at the exact point where it previously failed.
