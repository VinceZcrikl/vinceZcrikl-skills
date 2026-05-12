# everything-search

An Agent Skill powered by [Everything (voidtools)](https://www.voidtools.com) — instant file search for Windows. Find any file in milliseconds with natural language or Everything's full query syntax.

## Skill structure

This repository is a self-contained Agent Skill following the [Anthropic Agent Skills specification](https://docs.anthropic.com/en/agents-and-tools/agent-skills).

```
everything-search/
├── SKILL.md               # Skill definition (instructions + metadata)
├── LICENSE.txt
├── README.md
├── reference/
│   └── syntax.md          # Full Everything search syntax reference
├── scripts/
│   └── es_helper.py       # Search helper (Python, stdlib only)
└── bin/
    └── es.exe             # Bundled Everything CLI (MIT license)
```

**Loading levels:**
- `SKILL.md` frontmatter → always loaded (~100 tokens, skill discovery)
- `SKILL.md` body → loaded when user requests a file search
- `reference/syntax.md` + `scripts/es_helper.py` → loaded on demand as needed

## Prerequisites

| Requirement | Notes |
|---|---|
| Windows 10 / 11 | Everything is Windows-only |
| Python 3.8+ | Stdlib only, no pip required |

Everything itself is **bundled** — `bin/Everything.exe` is included in the skill. No separate
installation is required. If Everything is not running when you search, the skill launches it
automatically (appears as a tray icon) and retries.

### First-run notes

- Everything builds a file-system index on first launch. This takes a few seconds to a minute
  depending on drive size. Subsequent launches are instant.
- The tray icon remains until you quit it from the tray menu. This is normal — it keeps the
  index ready for fast searches.
- On x86 Windows (rare/legacy), the bundled x64 binary is incompatible. Pass `--auto-install`
  to download the matching x86 build instead.

## Installation

### Via plugin marketplace (recommended)

```
/plugin marketplace add VinceZcrikl/VinceZcrikl-skills
```

### Personal (available in all projects)

```bash
git clone https://github.com/VinceZcrikl/VinceZcrikl-skills.git "%USERPROFILE%\.claude\skills\VinceZcrikl-skills"
```

### Project (current project only)

```bash
git clone https://github.com/VinceZcrikl/VinceZcrikl-skills.git ".claude\skills\VinceZcrikl-skills"
```

### Via Skills API

Zip the `skills/everything-search` folder and upload it through the product's Skills API or settings UI.

## es.exe

`bin/es.exe` is the official Everything command-line interface, redistributed under the Everything MIT license (see [LICENSE.txt](LICENSE.txt)). No additional download is needed — it is bundled and ready to use.

## HTTP Server Fallback (Optional)

If `es.exe` is unavailable, the skill falls back to Everything's HTTP API:

1. Open Everything → **Tools → Options → HTTP Server**
2. Enable HTTP Server (default port: 80)
3. If using a custom port, pass `--http-port <port>` in the search command (see `SKILL.md` Step 3)

## Usage

Once installed, ask Claude in plain English — no special syntax needed.

| What you say | Everything query | Sort |
|---|---|---|
| **Development** | | |
| "Which Python files did I edit today?" | `ext:py dm:today` | `date-modified` desc |
| "Find all package.json files so I can see where my Node projects live." | `child:package.json` | `path` asc |
| "I have a `.env` file somewhere in my Workspace folder, where is it?" | `path:Workspace\ .env` | `name` asc |
| "List all git repos on my machine." | `folder: .git` | `path` asc |
| "Find all `.log` files written today inside my project." | `path:Workspace\ ext:log dm:today` | `date-modified` desc |
| "Show me TypeScript files larger than 100 KB." | `ext:ts size:>100kb` | `size` desc |
| **Documents** | | |
| "Find Word and Excel files I worked on last month." | `ext:docx;xlsx dm:lastmonth` | `date-modified` desc |
| "I downloaded a PDF about Kubernetes last year, find it." | `ext:pdf kubernetes path:Downloads\` | `date-modified` desc |
| "How many PDFs do I have in total?" | `ext:pdf` + `--count-only` | — |
| "Find all PowerPoint presentations modified this week." | `ext:pptx dm:thisweek` | `date-modified` desc |
| "Show me Markdown files in my notes folder." | `path:notes\ ext:md` | `name` asc |
| **Media & photos** | | |
| "Find all videos bigger than 500 MB." | `ext:mp4;mkv;avi size:>500mb` | `size` desc |
| "Which screenshots did I take this month?" | `ext:png <screenshot \| screen \| snip> dm:thismonth` | `date-modified` desc |
| "I shot footage on my Insta360 last week, find the raw files." | `ext:insv dm:lastweek path:Insta360\` | `date-modified` desc |
| "Find photos from last year's holiday trip." | `ext:jpg;jpeg dc:lastyear path:holiday` | `date-created` desc |
| "Show me all images in my project's assets folder." | `path:assets\ pic:` | `name` asc |

### Helper script flags

- `--max N` — result cap (default `20`)
- `--sort name|size|date-modified|date-created|path` — sort field (default `name`)
- `--order asc|desc` — sort direction. Defaults: `name`/`path` → asc, `size`/`date-*` → desc
- `--count-only` — return only `{total, query}`, useful as a cheap probe before picking `--max`
- `--http-port N` — Everything HTTP fallback port (default `80`)

## Troubleshooting

| Error | Solution |
|---|---|
| Everything is not running | Start Everything from the Start Menu or install from [voidtools.com](https://www.voidtools.com) |
| es.exe not found / HTTP unavailable | Verify the skill is installed at `~/.claude/skills/everything-search/` |
| IPC not ready | Wait ~10 seconds after starting Everything, then retry |
| HTTP API unavailable | Enable HTTP Server: Tools → Options → HTTP Server |
| Windows-only error | Everything does not run on macOS or Linux |

## License

MIT. See [LICENSE.txt](LICENSE.txt) for details, including third-party notices for Everything and PCRE.
