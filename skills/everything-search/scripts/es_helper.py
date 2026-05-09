#!/usr/bin/env python3
"""
es_helper.py - Everything search helper for Claude Code skill.
Stdlib only. No pip dependencies required.

Usage:
  python3 es_helper.py --query "<query>" [--max 50] [--sort name] [--http-port 80]
"""

import argparse
import csv
import io
import json
import locale
import pathlib
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Dict, List, Optional, Tuple

SKILL_ROOT = pathlib.Path(__file__).resolve().parent.parent

ES_EXIT_CODES = {
    0: "success",
    1: "window_class_failed",
    2: "listening_window_failed",
    3: "out_of_memory",
    4: "missing_option",
    5: "export_failed",
    6: "unknown_switch",
    7: "ipc_failed",
    8: "not_running",
}

SORT_MAP = {
    "name": "name",
    "size": "size",
    "date-modified": "date-modified",
    "date-created": "date-created",
    "path": "path",
}


def find_es_exe(hint: Optional[str] = None) -> Optional[pathlib.Path]:
    """Find es.exe: explicit hint > skill bin/ > system PATH."""
    if hint:
        p = pathlib.Path(hint)
        if p.exists():
            return p

    bundled = SKILL_ROOT / "bin" / "es.exe"
    if bundled.exists():
        return bundled

    found = shutil.which("es") or shutil.which("es.exe")
    if found:
        return pathlib.Path(found)

    return None


def format_size(size_bytes: Optional[int]) -> str:
    if size_bytes is None:
        return ""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024 ** 3:
        return f"{size_bytes / 1024 ** 2:.1f} MB"
    return f"{size_bytes / 1024 ** 3:.2f} GB"


def parse_es_csv(raw: str) -> List[dict]:
    """Parse es.exe CSV output into normalized result dicts."""
    results = []
    reader = csv.DictReader(io.StringIO(raw))
    for row in reader:
        name = row.get("Filename") or row.get("Name") or ""
        path = row.get("Path") or ""
        size_str = row.get("Size") or ""
        date_mod = row.get("Date Modified") or row.get("Date modified") or ""

        try:
            size_bytes = int(size_str.replace(",", "")) if size_str.strip() else None
        except ValueError:
            size_bytes = None

        results.append({
            "name": name.strip(),
            "path": path.strip(),
            "size": size_bytes,
            "size_human": format_size(size_bytes),
            "date_modified": date_mod.strip(),
        })
    return results


def search_via_es(
    es_path: pathlib.Path,
    query: str,
    max_results: int,
    sort: str,
) -> dict:
    """Execute search using es.exe CLI."""
    cmd = [
        str(es_path),
        "-n", str(max_results),
        "-sort", SORT_MAP.get(sort, "name"),
        "-csv",
        "-name",
        "-path-column",
        "-size",
        "-date-modified",
        query,
    ]

    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=15)
        # es.exe outputs in the Windows ANSI code page (e.g. cp936/GBK on Chinese Windows)
        enc = locale.getpreferredencoding(False) or "utf-8"
        stdout_text = proc.stdout.decode(enc, errors="replace") if proc.stdout else ""
        stderr_text = proc.stderr.decode(enc, errors="replace") if proc.stderr else ""
        returncode = proc.returncode
    except subprocess.TimeoutExpired:
        return {"error": "ipc_failed", "message": "es.exe timed out after 15s.", "setup": ""}
    except FileNotFoundError:
        return {"error": "not_found", "message": f"es.exe not found at {es_path}", "setup": ""}

    if returncode == 8:
        return {
            "error": "not_running",
            "message": "Everything is not running.",
            "setup": "Start Everything from the Start Menu (or install from https://www.voidtools.com), then retry.",
        }
    if returncode == 7:
        return {
            "error": "ipc_failed",
            "message": "Everything IPC is not ready (error 7). Everything may still be loading.",
            "setup": "Wait a moment and retry. If the problem persists, restart Everything.",
        }
    if returncode != 0:
        return {
            "error": "es_error",
            "message": f"es.exe returned exit code {returncode} ({ES_EXIT_CODES.get(returncode, 'unknown')}).",
            "setup": stderr_text.strip(),
        }

    results = parse_es_csv(stdout_text)
    return {
        "results": results,
        "total": len(results),
        "query": query,
        "source": "es.exe",
    }


def search_via_http(query: str, max_results: int, ports: List[int]) -> dict:
    """Execute search using Everything HTTP API."""
    params = urllib.parse.urlencode({
        "s": query,
        "j": 1,
        "c": max_results,
        "path_column": 1,
        "size_column": 1,
        "date_modified_column": 1,
    })

    last_error = ""
    for port in ports:
        url = f"http://localhost:{port}/?{params}"
        try:
            with urllib.request.urlopen(url, timeout=3) as resp:
                raw = json.loads(resp.read().decode("utf-8", errors="replace"))
        except urllib.error.URLError as exc:
            last_error = str(exc.reason)
            continue
        except Exception as exc:
            last_error = str(exc)
            continue

        raw_results = raw.get("results", [])
        results = []
        for item in raw_results:
            size_bytes = item.get("size")
            try:
                size_bytes = int(size_bytes) if size_bytes is not None else None
            except (TypeError, ValueError):
                size_bytes = None

            results.append({
                "name": item.get("name", ""),
                "path": item.get("path", ""),
                "size": size_bytes,
                "size_human": format_size(size_bytes),
                "date_modified": item.get("date_modified", ""),
            })

        return {
            "results": results,
            "total": raw.get("totalResults", len(results)),
            "query": query,
            "source": f"http:{port}",
        }

    return {
        "error": "http_failed",
        "message": f"HTTP API unavailable on ports {ports}. Last error: {last_error}",
        "setup": (
            "Enable the Everything HTTP Server: "
            "Tools > Options > HTTP Server > Enable HTTP Server. "
            "Default port is 80; if you changed it, pass --http-port <port> to the search command."
        ),
    }


def _json_out(data: dict) -> None:
    """Write JSON to stdout, forcing UTF-8 on Windows to avoid GBK encode errors."""
    text = json.dumps(data, ensure_ascii=False)
    if hasattr(sys.stdout, "buffer"):
        sys.stdout.buffer.write((text + "\n").encode("utf-8"))
        sys.stdout.buffer.flush()
    else:
        print(text)


def main() -> None:
    parser = argparse.ArgumentParser(description="Search using Everything")
    parser.add_argument("--query", required=True, help="Everything search query")
    parser.add_argument("--max", type=int, default=50, help="Maximum results (default: 50)")
    parser.add_argument(
        "--sort",
        default="name",
        choices=list(SORT_MAP.keys()),
        help="Sort order (default: name)",
    )
    parser.add_argument("--es-path", help="Explicit path to es.exe")
    parser.add_argument("--http-port", type=int, default=80, help="Everything HTTP port (default: 80)")
    args = parser.parse_args()

    if sys.platform != "win32":
        _json_out({
            "error": "windows_only",
            "message": "Everything only runs on Windows. This skill cannot run on macOS/Linux.",
            "setup": "",
        })
        sys.exit(5)

    # Strategy 1: es.exe
    es_path = find_es_exe(args.es_path)
    if es_path:
        result = search_via_es(es_path, args.query, args.max, args.sort)
        if "error" not in result:
            _json_out(result)
            sys.exit(0)
        # Everything not running — HTTP won't work either
        if result["error"] == "not_running":
            _json_out(result)
            sys.exit(1)
        # IPC not ready or other es error — fall through to HTTP

    # Strategy 2: HTTP API (try configured port + 8080)
    ports = [args.http_port]
    if args.http_port != 8080:
        ports.append(8080)

    http_result = search_via_http(args.query, args.max, ports)
    if "error" not in http_result:
        _json_out(http_result)
        sys.exit(0)

    # Both failed
    if es_path is None:
        _json_out({
            "error": "not_found",
            "message": "es.exe not found in skill bin/ and not on system PATH. HTTP API also unavailable.",
            "setup": (
                "Option A (recommended): Ensure Everything is installed and running — "
                "es.exe is bundled in the skill's bin/ directory. "
                "Option B: Download es.exe from https://www.voidtools.com/support/everything/command_line_interface/ "
                "and place it in the skill's bin/ directory. "
                "Option C: Enable Everything HTTP Server (Tools > Options > HTTP Server)."
            ),
        })
        sys.exit(3)

    _json_out(http_result)
    sys.exit(4)


if __name__ == "__main__":
    main()
