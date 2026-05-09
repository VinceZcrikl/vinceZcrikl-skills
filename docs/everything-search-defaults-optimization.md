# everything-search: Default Parameter Optimization

## Context

`es_helper.py` currently hard-codes `--max 50` and `--sort name` as defaults, and `SKILL.md` echoes those values verbatim. This causes two problems:

1. **Sort is not intent-aware.** When the user asks for "Python files modified this week," sorting alphabetically by name buries the most relevant result (the most recently modified file) somewhere in the middle.
2. **Result count lacks elasticity.** For lookup queries ("the file called `config.json`") 50 is far too many; for browsing queries ("all PDFs") 50 is far too few.

`es.exe` natively supports `-sort-ascending` / `-sort-descending`, and `SKILL.md` is the agent's decision surface. If we tell the agent *when* to pick *which* parameters, it can route by user intent instead of mechanically applying defaults.

## Plan

### 1. Script changes (`scripts/es_helper.py`)

**Add `--order asc|desc`** with sensible per-sort defaults:

| `--sort` | default `--order` | rationale |
|---|---|---|
| `name`, `path` | `asc` | alphabetical ordering is naturally ascending |
| `size` | `desc` | "largest first" is the common ask |
| `date-modified`, `date-created` | `desc` | "most recent first" is the common ask |

Implementation: when building `cmd`, append `-sort-ascending` or `-sort-descending` after `-sort <field>`. For the HTTP fallback, pass `sort_ascending=1` (or `0`) via the query string.

**Lower default `--max` from 50 to 20.** Most agent calls want a fast, focused answer. The existing `total` field in the JSON output already lets the agent detect truncation and decide whether to retry with a larger `--max`.

**Add `--count-only` mode.** Returns `{"total": N, "query": "..."}` only — no `results` list. The agent can use this as a cheap probe before committing to a `--max` for open-ended queries. `es.exe` exposes `-get-result-count`; the HTTP API supports `c=0` with `count=1`. Roughly 15 lines of code.

### 2. SKILL.md decision table

Insert an **intent → parameters** table immediately before Step 3, so the agent stops blindly applying defaults:

| User intent (signals) | `--sort` | `--order` | `--max` |
|---|---|---|---|
| "recent / today / this week / this month" `dm:` / `dc:` | `date-modified` | `desc` | 30 |
| "largest / smallest / over N MB" `size:` | `size` | `desc` (largest) / `asc` (smallest) | 30 |
| "the file called X / find a specific file" (concrete name) | `name` | `asc` | 10 |
| "all X / list X" (browsing) | `name` | `asc` | 50 |
| "duplicates" `dupe:` / `sizedupe:` | `size` | `desc` | 100 |
| Unclear / fallback | `name` | `asc` | 20 |

Add to Step 4: if `total > max * 5`, instruct the agent to either rerun with `--count-only` to gauge scale, or narrow filters before expanding `--max`.

### 3. Out of scope

- **No query auto-sniffing.** We will *not* parse the query string in the script to silently switch sort. Hidden magic is hard to debug; making the agent choose explicitly is more transparent.
- **No new dependencies.** Honor the README's "stdlib only" promise.
- **No JSON shape changes.** `{results, total, query, source}` and the error envelope stay stable so existing callers don't break.

## Files to modify

- [skills/everything-search/scripts/es_helper.py](../skills/everything-search/scripts/es_helper.py)
  - `search_via_es`: append `-sort-ascending` / `-sort-descending`; switch to `-get-result-count` when `count_only=True`.
  - `search_via_http`: forward `sort_ascending` and handle count-only via `c=0`.
  - `main`: register `--order` and `--count-only`; compute `--order` default from `--sort`; lower `--max` default to 20.
- [skills/everything-search/SKILL.md](../skills/everything-search/SKILL.md)
  - Insert intent-to-parameter decision table before Step 3.
  - Update example commands to demonstrate `--sort date-modified` and `--order` usage.
  - Add the `total > max * 5` guidance to Step 4.
- [skills/everything-search/README.md](../skills/everything-search/README.md)
  - Sync the Usage table with the new flags.

## Verification

On a Windows machine with Everything running:

```powershell
# 1. Default behavior — alphabetical, 20 results
python scripts\es_helper.py --query "ext:py"

# 2. Recency-first — newest Python files this week at the top
python scripts\es_helper.py --query "ext:py dm:thisweek" --sort date-modified

# 3. Explicit override — alphabetical descending
python scripts\es_helper.py --query "ext:py" --sort name --order desc

# 4. Count-only probe — only `total`, no `results`
python scripts\es_helper.py --query "ext:py" --count-only

# 5. HTTP fallback path — force es.exe miss, exercise sort/order via HTTP
python scripts\es_helper.py --query "ext:py" --sort size --order desc --es-path nonexistent.exe
```

Each call should emit JSON with the expected shape, correct ordering, and a `total` field present in every response (including `--count-only`).
