# Everything Search Syntax Reference

## Boolean Operators

| Operator | Meaning | Example |
|---|---|---|
| space | AND (both must match) | `report pdf` |
| `\|` | OR | `cat \| dog` |
| `!` | NOT | `!tmp` |
| `< >` | Grouping | `<cat \| dog> ext:jpg` |
| `"..."` | Exact phrase | `"project report"` |

## Wildcards

| Pattern | Meaning | Example |
|---|---|---|
| `*` | Zero or more characters | `*.log` |
| `?` | Exactly one character | `file?.txt` |

## Scope Operators

| Operator | Meaning | Example |
|---|---|---|
| `ext:` | File extension(s), semicolon-separated | `ext:py;js;ts` |
| `noext:` | Files with no extension | `file: noext:` |
| `path:` | Match text in full path | `path:Downloads\` |
| `folder:` | Folders only | `folder: node_modules` |
| `file:` | Files only | `file: *.log` |
| `child:` | Folders containing this child | `child:package.json` |
| `parent:` | Files directly inside this path | `parent:C:\Projects` |

## Size Operators

Format: `size:<operator><value><unit>` where unit is `kb`, `mb`, or `gb` (default bytes).

| Example | Meaning |
|---|---|
| `size:>1mb` | Larger than 1 MB |
| `size:<100kb` | Smaller than 100 KB |
| `size:100kb..1gb` | Between 100 KB and 1 GB |
| `size:0` | Empty files |

Named sizes (shortcuts):

| Name | Range |
|---|---|
| `size:empty` | 0 bytes |
| `size:tiny` | 0–10 KB |
| `size:small` | 10–100 KB |
| `size:medium` | 100 KB–1 MB |
| `size:large` | 1–16 MB |
| `size:huge` | 16–128 MB |
| `size:gigantic` | > 128 MB |

## Date Operators

Three prefixes: `dm:` (date modified), `dc:` (date created), `da:` (date accessed).

**Constants:**

| Value | Meaning |
|---|---|
| `today` | Today |
| `yesterday` | Yesterday |
| `thisweek` | This week (Mon–Sun) |
| `lastweek` | Last week |
| `thismonth` | This calendar month |
| `lastmonth` | Last calendar month |
| `thisyear` | This calendar year |
| `lastyear` | Last calendar year |

**Specific dates:**

| Format | Example |
|---|---|
| `YYYY` | `dm:2025` |
| `YYYY/MM` | `dm:2025/12` |
| `YYYY/MM/DD` | `dm:2026/05/01` |
| Range | `dm:2026/01/01..2026/03/31` |

**Examples:**

```
dm:thisweek          # modified this week
dc:today             # created today
da:lastmonth         # accessed last month
dm:2026/01/01..2026/03/31   # modified in Q1 2026
```

## File Type Macros

These expand to common extensions automatically:

| Macro | Typical extensions |
|---|---|
| `pic:` | jpg jpeg png gif bmp tiff webp svg ico |
| `audio:` | mp3 wav flac aac ogg m4a wma |
| `video:` | mp4 mkv avi mov wmv flv webm m4v |
| `doc:` | doc docx pdf txt rtf odt xls xlsx ppt pptx |
| `zip:` | zip rar 7z tar gz bz2 xz |
| `exe:` | exe msi com bat cmd |

## Search Modifiers (prefix style)

These can be used as prefixes to change matching behavior for the term that follows:

| Modifier | Meaning |
|---|---|
| `case:` | Case-sensitive match |
| `nocase:` | Case-insensitive (default) |
| `regex:` | Enable PCRE regex |
| `noregex:` | Disable regex (default) |
| `wfn:` | Wildcard match filename only (not full path) |
| `path:` | Match in full path |
| `wholeword:` / `ww:` | Whole word match |
| `diacritics:` | Match diacritics exactly |

## Advanced Functions

| Function | Meaning | Example |
|---|---|---|
| `dupe:` | Files with duplicate filenames | `dupe:` |
| `sizedupe:` | Files with same size | `sizedupe:` |
| `empty:` | Empty folders | `folder: empty:` |
| `attrib:` | File attributes (R/H/S/A/D) | `attrib:H` |
| `runcount:>N` | Files opened N+ times | `runcount:>10` |
| `content:` | Full-text content search (IFilter) | `content:password ext:txt` |

## Practical Examples

| Goal | Query |
|---|---|
| PDFs modified this month | `ext:pdf dm:thismonth` |
| Large videos anywhere | `video: size:>500mb` |
| Python files in a project folder | `path:myproject\ ext:py` |
| Folders named dist or build | `folder: dist \| folder: build` |
| Files with no extension | `file: noext:` |
| Images created today | `pic: dc:today` |
| Regex: test files in TypeScript | `regex:.*test.*\.ts$` |
| Temp/junk files to clean | `ext:tmp;bak;log size:>10mb` |
| Recently modified large files | `size:>100mb dm:thisweek` |
| Duplicate filenames | `dupe: ext:jpg` |
| Empty folders | `folder: empty:` |
| Word documents from last year | `ext:docx dm:lastyear` |
| Files in Downloads not accessed this year | `path:Downloads\ !da:thisyear` |
| MP3s by size descending | `audio: ext:mp3` *(sort by size in command)* |
