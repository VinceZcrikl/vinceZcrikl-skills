# Source Ingestion and Archival

## Purpose

Use this reference when the source for a bilingual video may come from many different content types and the archive target may vary.

The two key principles are:
- treat ingestion as source-agnostic
- treat archival as backend-pluggable

Do not hardcode one source type or one storage destination into the workflow.

## Supported source types

The workflow should accommodate at least these source classes:

- normal web articles
- documentation pages
- raw HTML pages
- X/Twitter posts and longform articles
- PDFs and other document-like study materials
- pasted text from the user
- mixed source bundles where text and images come separately

## Extraction strategy by source type

### Web pages and articles
Use standard extraction first. If it fails, switch to browser-based extraction.

Typical extracted fields:
- title
- author or site
- source URL
- published date when available
- cleaned body text
- key images

### HTML-heavy or blocked pages
Use browser-based fallback when:
- normal extraction is blocked
- DOM inspection is needed
- the visible page differs materially from the raw source

In that case, collect:
- visible text
- article-scoped content where possible
- image URLs
- screenshots only when needed for verification

### PDFs and study materials
Use PDF/document extraction tooling.

Collect:
- document title
- source file path or URL
- extracted text
- chapter or section structure
- figures or key assets if relevant

### User-pasted text
Normalize directly.

Collect:
- user-provided title or inferred title
- cleaned structure
- any links or references embedded in the pasted text

## Archive backend selection

The knowledge asset should be Markdown regardless of backend.

### Backend A — Obsidian vault
Choose this when:
- the user explicitly wants Obsidian
- the user already uses a known vault workflow
- wikilinks or vault categorization matter

### Backend B — Local Markdown directory
Choose this when:
- the user does not use Obsidian
- the user wants normal filesystem storage
- portability matters more than vault-specific features

The output should still be organized, for example:
- `notes/<topic>/<slug>.md`
- `notes/<topic>/assets/...`

### Backend C — No persistent write
Choose this when:
- the user only wants the video pipeline
- the archive would be temporary or unnecessary

Even in this mode, still structure the extracted content internally as if it were a Markdown knowledge note.

## Archive note requirements

A reusable archive note should include:
- source metadata
- concise summary
- interpretation or takeaways
- key points
- cleaned source body
- asset references when relevant

Recommended generic sections:
- `## Source Information`
- `## Summary`
- `## Interpretation`
- `## Key Points`
- `## Cleaned Source`

## Asset strategy

Use a deterministic asset folder near the Markdown file.

Recommended pattern:
- `assets/<note-slug>/...`

Rules:
- download only useful assets
- skip decorative images unless they matter to understanding
- avoid duplicate downloads across archive and video work when possible
- keep paths stable so later subtitle/video tooling can refer back to them

## Categorization guidance

Pick categories that remain understandable outside a specific app.

Good examples:
- `Articles/AI/`
- `Tutorials/Agents/`
- `Research/UI/`
- `Study/IELTS/`

Avoid backend-specific assumptions in the logical category model. The category scheme should work in both Obsidian and plain directories.

## Fallback principle

If one archival backend is unavailable, the workflow should degrade gracefully to another:
- Obsidian unavailable → local Markdown directory
- local write not requested → in-memory structured note for immediate video work

The video workflow must not depend on one note application.

## Common pitfalls

1. **Assuming every source is a normal article**
   - PDFs, HTML pages, and social posts often need different extraction logic

2. **Treating Obsidian features as mandatory**
   - wikilinks and vault paths are optional conveniences, not universal requirements

3. **Writing raw extraction output without editorial cleanup**
   - the archive should be reusable, not just dumped text

4. **Saving all available images blindly**
   - only keep assets that support later reading or video production

5. **Tying archive layout too tightly to one backend**
   - categories and filenames should survive backend changes

## Operating principle

Extract from any source, normalize into reusable Markdown knowledge, and write it to whichever archive backend the user actually wants.