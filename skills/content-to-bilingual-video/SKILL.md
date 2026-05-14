---
name: content-to-bilingual-video
description: Use when turning any article or source document—web page, X/Twitter post, HTML page, PDF, or other extractable content—into a reusable Markdown knowledge asset and then into a polished bilingual explainer video with scene-wise narration, subtitle burn-in, and final delivery verification.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [content, article, html, pdf, markdown, video, bilingual-subtitles, workflow]
    related_skills: [obsidian, hyperframes, hermes-agent]
---

# Content to Bilingual Video

Use this skill when the user wants to turn source content into a reusable knowledge asset and then into a polished bilingual video.

If the user is writing in Chinese, respond in Chinese.

## Included references and templates

Load these references as needed:
- [reference/source-ingestion-and-archival.md](reference/source-ingestion-and-archival.md)
- [reference/scene-wise-tts-fitting.md](reference/scene-wise-tts-fitting.md)
- [reference/bilingual-subtitle-layout.md](reference/bilingual-subtitle-layout.md)
- [reference/versioning-and-validation.md](reference/versioning-and-validation.md)
- [reference/zh.md](reference/zh.md) for a Chinese operating guide and checklist

Start from these templates when building project artifacts:
- [templates/archive-note.md](templates/archive-note.md)
- [templates/scene-scripts.json](templates/scene-scripts.json)
- [templates/bilingual-subtitles-manifest.json](templates/bilingual-subtitles-manifest.json)

## Overview

This workflow is not just "make a video from an article". It is a multi-stage production pipeline with separate source-of-truth artifacts for:

1. source extraction
2. archive output
3. editorial structure
4. scene-wise narration
5. subtitle display
6. final delivery exports
7. technical validation

Treat these as linked but separate layers. Do not collapse them into one giant script or one opaque final render step.

## When to Use

Use this workflow when:
- the source may be a normal article, documentation page, HTML page, blog post, X/Twitter post, PDF, or other extractable document
- the user wants the source turned into a reusable note before or alongside video production
- the user wants a narrated explainer video rather than just a summary
- the output needs bilingual subtitles
- the project may require multiple rounds of voice, subtitle, or timing iteration
- the final output must be compatible with a specific delivery target such as Telegram

Do not use this workflow when:
- the user only wants extraction, translation, or archival but no video
- the user wants a quick one-shot TTS over static slides with no iteration
- the source is already a clean finished script and there is no need for extraction or knowledge packaging

## Supported source types

Treat the ingestion layer as source-agnostic. Typical inputs include:
- web articles and blogs
- documentation pages
- raw HTML pages
- X/Twitter posts or longform articles
- PDFs and study materials
- copied text blocks supplied directly by the user
- other sources that can be extracted into structured text plus optional media assets

Choose extraction tools based on the source:
- `web_extract` when it works cleanly
- browser-based extraction when the site blocks normal extraction or needs DOM inspection
- PDF/document extraction tools for PDFs and similar files
- direct text normalization when the user already pasted the content

## Archive backend must be pluggable

Do not hardcode Obsidian as the only archive target.

Treat archival as a pluggable backend with at least these modes:

### Mode A — Obsidian vault
Use when the user wants the result stored in Obsidian or already has a vault workflow.

### Mode B — Local Markdown directory
Use when the user does not use Obsidian or simply wants files saved to a normal local folder.

### Mode C — No archive write
Use when the user only wants the video pipeline and does not need persistent note storage.

The knowledge asset should still be represented as Markdown even when not using Obsidian.

If the user wants Obsidian archival, also load and follow the `obsidian` skill.

## Core output model

Treat the pipeline as five linked artifacts, not one file:

### 1. Source archive
- original source reference or file path
- extracted text
- downloaded or copied media assets when relevant
- structured Markdown knowledge note or archive

### 2. Editorial structure
- video thesis
- key arguments
- scene outline
- pacing decisions

### 3. Narration sources
- per-scene script JSON
- target durations per scene
- generated audio files per scene
- concatenated narration master

### 4. Subtitle sources
- bilingual subtitle manifest
- card images or subtitle render inputs
- explicit separation between spoken text and displayed text

### 5. Delivery exports
- voice-replaced intermediate MP4
- subtitle-burned final MP4
- validation artifacts and compatibility checks

## Workflow

### Phase 1 — Ingest the source

1. Capture the source type and location.
2. Extract:
   - title
   - author or source attribution if available
   - source URL or file path
   - full usable text
   - key images or media assets when relevant
3. If the normal extraction route fails, switch to a source-appropriate fallback.
4. Save media into a deterministic asset folder when needed.
5. Preserve enough source structure that the content remains useful later.

For general ingestion and archive-target selection, load [reference/source-ingestion-and-archival.md](reference/source-ingestion-and-archival.md).

### Phase 2 — Archive into a reusable Markdown knowledge asset

Create a structured Markdown note that includes:
- original metadata
- core summary
- interpretation / analysis
- key points
- cleaned source content
- embedded or linked important assets when needed

Recommended sections:
- `## Source Information`
- `## Summary`
- `## Interpretation`
- `## Key Points`
- `## Cleaned Source`

Important rule:
- the archive is not just a link dump or extracted blob; it must become a reusable knowledge asset

The write target must be backend-specific:
- Obsidian vault path if using Obsidian
- normal local directory if using plain Markdown storage
- skipped entirely if the user does not want persistence

### Phase 3 — Derive the video thesis

Before writing any scene scripts, extract the actual argument of the video.

Ask:
- what is the central claim?
- what tensions or comparisons make it interesting?
- what evidence or examples support it?
- what should the viewer remember at the end?

Turn the source into a compact video spine, for example:
- the initial advantage or promise
- where the approach starts breaking down
- what alternative becomes stronger and why
- what concrete evidence supports the shift
- what trade-offs remain
- the final conclusion

### Phase 4 — Break the video into scenes

Prefer scene-wise scripting instead of one monolithic narration.

Each scene should have:
- `id`
- `text`
- `target_duration`

Why this matters:
- easier audio fitting
- easier subtitle timing
- easier re-generation when one line is wrong
- easier sync against fixed visuals
- easier pronunciation fixes without redoing everything

A 6-10 scene structure is a good default for short explainers.

For detailed fitting guidance, load [reference/scene-wise-tts-fitting.md](reference/scene-wise-tts-fitting.md).

### Phase 5 — Generate scene-wise narration

Preferred approach:
- render each scene separately
- compare actual duration to target duration
- fit each scene individually
- concatenate fitted results into one master narration

Per-scene fitting strategy:
1. if a clip is shorter than target, pad with silence
2. if a clip is slightly longer, use mild `atempo`
3. if it is much longer, rewrite the script instead of crushing the audio

Scene-wise fitting is preferred because it preserves more natural phrasing, keeps pauses aligned with scene cuts, and makes versioned re-renders manageable.

If HyperFrames, subtitle burn-in, or local narration tooling are involved, also load and follow the `hyperframes` skill.

### Phase 6 — Replace audio first, before rerendering everything

After generating a new narration track, produce a voice-replaced intermediate MP4 before touching subtitle burn-in.

This gives a stable checkpoint:
- visuals remain unchanged
- encoding risk is lower
- pronunciation changes can be validated quickly
- subtitle work can target the latest audio-approved version

Recommended version naming pattern:
- base video
- `fixedvoice`
- `fixedvoice-v2`
- `fixedvoice-v3`

Use version names to reflect actual iteration history, especially when the spoken script changes.

For naming and validation discipline, load [reference/versioning-and-validation.md](reference/versioning-and-validation.md).

### Phase 7 — Separate speech from display text

Keep these logically separate:

1. **TTS script source**
   - optimized for pronunciation
   - may include phonetic hacks

2. **Subtitle / display manifest**
   - optimized for readability and visual consistency
   - should not inherit pronunciation hacks by accident

Important rule:
- only mirror phonetic spellings into subtitles if the user explicitly wants the display text changed too

### Phase 8 — Handle pronunciation fixes surgically

When a product term, foreign-language word, or branded term is mispronounced in narration:

1. locate the exact scene containing the problem
2. patch only that scene's spoken text
3. regenerate the affected narration outputs
4. rebuild the merged narration
5. update the voice-replaced MP4
6. only then reburn subtitles if needed

Always verify whether:
- only audio needs the change
- audio and subtitle text both need the change

### Phase 9 — Stabilize subtitles around one visual layout

If subtitle strategies keep changing, converge on one clear subtitle grammar.

For bilingual explainers, a robust default is:
- one unified subtitle box
- primary language on top
- secondary language below
- both centered within the same card
- no overlap between languages

Preferred rendering fallback when ffmpeg subtitle filters are unreliable:
1. generate transparent PNG subtitle cards
2. one card per scene or subtitle beat
3. overlay cards with ffmpeg
4. keep audio stream and MP4 compatibility under control

Why this works well:
- avoids missing `ass` or `drawtext` issues
- layout is visually deterministic
- easy to inspect frame by frame
- consistent across subtitle iterations

For layout rules and density tradeoffs, load [reference/bilingual-subtitle-layout.md](reference/bilingual-subtitle-layout.md).

### Phase 10 — Iterate subtitle density the right way

When the user says subtitles block too much of the screen, prefer these fixes in order:
1. shorten subtitle chunks
2. split long lines into more beats
3. simplify subtitle phrasing
4. reduce card height and margins
5. only then reduce font size if still necessary

Do not jump straight to tiny fonts.

### Phase 11 — Verify the final export technically

Always verify the final file after the last voice/subtitle change.

Check at least:
- codec
- resolution
- pixel format
- frame rate
- audio codec
- sample rate
- channel layout
- duration
- MP4 atom order / faststart

For Telegram-friendly MP4, confirm:
- H.264 video
- yuv420p
- AAC audio
- `moov` atom near the front

### Phase 12 — Verify content visually and aurally

Do not stop at container metadata.

Sample multiple timestamps, including:
- an early frame
- a mid-video frame
- a scene known to contain a fixed pronunciation or subtitle issue

Confirm:
- no black screen
- no visual drift
- no subtitle overlap
- bilingual box looks correct
- fixed text actually appears on screen
- regenerated voice matches the intended wording

### Phase 13 — Treat system failures as production blockers

If the workflow fails due to infrastructure problems, fix them as part of the pipeline.

Examples:
- file descriptor exhaustion
- WebUI/session database leaks
- browser session instability
- maxfiles limits too low

A broken orchestration environment is part of the video workflow if it blocks delivery.

## Common pitfalls

1. **Designing the workflow around only one source type**
   - the skill should work for articles, HTML pages, PDFs, and pasted text

2. **Hardcoding Obsidian as the only storage backend**
   - the archive target must be swappable

3. **Using one giant narration file as the only source of truth**
   - makes fixes expensive
   - scene-wise sources are far easier to patch

4. **Merging pronunciation fixes directly into display text without intent**
   - spoken and displayed text serve different purposes

5. **Reburning subtitles onto an older audio intermediate**
   - always ensure subtitle burn-in targets the newest voice-fixed MP4

6. **Trying to solve subtitle obstruction only by shrinking fonts**
   - rewrite and split first

7. **Overcompressing narration to fit the original duration**
   - leads to rushed, artifact-heavy speech
   - rewrite or extend timing instead

8. **Skipping final technical verification because the render succeeded**
   - successful render does not guarantee compatibility or correct content

## Verification checklist

- [ ] source text and assets were extracted with an appropriate toolchain
- [ ] the archive target was chosen correctly: Obsidian, local Markdown directory, or none
- [ ] a reusable Markdown knowledge asset exists when persistence was requested
- [ ] video thesis is clear and not just a copy of the source
- [ ] scene JSON exists with per-scene durations
- [ ] narration was generated per scene and fitted conservatively
- [ ] latest audio was merged into a checkpoint MP4
- [ ] subtitle manifest is distinct from TTS script source
- [ ] bilingual subtitles use one unified box with the intended language order
- [ ] pronunciation fixes were applied only where needed
- [ ] final MP4 metadata was checked
- [ ] faststart / atom order was checked when needed
- [ ] sample timestamps were visually inspected
- [ ] the specific user-reported issue was rechecked in the final export

## One-line summary

Extract flexibly, archive to a pluggable Markdown backend, structure the narrative, generate scene-wise narration, separate speech from display, stabilize subtitles into one shared bilingual box, then verify both media content and delivery compatibility.
