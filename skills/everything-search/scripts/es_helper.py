#!/usr/bin/env python3
"""
es_helper.py - Everything search helper for Claude Code skill.
Stdlib only. No pip dependencies required.

Usage:
  python3 es_helper.py --query "<query>" [--max 30] [--sort name]
                       [--order asc|desc] [--count-only] [--http-port 80]
"""

import argparse
import csv
import io
import json
import locale
import pathlib
import platform
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from typing import Dict, List, Optional, Tuple

SKILL_ROOT = pathlib.Path(__file__).resolve().parent.parent

EVERYTHING_VERSION = "1.4.1.1026"
EVERYTHING_PORTABLE_URLS: Dict[str, str] = {
    "AMD64": f"https://www.voidtools.com/Everything-{EVERYTHING_VERSION}.x64.zip",
    "x86":   f"https://www.voidtools.com/Everything-{EVERYTHING_VERSION}.x86.zip",
    # ARM64 native build not yet widely available; fall back to x64
    "ARM64": f"https://www.voidtools.com/Everything-{EVERYTHING_VERSION}.x64.zip",
}

EVERYTHING_COMMON_PATHS = [
    pathlib.Path(r"C:\Program Files\Everything\Everything.exe"),
    pathlib.Path(r"C:\Program Files (x86)\Everything\Everything.exe"),
]

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

# Default sort direction per field — picked to match the most common intent
# (largest/newest first, names alphabetical).
DEFAULT_ORDER = {
    "name": "asc",
    "path": "asc",
    "size": "desc",
    "date-modified": "desc",
    "date-created": "desc",
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


def find_everything_exe() -> Optional[pathlib.Path]:
    """Locate Everything.exe: skill bin/ > common install paths > PATH > registry."""
    bundled = SKILL_ROOT / "bin" / "Everything.exe"
    if bundled.exists():
        return bundled

    for p in EVERYTHING_COMMON_PATHS:
        if p.exists():
            return p

    found = shutil.which("Everything") or shutil.which("Everything.exe")
    if found:
        return pathlib.Path(found)

    try:
        import winreg
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            try:
                with winreg.OpenKey(hive, r"Software\voidtools\Everything") as key:
                    install_dir, _ = winreg.QueryValueEx(key, "install_dir")
                    candidate = pathlib.Path(install_dir) / "Everything.exe"
                    if candidate.exists():
                        return candidate
            except OSError:
                pass
    except ImportError:
        pass

    return None


def download_portable(dest_dir: pathlib.Path) -> pathlib.Path:
    """Download the portable Everything ZIP and extract Everything.exe into dest_dir."""
    arch = platform.machine()
    url = EVERYTHING_PORTABLE_URLS.get(arch, EVERYTHING_PORTABLE_URLS["AMD64"])

    print(f"Downloading Everything {EVERYTHING_VERSION} ({arch}) from {url} ...", file=sys.stderr)

    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp_path = pathlib.Path(tmp.name)

    try:
        def _report(block_count: int, block_size: int, total: int) -> None:
            downloaded = block_count * block_size
            if total > 0:
                pct = min(downloaded * 100 // total, 100)
                print(f"\r  {pct}% ({downloaded // 1024} KB / {total // 1024} KB)", end="", file=sys.stderr)

        urllib.request.urlretrieve(url, tmp_path, reporthook=_report)
        print(file=sys.stderr)  # newline after progress
    except Exception as exc:
        tmp_path.unlink(missing_ok=True)
        raise RuntimeError(f"Download failed: {exc}") from exc

    dest_dir.mkdir(parents=True, exist_ok=True)
    exe_dest = dest_dir / "Everything.exe"

    try:
        with zipfile.ZipFile(tmp_path) as zf:
            names = zf.namelist()
            exe_name = next((n for n in names if n.lower().endswith("everything.exe")), None)
            if exe_name is None:
                raise RuntimeError(f"Everything.exe not found in ZIP. Contents: {names}")
            with zf.open(exe_name) as src, open(exe_dest, "wb") as dst:
                shutil.copyfileobj(src, dst)
    finally:
        tmp_path.unlink(missing_ok=True)

    if not exe_dest.exists():
        raise RuntimeError(f"Extraction finished but {exe_dest} is missing.")

    print(f"Extracted to {exe_dest}", file=sys.stderr)
    return exe_dest


def is_everything_running() -> bool:
    """Return True if at least one Everything.exe process is running."""
    try:
        out = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq Everything.exe", "/NH"],
            capture_output=True, timeout=5,
        ).stdout
        return b"Everything.exe" in out
    except Exception:
        return False


def is_ipc_ready(es_path: pathlib.Path) -> bool:
    """Quick probe: return True if es.exe can reach Everything's IPC right now."""
    try:
        result = subprocess.run(
            [str(es_path), "-get-result-count"],
            capture_output=True,
            timeout=3,
        )
        return result.returncode == 0
    except Exception:
        return False


def _db_is_corrupt(db_path: pathlib.Path) -> bool:
    """Return True if the Everything.db looks corrupted (too small to be valid)."""
    try:
        return db_path.exists() and db_path.stat().st_size < 1024
    except OSError:
        return False


def launch_everything(exe_path: pathlib.Path) -> Optional[subprocess.Popen]:
    """Start Everything in the background (minimized to tray).

    Returns the Popen object on success, None on failure.
    Note: -disable-run-as-admin is an admin-only install flag and must NOT be
    passed here — it causes Everything to exit immediately under a standard user
    account.
    """
    # Delete a corrupt database so Everything doesn't crash on load.
    db_path = exe_path.parent / "Everything.db"
    if _db_is_corrupt(db_path):
        print(f"Removing corrupt database ({db_path.stat().st_size} bytes): {db_path}", file=sys.stderr)
        try:
            db_path.unlink()
        except OSError as exc:
            print(f"Warning: could not remove corrupt db: {exc}", file=sys.stderr)

    try:
        proc = subprocess.Popen(
            [str(exe_path), "-startup"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
        )
        print(f"Launched {exe_path.name}", file=sys.stderr)
        return proc
    except Exception as exc:
        print(f"Failed to launch {exe_path}: {exc}", file=sys.stderr)
        return None


def launch_everything_elevated(exe_path: pathlib.Path) -> bool:
    """Relaunch Everything with UAC elevation via ShellExecute runas.

    Shows a UAC dialog — user must click Yes. Returns True if ShellExecute succeeded
    (not whether the user approved; approval is confirmed later by wait_for_ipc).
    """
    import ctypes
    try:
        ret = ctypes.windll.shell32.ShellExecuteW(
            None,           # hwnd
            "runas",        # verb — triggers UAC elevation
            str(exe_path),  # file
            "-startup",     # parameters
            None,           # working directory
            0,              # SW_HIDE
        )
        # ShellExecuteW returns >32 on success, <=32 on error
        if ret <= 32:
            print(f"ShellExecuteW returned {ret} (user may have cancelled UAC)", file=sys.stderr)
            return False
        print(f"Launched {exe_path.name} (elevated)", file=sys.stderr)
        return True
    except Exception as exc:
        print(f"Failed to launch elevated {exe_path}: {exc}", file=sys.stderr)
        return False


def wait_for_ipc(
    es_path: pathlib.Path,
    timeout: int = 30,
    process: Optional[subprocess.Popen] = None,
) -> bool:
    """Poll es.exe until Everything's IPC is ready or timeout expires.

    Pass the Popen object returned by launch_everything() so this function can
    detect an early exit and stop waiting immediately instead of burning the
    full timeout.
    """
    print(f"Waiting for Everything IPC (up to {timeout}s) ...", file=sys.stderr)
    time.sleep(2)  # let Everything register its IPC window
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        # If the process we launched already exited, IPC will never arrive.
        if process is not None and process.poll() is not None:
            print(
                f"Everything exited early (code {process.returncode}) — IPC will not become ready.",
                file=sys.stderr,
            )
            return False
        try:
            result = subprocess.run(
                [str(es_path), "-get-result-count"],
                capture_output=True,
                timeout=3,
            )
            if result.returncode == 0:
                print("IPC ready.", file=sys.stderr)
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def ensure_everything(
    es_path: pathlib.Path,
    auto_install: bool,
    bin_dir: pathlib.Path,
) -> dict:
    """Handle the not_running case: locate/download Everything, launch it, wait for IPC.

    Returns {} on success (caller should retry the search), or an error dict on failure.

    Cross-session note: Everything may already be running as a Windows service in
    Session 0 (LocalSystem).  In that case is_everything_running() returns True but
    es.exe still gets exit code 8 because IPC window messages don't cross session
    boundaries.  The fix is to launch a user-session client anyway; it connects to
    the service via the default named pipe and registers an IPC window that es.exe
    can reach.
    """
    everything_exe = find_everything_exe()

    if everything_exe:
        if is_everything_running():
            # Quick probe: IPC might already be available (user-session client running).
            if is_ipc_ready(es_path):
                print("Everything IPC is already ready.", file=sys.stderr)
                return {}

            # IPC not ready.  Everything is likely a service in Session 0 — launch a
            # user-session client that bridges to it via named pipe.
            print(
                "Everything is running but IPC is unavailable "
                "(possibly a service in Session 0). Launching user-session client ...",
                file=sys.stderr,
            )

        proc = launch_everything(everything_exe)
        if proc is None:
            return {
                "error": "launch_failed",
                "message": f"Could not start {everything_exe}.",
                "setup": "Try launching Everything manually from the Start Menu.",
            }
        if not wait_for_ipc(es_path, timeout=30, process=proc):
            return {
                "error": "ipc_timeout",
                "message": "Everything launched but IPC was not ready within 30s.",
                "setup": "Everything may still be building its index. Wait a moment and retry.",
            }
        return {}  # success — caller retries the search

    # Binary not found anywhere — need to download.
    if not auto_install:
        return {
            "error": "not_installed",
            "message": "Everything is not installed and the portable binary is missing from bin/.",
            "setup": (
                "Re-run with --auto-install to download the portable version (~5 MB). "
                "Or install Everything from https://www.voidtools.com."
            ),
            "can_auto_install": True,
        }

    # --auto-install path: download, then launch.
    print("Everything not found — downloading portable build ...", file=sys.stderr)
    try:
        everything_exe = download_portable(bin_dir)
    except RuntimeError as exc:
        return {"error": "download_failed", "message": str(exc), "setup": ""}

    proc = launch_everything(everything_exe)
    if proc is None:
        return {
            "error": "launch_failed",
            "message": f"Could not start {everything_exe}.",
            "setup": "Try launching Everything manually from the Start Menu.",
        }

    # First-time launch needs longer to build the initial index.
    if not wait_for_ipc(es_path, timeout=60, process=proc):
        return {
            "error": "ipc_timeout",
            "message": "Everything launched but IPC was not ready within 60s.",
            "setup": "Everything may still be building its index. Wait a moment and retry.",
        }

    return {}  # success — caller retries the search


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
    order: str,
    count_only: bool = False,
) -> dict:
    """Execute search using es.exe CLI.

    es.exe expects each search term/operator as its own argv token.
    Passing the whole query as one string makes compound queries like
    `meeting ext:zip` or `ext:pptx dm:lastmonth` fail silently.
    """
    query_args = shlex.split(query, posix=False)
    order_flag = "-sort-ascending" if order == "asc" else "-sort-descending"

    if count_only:
        cmd = [str(es_path), "-get-result-count", *query_args]
    else:
        cmd = [
            str(es_path),
            "-n", str(max_results),
            "-sort", SORT_MAP.get(sort, "name"),
            order_flag,
            "-csv",
            "-name",
            "-path-column",
            "-size",
            "-date-modified",
            *query_args,
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

    if count_only:
        try:
            total = int(stdout_text.strip().splitlines()[-1])
        except (ValueError, IndexError):
            total = 0
        return {"total": total, "query": query, "source": "es.exe"}

    results = parse_es_csv(stdout_text)
    return {
        "results": results,
        "total": len(results),
        "query": query,
        "source": "es.exe",
    }


def search_via_http(
    query: str,
    max_results: int,
    ports: List[int],
    sort: str = "name",
    order: str = "asc",
    count_only: bool = False,
) -> dict:
    """Execute search using Everything HTTP API."""
    params = urllib.parse.urlencode({
        "s": query,
        "j": 1,
        "c": 0 if count_only else max_results,
        "path_column": 1,
        "size_column": 1,
        "date_modified_column": 1,
        "sort": SORT_MAP.get(sort, "name"),
        "ascending": 1 if order == "asc" else 0,
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

        if count_only:
            return {
                "total": raw.get("totalResults", 0),
                "query": query,
                "source": f"http:{port}",
            }

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
    parser.add_argument("--max", type=int, default=30, help="Maximum results (default: 30)")
    parser.add_argument(
        "--sort",
        default="name",
        choices=list(SORT_MAP.keys()),
        help="Sort field (default: name)",
    )
    parser.add_argument(
        "--order",
        choices=["asc", "desc"],
        default=None,
        help="Sort direction. Default depends on --sort: name/path=asc, size/date-*=desc.",
    )
    parser.add_argument(
        "--count-only",
        action="store_true",
        help="Return only the total count, no result list. Useful for cheap probing.",
    )
    parser.add_argument(
        "--elevated",
        action="store_true",
        help=(
            "Relaunch Everything with UAC elevation so it can index system directories "
            "(C:\\Windows, Program Files, etc.). Shows a UAC confirmation dialog once."
        ),
    )
    parser.add_argument(
        "--auto-install",
        action="store_true",
        help=(
            "If Everything is not running, automatically download the portable build, "
            "launch it, and retry the search. Requires internet access (~5 MB download)."
        ),
    )
    parser.add_argument("--es-path", help="Explicit path to es.exe")
    parser.add_argument("--http-port", type=int, default=80, help="Everything HTTP port (default: 80)")
    args = parser.parse_args()

    order = args.order or DEFAULT_ORDER.get(args.sort, "asc")

    if sys.platform != "win32":
        _json_out({
            "error": "windows_only",
            "message": "Everything only runs on Windows. This skill cannot run on macOS/Linux.",
            "setup": "",
        })
        sys.exit(5)

    # --elevated: relaunch Everything with UAC, then search
    if args.elevated:
        everything_exe = find_everything_exe()
        if everything_exe is None:
            _json_out({
                "error": "not_found",
                "message": "Everything.exe not found — cannot relaunch elevated.",
                "setup": "Ensure Everything is installed or the skill's bin/ contains Everything.exe.",
            })
            sys.exit(1)
        print("Requesting UAC elevation — please confirm the dialog ...", file=sys.stderr)
        if not launch_everything_elevated(everything_exe):
            _json_out({
                "error": "launch_failed",
                "message": "UAC elevation was cancelled or failed.",
                "setup": "Accept the UAC dialog to allow Everything to index system directories.",
            })
            sys.exit(1)
        if not wait_for_ipc(find_es_exe(args.es_path) or pathlib.Path("es.exe"), timeout=30):
            _json_out({
                "error": "ipc_timeout",
                "message": "Everything (elevated) launched but IPC was not ready within 30s.",
                "setup": "Wait a moment and retry.",
            })
            sys.exit(1)

    # Strategy 1: es.exe
    es_path = find_es_exe(args.es_path)
    if es_path:
        result = search_via_es(
            es_path, args.query, args.max, args.sort, order, args.count_only
        )
        if "error" not in result:
            _json_out(result)
            sys.exit(0)
        if result["error"] == "not_running":
            # Attempt to locate/install/launch Everything, then retry once
            bootstrap = ensure_everything(es_path, args.auto_install, SKILL_ROOT / "bin")
            if "error" in bootstrap:
                _json_out(bootstrap)
                sys.exit(1)
            # Everything is now running — retry the search
            result = search_via_es(
                es_path, args.query, args.max, args.sort, order, args.count_only
            )
            if "error" not in result:
                _json_out(result)
                sys.exit(0)
            _json_out(result)
            sys.exit(1)
        # IPC not ready or other es error — fall through to HTTP

    # Strategy 2: HTTP API (try configured port + 8080)
    ports = [args.http_port]
    if args.http_port != 8080:
        ports.append(8080)

    http_result = search_via_http(
        args.query, args.max, ports, args.sort, order, args.count_only
    )
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
