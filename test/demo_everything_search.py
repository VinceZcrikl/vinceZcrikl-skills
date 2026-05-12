#!/usr/bin/env python3
"""
demo_everything_search.py — Real-world demo cases for the Everything search skill.

Run:  python test/demo_everything_search.py
      python test/demo_everything_search.py --case 3   # run a single case by number
"""

import argparse
import io
import pathlib
import sys

# Force UTF-8 output so box-drawing chars and non-ASCII filenames don't crash
# on Windows consoles that default to a legacy ANSI code page (cp936 / GBK).
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SKILL_ROOT = pathlib.Path(__file__).resolve().parent.parent / "skills" / "everything-search"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
import es_helper

# ── display helpers ───────────────────────────────────────────────────────────

RESET  = "\033[0m"
BOLD   = "\033[1m"
CYAN   = "\033[36m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
DIM    = "\033[2m"


def _color(text: str, code: str) -> str:
    return f"{code}{text}{RESET}" if sys.stdout.isatty() else text


def _header(title: str, query: str) -> None:
    print()
    print(_color(f"  {title}", BOLD + CYAN))
    print(_color(f"  Query: {query}", DIM))
    print("  " + "─" * 60)


def _print_results(result: dict, max_show: int = 8) -> None:
    if "error" in result:
        print(_color(f"  [error] {result['error']}: {result.get('message', '')}", YELLOW))
        return

    rows = result.get("results", [])
    total = result.get("total", 0)

    if not rows:
        print(_color("  (no results)", DIM))
        return

    for r in rows[:max_show]:
        size_col = f"{r['size_human']:>9}" if r.get("size_human") else " " * 9
        date_col = r.get("date_modified", "")[:16]
        name_col = _color(r["name"], GREEN)
        path_col = _color(r["path"], DIM)
        print(f"  {size_col}  {date_col}  {name_col}")
        print(f"           {' ' * 16}  {path_col}")

    shown = min(len(rows), max_show)
    if total > shown:
        print(_color(f"  … {total - shown} more (total {total})", DIM))
    else:
        print(_color(f"  {total} result(s)", DIM))


def _print_count(result: dict, label: str) -> None:
    if "error" in result:
        print(_color(f"  [error] {result['error']}", YELLOW))
    else:
        n = result.get("total", 0)
        print(f"  {_color(str(n), BOLD + GREEN)}  {label}")


# ── demo cases ────────────────────────────────────────────────────────────────

def case_01_recent_code_files(es):
    """Python / JS / TS files modified today — shows active development."""
    _header("Recent code files (modified today)", "ext:py;js;ts dm:today")
    result = es_helper.search_via_es(es, "ext:py;js;ts dm:today", 20, "date-modified", "desc")
    _print_results(result)


def case_02_large_video_files(es):
    """Large video files — useful for cleaning up disk space."""
    _header("Large video files (> 500 MB)", "ext:mp4;mkv;avi size:>500mb")
    result = es_helper.search_via_es(es, "ext:mp4;mkv;avi size:>500mb", 10, "size", "desc")
    _print_results(result)


def case_03_downloads_this_week(es):
    """Files landing in any Downloads folder this week."""
    _header("Downloads from this week", "path:Downloads\\ dm:thisweek")
    result = es_helper.search_via_es(es, "path:Downloads\\ dm:thisweek", 15, "date-modified", "desc")
    _print_results(result)


def case_04_project_config_files(es):
    """Config / manifest files — locate project roots instantly."""
    _header("Project config files", "ext:json;yaml;toml;ini file: size:<500kb")
    result = es_helper.search_via_es(es, "ext:json;yaml;toml;ini file: size:<500kb", 15, "date-modified", "desc")
    _print_results(result)


def case_05_log_files_today(es):
    """Log files written today — handy during debugging."""
    _header("Log files written today", "ext:log dm:today")
    result = es_helper.search_via_es(es, "ext:log dm:today", 10, "date-modified", "desc")
    _print_results(result)


def case_06_disk_hogs(es):
    """Largest files anywhere on the machine."""
    _header("Top disk hogs (> 1 GB)", "size:>1gb file:")
    result = es_helper.search_via_es(es, "size:>1gb file:", 10, "size", "desc")
    _print_results(result)


def case_07_empty_files(es):
    """Zero-byte files — often forgotten placeholders or failed writes."""
    _header("Empty (zero-byte) files", "size:empty file:")
    result = es_helper.search_via_es(es, "size:empty file:", 10, "name", "asc")
    _print_results(result)


def case_08_office_docs_last_month(es):
    """Word / Excel / PowerPoint files modified last month."""
    _header("Office documents (last month)", "ext:docx;xlsx;pptx dm:lastmonth")
    result = es_helper.search_via_es(es, "ext:docx;xlsx;pptx dm:lastmonth", 10, "date-modified", "desc")
    _print_results(result)


def case_09_node_modules_folders(es):
    """All node_modules folders — find JS projects or reclaim space."""
    _header("node_modules folders", "folder: node_modules")
    result = es_helper.search_via_es(es, "folder: node_modules", 10, "path", "asc")
    _print_results(result)


def case_10_exe_installers(es):
    """Executable installers sitting around."""
    _header("Executable installers (> 10 MB)", "ext:exe;msi size:>10mb")
    result = es_helper.search_via_es(es, "ext:exe;msi size:>10mb", 10, "size", "desc")
    _print_results(result)


def case_11_duplicate_names(es):
    """Files sharing a common generic name — often duplicates."""
    _header("Files named 'backup' or 'copy'", '"backup" | "copy" ext:zip;rar;7z')
    result = es_helper.search_via_es(es, '"backup" | "copy" ext:zip;rar;7z', 10, "date-modified", "desc")
    _print_results(result)


def case_12_count_by_extension(es):
    """Quick census — how many files of each common type exist."""
    _header("File count by extension (census)", "count queries")
    counts = [
        ("ext:py",          "Python files"),
        ("ext:js;ts;jsx;tsx", "JavaScript / TypeScript"),
        ("ext:mp4;mkv;avi", "Video files"),
        ("ext:jpg;jpeg;png;gif;webp", "Images"),
        ("ext:pdf",         "PDFs"),
        ("ext:zip;rar;7z",  "Archives"),
        ("ext:exe;msi",     "Executables"),
    ]
    for query, label in counts:
        r = es_helper.search_via_es(es, query, 1, "name", "asc", count_only=True)
        _print_count(r, label)


def case_13_git_repos(es):
    """Locate git repositories by finding .git folders."""
    _header("Git repositories (.git folders)", "folder: .git")
    result = es_helper.search_via_es(es, "folder: .git", 15, "path", "asc")
    _print_results(result)


def case_14_temp_files(es):
    """Leftover temp files that can usually be deleted."""
    _header("Temp / scratch files", "ext:tmp;bak;old;orig")
    result = es_helper.search_via_es(es, "ext:tmp;bak;old;orig", 10, "size", "desc")
    _print_results(result)


def case_15_screenshots(es):
    """Screenshots taken this month — quick access to recent captures."""
    _header("Screenshots this month", 'ext:png <screenshot | screen | capture | snip> dm:thismonth')
    result = es_helper.search_via_es(
        es, 'ext:png <screenshot | screen | capture | snip> dm:thismonth',
        10, "date-modified", "desc",
    )
    _print_results(result)


# ── runner ────────────────────────────────────────────────────────────────────

CASES = [
    case_01_recent_code_files,
    case_02_large_video_files,
    case_03_downloads_this_week,
    case_04_project_config_files,
    case_05_log_files_today,
    case_06_disk_hogs,
    case_07_empty_files,
    case_08_office_docs_last_month,
    case_09_node_modules_folders,
    case_10_exe_installers,
    case_11_duplicate_names,
    case_12_count_by_extension,
    case_13_git_repos,
    case_14_temp_files,
    case_15_screenshots,
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Everything search demo")
    parser.add_argument("--case", type=int, default=0,
                        help="Run a single case by number (1-based). Default: run all.")
    parser.add_argument("--es-path", help="Explicit path to es.exe")
    args = parser.parse_args()

    es = es_helper.find_es_exe(args.es_path)
    if es is None:
        print("es.exe not found. Make sure Everything is installed or es.exe is in skills/everything-search/bin/.")
        sys.exit(1)

    probe = es_helper.search_via_es(es, "ext:txt", 1, "name", "asc", count_only=True)
    if "error" in probe:
        print(f"Everything is not reachable: {probe['error']} — {probe.get('message', '')}")
        sys.exit(1)

    print(_color("\nEverything Search — Demo Cases", BOLD))
    print(_color(f"  es.exe : {es}", DIM))

    if args.case:
        idx = args.case - 1
        if idx < 0 or idx >= len(CASES):
            print(f"No case #{args.case}. Valid range: 1–{len(CASES)}.")
            sys.exit(1)
        CASES[idx](es)
    else:
        for fn in CASES:
            fn(es)

    print()


if __name__ == "__main__":
    main()
