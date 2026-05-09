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
| [Everything](https://www.voidtools.com) installed and running | Free, ~2 MB |
| Python 3.8+ | Stdlib only, no pip required |

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

Once installed, the AI agent automatically uses this skill when you ask to find files:

| Request | Translated query | Suggested sort |
|---|---|---|
| large PDF files modified this week | `ext:pdf size:large dm:thisweek` | `--sort date-modified` |
| Python files in the src folder | `path:src\ ext:py` | `--sort name` |
| videos bigger than 2GB on D drive | `video: size:>2gb path:D:\` | `--sort size` (desc) |
| folders named dist or build | `folder: dist \| folder: build` | `--sort name` |
| images created today | `pic: dc:today` | `--sort date-created` |

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
