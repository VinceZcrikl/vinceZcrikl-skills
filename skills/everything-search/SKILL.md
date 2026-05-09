---
name: everything-search
description: '[Windows only] Search for files and folders instantly on Windows using Everything (voidtools). Use when the user wants to find files by name, extension, size, date, or path; navigate the filesystem; or identify what files exist in a location. Accepts natural language ("large PDFs modified this week") and raw Everything syntax (ext:pdf size:>1mb dm:thisweek). Searches complete in milliseconds regardless of drive size.'
---

# Everything File Search

Everything (voidtools) is a near-instant Windows file search engine that indexes the entire filesystem. This skill lets you search any file by name, type, size, date, or path in milliseconds.

## Quick start

Translate the user's request to Everything search syntax, then run the search:

```bash
python {skill_dir}/scripts/es_helper.py --query "ext:py dm:thisweek" --max 50
```

The script prints JSON to stdout. Parse it and format the results as a markdown table.

## Step 1 — Locate the skill directory

The helper script lives at `scripts/es_helper.py` relative to this SKILL.md file. Find the skill root:

```bash
python -c "import pathlib; matches = list(pathlib.Path.home().glob('.claude/skills/*/scripts/es_helper.py')) + list(pathlib.Path.home().glob('.claude/skills/*/skills/everything-search/scripts/es_helper.py')); print(matches[0].parent.parent if matches else '')"
```

Store the result as `SKILL_DIR`. If not found, also check `.claude/skills/VinceZcrikl-skills/skills/everything-search/` relative to the current project.

## Step 2 — Translate natural language to Everything syntax

If the query already contains Everything operators (`ext:`, `size:`, `dm:`, `path:`, `folder:`, `pic:`, etc.), use it as-is.

Otherwise translate using these rules:

| Natural language | Everything syntax |
|---|---|
| "PDF files" / "PDFs" | `ext:pdf` |
| "Word documents" | `ext:docx` |
| "images" / "pictures" | `pic:` |
| "videos" / "movies" | `video:` |
| "music" / "audio files" | `audio:` |
| "zip files" / "archives" | `zip:` |
| "executables" / "programs" | `exe:` |
| "files larger than X" | `size:>X` (kb/mb/gb) |
| "files smaller than X" | `size:<X` |
| "between X and Y in size" | `size:X..Y` |
| "modified today" | `dm:today` |
| "modified this week" | `dm:thisweek` |
| "modified this month" | `dm:thismonth` |
| "created today" | `dc:today` |
| "in [folder]" | `path:foldername\` |
| "folders named X" | `folder: X` |
| "folders only" | `folder:` |
| "on C drive" | `path:C:\` |

Combine conditions with space (AND). Use `|` for OR, `!` to exclude.

Tell the user the translated query before running: **Searching for: `<translated query>`**

For complex queries or unfamiliar operators, load [reference/syntax.md](reference/syntax.md) for the full reference.

## Step 3 — Run the search

```bash
python "{SKILL_DIR}/scripts/es_helper.py" --query "<translated_query>" --max 50 --sort name
```

Options:
- `--max N` — maximum results (default 50; increase if user asks for more)
- `--sort name|size|date-modified|date-created|path` — sort order
- `--http-port N` — Everything HTTP server port if not using default 80

## Step 4 — Present results

The script outputs JSON. On success:

```json
{
  "results": [
    {"name": "report.pdf", "path": "C:\\Users\\...", "size": 1048576, "size_human": "1.0 MB", "date_modified": "2026-05-01 14:32"}
  ],
  "total": 142,
  "query": "ext:pdf dm:thismonth",
  "source": "es.exe"
}
```

Format as a markdown table:

```
Found **N** result(s) for `<query>`:

| # | Name | Path | Size | Modified |
|---|------|------|------|----------|
| 1 | report.pdf | C:\Users\... | 1.0 MB | 2026-05-01 14:32 |
```

- If `total > 50` and results is full: add *"Showing top 50 of N. Use narrower filters to reduce results."*
- If `results` is empty: *"No files found matching `<query>`. Try broader terms or check the spelling."*

## Step 5 — Handle errors

| `error` field | Response |
|---|---|
| `not_running` | "Everything is not running. Start it from the Start Menu (or install from https://www.voidtools.com), then retry." |
| `not_found` | "es.exe is missing and the HTTP API is unavailable. See the README for setup instructions." |
| `ipc_failed` | "Everything's IPC is not ready. It may still be loading — wait a few seconds and retry." |
| `http_failed` | "HTTP API unavailable. Enable it in Everything: Tools → Options → HTTP Server." |
| `windows_only` | "Everything only runs on Windows. This skill cannot run on macOS or Linux." |

Always include the `setup` field from the error JSON as additional context.

## Implementation note — query tokenization

`es.exe` expects each search term and operator as a separate argv token. Passing
the full query string as one argument causes compound queries to silently return
zero results.

Inside `scripts/es_helper.py`, the query is split before building the command:

```python
query_args = shlex.split(query, posix=False)
cmd = [str(es_path), ..., *query_args]
```

Symptom of the bug: plain single-keyword searches work, but queries like
`meeting ext:zip` or `ext:pptx dm:lastmonth` return nothing.
