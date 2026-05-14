# Bilingual Subtitle Layout

## Purpose

Use this reference when rendering bilingual subtitles for narrated videos, especially when the requirement is:
- one shared subtitle box
- two language layers
- no overlap
- stable layout across multiple subtitle iterations

## Stable default layout

Preferred visual grammar:

- one unified rounded subtitle card
- primary language line block on top
- secondary language line block below
- both centered in the same card
- consistent safe margin from the bottom edge
- semi-transparent dark background for readability

This layout is more robust than stacking two independent overlays near the bottom of the frame.

## Why one shared box works better

A shared bilingual card:
- prevents the two languages from drifting into each other
- makes visual hierarchy obvious
- simplifies spacing rules
- is easier to inspect frame by frame
- survives subtitle strategy changes better than independent overlays

## Text hierarchy

Recommended ordering:

1. Primary language
   - slightly larger
   - primary reading target
   - stronger weight

2. Secondary language
   - slightly smaller
   - secondary explanatory layer
   - looser line length control

Choose the actual language order according to the user's intent and audience. For Chinese-primary explainers, this usually means Chinese on top and English below.

## Layout rules

### Card-level rules
- use a single shared background card
- keep left/right padding symmetrical
- keep top/bottom padding sufficient so text never touches edges
- maintain a fixed maximum width rather than allowing full-width subtitles
- keep the card vertically compact enough to avoid blocking key visuals

### Primary-language block rules
- keep phrasing compact and natural
- allow balanced 1-2 lines when needed
- avoid excessively long literary sentences

### Secondary-language block rules
- rewrite for subtitle readability, not literal completeness
- prefer shorter spoken phrasing
- avoid one-word orphan lines
- split long beats before shrinking text too much

## Subtitle density strategy

When subtitles feel too intrusive, fix them in this order:

1. shorten each subtitle beat
2. split one long beat into multiple shorter beats
3. rewrite subtitle phrasing more tightly
4. reduce card height or margins slightly
5. reduce font size only if the above are insufficient

This preserves readability better than immediate font shrinking.

## Card generation strategy

When ffmpeg subtitle filters are unreliable or unavailable, use PNG cards.

Recommended approach:
1. generate one transparent PNG subtitle card per scene or subtitle beat
2. render both language layers inside that same card
3. overlay each card during its time window
4. verify a few timestamps after burn-in

Why this is robust:
- layout is deterministic
- typography is fully controlled
- easy to re-render only changed subtitle cards
- avoids `ass` / `drawtext` dependency issues

## Spoken text vs displayed text

Do not automatically reuse the TTS script as subtitle text.

Reason:
- pronunciation hacks may improve audio but look wrong on screen
- subtitle wording often needs to be shorter and more readable
- subtitle rhythm is not always the same as the spoken line

Keep separate sources:
- TTS source for pronunciation and timing
- subtitle manifest for visual display

## Timing granularity

There are two workable modes:

### Scene-level cards
Use when:
- the scene structure is already stable
- each scene has a clean, compact bilingual line pair
- speed of iteration matters more than fine-grained subtitle rhythm

### Multi-beat cards within a scene
Use when:
- subtitle obstruction is still too high
- one language needs shorter chunks
- the scene contains multiple distinct spoken ideas

## Quality checks

At several timestamps, confirm:
- the primary language is visually above the secondary language when that is the intended order
- both are inside one shared box
- no overlap or touching occurs between languages
- safe margins are preserved
- no text is clipped
- the subtitle card does not cover the most important screen content

Also check an especially problematic line manually, such as:
- a line with foreign product names
- a line with long phrasing
- a line likely to wrap awkwardly

## Common pitfalls

1. **Rendering the two languages as separate overlays**
   - often causes overlap or inconsistent spacing

2. **Letting subtitle text inherit TTS pronunciation spellings**
   - makes on-screen copy look unnatural

3. **Trying to solve obstruction only by shrinking fonts**
   - usually hurts readability more than it helps

4. **Ignoring orphan-wrap problems**
   - short dangling last lines make the card look sloppy

5. **Using a card width that is too wide**
   - subtitles become visually heavy and block more content

## Operating principle

For bilingual subtitle burn-ins, optimize for stable geometry first: one box, clear language hierarchy, controlled spacing, and short readable beats.
