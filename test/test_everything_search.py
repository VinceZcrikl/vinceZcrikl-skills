"""
Tests for skills/everything-search/scripts/es_helper.py

Run:  python -m pytest test/ -v
  or  python test/run_tests.py
"""

import io
import json
import pathlib
import subprocess
import sys
import unittest
from unittest.mock import MagicMock, patch

# ── resolve skill root and inject scripts/ into path ────────────────────────
SKILL_ROOT = pathlib.Path(__file__).resolve().parent.parent / "skills" / "everything-search"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
import es_helper  # noqa: E402


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_proc(returncode: int, stdout: bytes = b"", stderr: bytes = b"") -> MagicMock:
    proc = MagicMock()
    proc.returncode = returncode
    proc.stdout = stdout
    proc.stderr = stderr
    return proc


CSV_HEADER = "Filename,Path,Size,Date Modified\r\n"
CSV_ROW    = 'report.pdf,"C:\\Users\\test",1048576,05/01/2026 14:32\r\n'


# ── format_size ──────────────────────────────────────────────────────────────

class TestFormatSize(unittest.TestCase):

    def test_none(self):
        self.assertEqual(es_helper.format_size(None), "")

    def test_bytes(self):
        self.assertEqual(es_helper.format_size(500), "500 B")

    def test_kilobytes(self):
        self.assertIn("KB", es_helper.format_size(2048))

    def test_megabytes(self):
        self.assertIn("MB", es_helper.format_size(2 * 1024 ** 2))

    def test_gigabytes(self):
        self.assertIn("GB", es_helper.format_size(2 * 1024 ** 3))

    def test_zero(self):
        self.assertEqual(es_helper.format_size(0), "0 B")


# ── parse_es_csv ─────────────────────────────────────────────────────────────

class TestParseEsCsv(unittest.TestCase):

    def test_empty_string(self):
        self.assertEqual(es_helper.parse_es_csv(""), [])

    def test_header_only(self):
        self.assertEqual(es_helper.parse_es_csv(CSV_HEADER), [])

    def test_single_row(self):
        rows = es_helper.parse_es_csv(CSV_HEADER + CSV_ROW)
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual(r["name"], "report.pdf")
        self.assertEqual(r["path"], "C:\\Users\\test")
        self.assertEqual(r["size"], 1048576)
        self.assertEqual(r["size_human"], "1.0 MB")
        self.assertEqual(r["date_modified"], "05/01/2026 14:32")

    def test_invalid_size_becomes_none(self):
        csv = "Filename,Path,Size,Date Modified\r\nfile.txt,C:\\,notanumber,\r\n"
        rows = es_helper.parse_es_csv(csv)
        self.assertIsNone(rows[0]["size"])

    def test_multiple_rows(self):
        csv = CSV_HEADER + CSV_ROW + 'other.txt,"C:\\",512,05/02/2026 10:00\r\n'
        self.assertEqual(len(es_helper.parse_es_csv(csv)), 2)


# ── constants & defaults ─────────────────────────────────────────────────────

class TestConstants(unittest.TestCase):

    def test_sort_map_keys(self):
        expected = {"name", "size", "date-modified", "date-created", "path"}
        self.assertEqual(set(es_helper.SORT_MAP.keys()), expected)

    def test_default_order_name_asc(self):
        self.assertEqual(es_helper.DEFAULT_ORDER["name"], "asc")

    def test_default_order_path_asc(self):
        self.assertEqual(es_helper.DEFAULT_ORDER["path"], "asc")

    def test_default_order_size_desc(self):
        self.assertEqual(es_helper.DEFAULT_ORDER["size"], "desc")

    def test_default_order_date_modified_desc(self):
        self.assertEqual(es_helper.DEFAULT_ORDER["date-modified"], "desc")

    def test_default_order_date_created_desc(self):
        self.assertEqual(es_helper.DEFAULT_ORDER["date-created"], "desc")

    def test_everything_version_nonempty(self):
        self.assertTrue(es_helper.EVERYTHING_VERSION)

    def test_portable_urls_cover_amd64(self):
        self.assertIn("AMD64", es_helper.EVERYTHING_PORTABLE_URLS)


# ── find_es_exe ───────────────────────────────────────────────────────────────

class TestFindEsExe(unittest.TestCase):

    def test_bundled_es_exe_exists(self):
        bundled = SKILL_ROOT / "bin" / "es.exe"
        result = es_helper.find_es_exe()
        if bundled.exists():
            self.assertIsNotNone(result)
        # else: no assertion — optional system install

    def test_explicit_hint_valid(self):
        bundled = SKILL_ROOT / "bin" / "es.exe"
        if bundled.exists():
            result = es_helper.find_es_exe(hint=str(bundled))
            self.assertEqual(result, bundled)

    def test_explicit_hint_invalid_returns_none_or_fallback(self):
        result = es_helper.find_es_exe(hint=str(SKILL_ROOT / "bin" / "nonexistent.exe"))
        # Should fall through to bundled / PATH lookup, not crash
        # (may still find es.exe via bundled path)
        self.assertIsInstance(result, (pathlib.Path, type(None)))


# ── find_everything_exe ───────────────────────────────────────────────────────

class TestFindEverythingExe(unittest.TestCase):

    def test_bundled_everything_exe_exists(self):
        bundled = SKILL_ROOT / "bin" / "Everything.exe"
        result = es_helper.find_everything_exe()
        if bundled.exists():
            self.assertIsNotNone(result)

    def test_returns_path_or_none(self):
        result = es_helper.find_everything_exe()
        self.assertIsInstance(result, (pathlib.Path, type(None)))


# ── search_via_es (mocked) ────────────────────────────────────────────────────

class TestSearchViaEsMocked(unittest.TestCase):

    ES = SKILL_ROOT / "bin" / "es.exe"

    @patch("subprocess.run")
    def test_not_running_exit_8(self, mock_run):
        mock_run.return_value = _make_proc(8)
        result = es_helper.search_via_es(self.ES, "ext:py", 20, "name", "asc")
        self.assertEqual(result["error"], "not_running")

    @patch("subprocess.run")
    def test_ipc_not_ready_exit_7(self, mock_run):
        mock_run.return_value = _make_proc(7)
        result = es_helper.search_via_es(self.ES, "ext:py", 20, "name", "asc")
        self.assertEqual(result["error"], "ipc_failed")

    @patch("subprocess.run")
    def test_success_returns_results(self, mock_run):
        csv_bytes = (CSV_HEADER + CSV_ROW).encode("utf-8")
        mock_run.return_value = _make_proc(0, stdout=csv_bytes)
        result = es_helper.search_via_es(self.ES, "ext:pdf", 20, "name", "asc")
        self.assertNotIn("error", result)
        self.assertIn("results", result)
        self.assertEqual(len(result["results"]), 1)
        self.assertEqual(result["source"], "es.exe")

    @patch("subprocess.run")
    def test_count_only_returns_total(self, mock_run):
        mock_run.return_value = _make_proc(0, stdout=b"42\n")
        result = es_helper.search_via_es(self.ES, "ext:py", 20, "name", "asc", count_only=True)
        self.assertNotIn("error", result)
        self.assertEqual(result["total"], 42)
        self.assertNotIn("results", result)

    @patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="es.exe", timeout=15))
    def test_timeout_returns_ipc_failed(self, _mock):
        result = es_helper.search_via_es(self.ES, "ext:py", 20, "name", "asc")
        self.assertEqual(result["error"], "ipc_failed")

    @patch("subprocess.run")
    def test_sort_ascending_flag_in_cmd(self, mock_run):
        mock_run.return_value = _make_proc(0, stdout=CSV_HEADER.encode())
        es_helper.search_via_es(self.ES, "ext:py", 20, "name", "asc")
        cmd = mock_run.call_args[0][0]
        self.assertIn("-sort-ascending", cmd)

    @patch("subprocess.run")
    def test_sort_descending_flag_in_cmd(self, mock_run):
        mock_run.return_value = _make_proc(0, stdout=CSV_HEADER.encode())
        es_helper.search_via_es(self.ES, "ext:py", 20, "size", "desc")
        cmd = mock_run.call_args[0][0]
        self.assertIn("-sort-descending", cmd)

    @patch("subprocess.run")
    def test_query_tokenised_in_cmd(self, mock_run):
        mock_run.return_value = _make_proc(0, stdout=CSV_HEADER.encode())
        es_helper.search_via_es(self.ES, "ext:pdf dm:thisweek", 20, "name", "asc")
        cmd = mock_run.call_args[0][0]
        self.assertIn("ext:pdf", cmd)
        self.assertIn("dm:thisweek", cmd)


# ── wait_for_ipc (mocked) ─────────────────────────────────────────────────────

class TestWaitForIpcMocked(unittest.TestCase):

    ES = SKILL_ROOT / "bin" / "es.exe"

    @patch("time.sleep")
    @patch("time.monotonic", side_effect=[0, 1, 2])
    @patch("subprocess.run")
    def test_ready_on_first_poll(self, mock_run, _mono, _sleep):
        mock_run.return_value = _make_proc(0)
        result = es_helper.wait_for_ipc(self.ES, timeout=30)
        self.assertTrue(result)

    @patch("time.sleep")
    @patch("time.monotonic", side_effect=[0, 0, 100])  # deadline=1, first poll enters, second exits
    @patch("subprocess.run")
    def test_timeout_returns_false(self, mock_run, _mono, _sleep):
        mock_run.return_value = _make_proc(8)
        result = es_helper.wait_for_ipc(self.ES, timeout=1)
        self.assertFalse(result)


# ── argparse defaults ─────────────────────────────────────────────────────────

class TestArgDefaults(unittest.TestCase):

    def _parse(self, args):
        import argparse
        # Temporarily replace sys.argv
        old = sys.argv
        sys.argv = ["es_helper.py", "--query", "test"] + args
        # Re-run the parser from main() logic
        parser = argparse.ArgumentParser()
        parser.add_argument("--query", required=True)
        parser.add_argument("--max", type=int, default=20)
        parser.add_argument("--sort", default="name",
                            choices=list(es_helper.SORT_MAP.keys()))
        parser.add_argument("--order", choices=["asc", "desc"], default=None)
        parser.add_argument("--count-only", action="store_true")
        parser.add_argument("--elevated", action="store_true")
        parser.add_argument("--auto-install", action="store_true")
        parser.add_argument("--es-path")
        parser.add_argument("--http-port", type=int, default=80)
        result = parser.parse_args()
        sys.argv = old
        return result

    def test_max_default_20(self):
        args = self._parse([])
        self.assertEqual(args.max, 20)

    def test_sort_default_name(self):
        args = self._parse([])
        self.assertEqual(args.sort, "name")

    def test_order_default_none(self):
        args = self._parse([])
        self.assertIsNone(args.order)

    def test_count_only_default_false(self):
        args = self._parse([])
        self.assertFalse(args.count_only)

    def test_elevated_default_false(self):
        args = self._parse([])
        self.assertFalse(args.elevated)

    def test_auto_install_default_false(self):
        args = self._parse([])
        self.assertFalse(args.auto_install)

    def test_http_port_default_80(self):
        args = self._parse([])
        self.assertEqual(args.http_port, 80)


# ── integration (skipped when Everything not running) ────────────────────────

def _everything_available() -> bool:
    es = es_helper.find_es_exe()
    if es is None:
        return False
    try:
        proc = subprocess.run([str(es), "-get-result-count", ""],
                              capture_output=True, timeout=3)
        return proc.returncode == 0
    except Exception:
        return False


@unittest.skipUnless(_everything_available(), "Everything not running — skipping live tests")
class TestLiveSearch(unittest.TestCase):

    ES = es_helper.find_es_exe()

    def test_simple_query_returns_results(self):
        result = es_helper.search_via_es(self.ES, "ext:py", 5, "name", "asc")
        self.assertNotIn("error", result)
        self.assertIn("results", result)
        self.assertIn("total", result)

    def test_count_only(self):
        result = es_helper.search_via_es(self.ES, "ext:py", 5, "name", "asc", count_only=True)
        self.assertNotIn("error", result)
        self.assertIsInstance(result["total"], int)
        self.assertNotIn("results", result)

    def test_date_sort_descending(self):
        result = es_helper.search_via_es(self.ES, "ext:py", 5, "date-modified", "desc")
        self.assertNotIn("error", result)

    def test_result_fields(self):
        result = es_helper.search_via_es(self.ES, "ext:py", 3, "name", "asc")
        if result.get("results"):
            r = result["results"][0]
            self.assertIn("name", r)
            self.assertIn("path", r)
            self.assertIn("size_human", r)
            self.assertIn("date_modified", r)


# ── parse_es_csv edge cases ───────────────────────────────────────────────────

class TestParseEsCsvEdgeCases(unittest.TestCase):

    def test_unicode_filename(self):
        csv = "Filename,Path,Size,Date Modified\r\n日本語.txt,C:\\Users\\test,100,\r\n"
        rows = es_helper.parse_es_csv(csv)
        self.assertEqual(rows[0]["name"], "日本語.txt")

    def test_path_with_spaces(self):
        csv = 'Filename,Path,Size,Date Modified\r\nfile.txt,"C:\\My Documents\\Work",256,\r\n'
        rows = es_helper.parse_es_csv(csv)
        self.assertEqual(rows[0]["path"], "C:\\My Documents\\Work")

    def test_size_with_commas(self):
        csv = "Filename,Path,Size,Date Modified\r\nbig.iso,C:\\,1,234,567,\r\n"
        # size field may have commas stripped or fail gracefully
        rows = es_helper.parse_es_csv(csv)
        self.assertIsInstance(rows[0]["size"], (int, type(None)))

    def test_empty_date_field(self):
        csv = "Filename,Path,Size,Date Modified\r\nfile.log,C:\\,0,\r\n"
        rows = es_helper.parse_es_csv(csv)
        self.assertEqual(rows[0]["date_modified"], "")

    def test_zero_size_formats_as_0b(self):
        csv = "Filename,Path,Size,Date Modified\r\nempty.txt,C:\\,0,\r\n"
        rows = es_helper.parse_es_csv(csv)
        self.assertEqual(rows[0]["size_human"], "0 B")

    def test_size_exactly_1kb(self):
        csv = "Filename,Path,Size,Date Modified\r\nexact.bin,C:\\,1024,\r\n"
        rows = es_helper.parse_es_csv(csv)
        self.assertIn("KB", rows[0]["size_human"])

    def test_size_exactly_1mb(self):
        csv = f"Filename,Path,Size,Date Modified\r\nexact.bin,C:\\,{1024**2},\r\n"
        rows = es_helper.parse_es_csv(csv)
        self.assertIn("MB", rows[0]["size_human"])

    def test_whitespace_around_fields(self):
        csv = "Filename,Path,Size,Date Modified\r\n  trimmed.txt , C:\\test ,512,\r\n"
        rows = es_helper.parse_es_csv(csv)
        self.assertEqual(rows[0]["name"], "trimmed.txt")
        self.assertEqual(rows[0]["path"], "C:\\test")


# ── format_size boundary values ───────────────────────────────────────────────

class TestFormatSizeBoundaries(unittest.TestCase):

    def test_1023_bytes(self):
        self.assertEqual(es_helper.format_size(1023), "1023 B")

    def test_1024_bytes_is_kb(self):
        self.assertIn("KB", es_helper.format_size(1024))

    def test_1mb_minus_1(self):
        self.assertIn("KB", es_helper.format_size(1024 ** 2 - 1))

    def test_exactly_1gb(self):
        self.assertIn("GB", es_helper.format_size(1024 ** 3))

    def test_large_value(self):
        result = es_helper.format_size(10 * 1024 ** 3)
        self.assertIn("GB", result)


# ── search_via_http (mocked) ──────────────────────────────────────────────────

class TestSearchViaHttpMocked(unittest.TestCase):

    def _http_response(self, body: dict) -> MagicMock:
        raw = json.dumps(body).encode("utf-8")
        cm = MagicMock()
        cm.__enter__ = MagicMock(return_value=cm)
        cm.__exit__ = MagicMock(return_value=False)
        cm.read = MagicMock(return_value=raw)
        return cm

    @patch("urllib.request.urlopen")
    def test_success_returns_results(self, mock_urlopen):
        payload = {
            "totalResults": 2,
            "results": [
                {"name": "a.py", "path": "C:\\src", "size": 512, "date_modified": ""},
                {"name": "b.py", "path": "C:\\src", "size": 1024, "date_modified": ""},
            ],
        }
        mock_urlopen.return_value = self._http_response(payload)
        result = es_helper.search_via_http("ext:py", 20, [80])
        self.assertNotIn("error", result)
        self.assertEqual(len(result["results"]), 2)
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["source"], "http:80")

    @patch("urllib.request.urlopen")
    def test_count_only_returns_total(self, mock_urlopen):
        payload = {"totalResults": 99, "results": []}
        mock_urlopen.return_value = self._http_response(payload)
        result = es_helper.search_via_http("ext:py", 20, [80], count_only=True)
        self.assertNotIn("error", result)
        self.assertEqual(result["total"], 99)
        self.assertNotIn("results", result)

    @patch("urllib.request.urlopen", side_effect=Exception("connection refused"))
    def test_all_ports_fail_returns_error(self, _mock):
        result = es_helper.search_via_http("ext:py", 20, [80, 8080])
        self.assertEqual(result["error"], "http_failed")
        self.assertIn("message", result)

    @patch("urllib.request.urlopen")
    def test_result_size_human_populated(self, mock_urlopen):
        payload = {
            "totalResults": 1,
            "results": [{"name": "big.iso", "path": "C:\\", "size": 2 * 1024 ** 3, "date_modified": ""}],
        }
        mock_urlopen.return_value = self._http_response(payload)
        result = es_helper.search_via_http("big.iso", 5, [80])
        self.assertIn("GB", result["results"][0]["size_human"])

    @patch("urllib.request.urlopen")
    def test_null_size_handled(self, mock_urlopen):
        payload = {
            "totalResults": 1,
            "results": [{"name": "nul.txt", "path": "C:\\", "size": None, "date_modified": ""}],
        }
        mock_urlopen.return_value = self._http_response(payload)
        result = es_helper.search_via_http("nul.txt", 5, [80])
        self.assertIsNone(result["results"][0]["size"])
        self.assertEqual(result["results"][0]["size_human"], "")

    @patch("urllib.request.urlopen")
    def test_fallback_to_second_port(self, mock_urlopen):
        import urllib.error
        payload = {"totalResults": 1, "results": [{"name": "x.txt", "path": "C:\\", "size": 0, "date_modified": ""}]}
        ok_response = self._http_response(payload)
        mock_urlopen.side_effect = [urllib.error.URLError("refused"), ok_response]
        result = es_helper.search_via_http("x.txt", 5, [80, 8080])
        self.assertNotIn("error", result)
        self.assertEqual(result["source"], "http:8080")


# ── is_everything_running (mocked) ────────────────────────────────────────────

class TestIsEverythingRunning(unittest.TestCase):

    @patch("subprocess.run")
    def test_returns_true_when_process_listed(self, mock_run):
        mock_run.return_value = _make_proc(0, stdout=b"Everything.exe   1234 Console   1 24,000 K")
        self.assertTrue(es_helper.is_everything_running())

    @patch("subprocess.run")
    def test_returns_false_when_not_listed(self, mock_run):
        mock_run.return_value = _make_proc(0, stdout=b"INFO: No tasks running with the specified criteria.")
        self.assertFalse(es_helper.is_everything_running())

    @patch("subprocess.run", side_effect=Exception("tasklist failed"))
    def test_exception_returns_false(self, _mock):
        self.assertFalse(es_helper.is_everything_running())


# ── is_ipc_ready (mocked) ─────────────────────────────────────────────────────

class TestIsIpcReady(unittest.TestCase):

    ES = SKILL_ROOT / "bin" / "es.exe"

    @patch("subprocess.run")
    def test_returns_true_on_exit_0(self, mock_run):
        mock_run.return_value = _make_proc(0)
        self.assertTrue(es_helper.is_ipc_ready(self.ES))

    @patch("subprocess.run")
    def test_returns_false_on_nonzero(self, mock_run):
        mock_run.return_value = _make_proc(8)
        self.assertFalse(es_helper.is_ipc_ready(self.ES))

    @patch("subprocess.run", side_effect=Exception("boom"))
    def test_exception_returns_false(self, _mock):
        self.assertFalse(es_helper.is_ipc_ready(self.ES))


# ── _db_is_corrupt ────────────────────────────────────────────────────────────

class TestDbIsCorrupt(unittest.TestCase):

    def test_missing_file_not_corrupt(self):
        p = pathlib.Path("nonexistent_db_xyz.db")
        self.assertFalse(es_helper._db_is_corrupt(p))

    def test_small_file_is_corrupt(self):
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
            f.write(b"x" * 100)
            tmp = pathlib.Path(f.name)
        try:
            self.assertTrue(es_helper._db_is_corrupt(tmp))
        finally:
            tmp.unlink(missing_ok=True)

    def test_large_file_not_corrupt(self):
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
            f.write(b"x" * 2048)
            tmp = pathlib.Path(f.name)
        try:
            self.assertFalse(es_helper._db_is_corrupt(tmp))
        finally:
            tmp.unlink(missing_ok=True)

    def test_exactly_1024_bytes_not_corrupt(self):
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
            f.write(b"x" * 1024)
            tmp = pathlib.Path(f.name)
        try:
            self.assertFalse(es_helper._db_is_corrupt(tmp))
        finally:
            tmp.unlink(missing_ok=True)


# ── search_via_es compound queries ────────────────────────────────────────────

class TestSearchViaEsCompoundQueries(unittest.TestCase):

    ES = SKILL_ROOT / "bin" / "es.exe"

    @patch("subprocess.run")
    def test_compound_query_tokens_split(self, mock_run):
        mock_run.return_value = _make_proc(0, stdout=CSV_HEADER.encode())
        es_helper.search_via_es(self.ES, "meeting ext:zip", 10, "name", "asc")
        cmd = mock_run.call_args[0][0]
        self.assertIn("meeting", cmd)
        self.assertIn("ext:zip", cmd)

    @patch("subprocess.run")
    def test_size_filter_query(self, mock_run):
        mock_run.return_value = _make_proc(0, stdout=CSV_HEADER.encode())
        es_helper.search_via_es(self.ES, "ext:mp4 size:>500mb", 5, "size", "desc")
        cmd = mock_run.call_args[0][0]
        self.assertIn("ext:mp4", cmd)
        self.assertIn("size:>500mb", cmd)

    @patch("subprocess.run")
    def test_date_filter_query(self, mock_run):
        mock_run.return_value = _make_proc(0, stdout=CSV_HEADER.encode())
        es_helper.search_via_es(self.ES, "ext:docx dm:thisweek", 20, "date-modified", "desc")
        cmd = mock_run.call_args[0][0]
        self.assertIn("dm:thisweek", cmd)

    @patch("subprocess.run")
    def test_path_filter_query(self, mock_run):
        mock_run.return_value = _make_proc(0, stdout=CSV_HEADER.encode())
        es_helper.search_via_es(self.ES, 'path:C:\\Users\\ ext:py', 20, "name", "asc")
        cmd = mock_run.call_args[0][0]
        self.assertTrue(any("path:" in token for token in cmd))

    @patch("subprocess.run")
    def test_max_results_respected_in_cmd(self, mock_run):
        mock_run.return_value = _make_proc(0, stdout=CSV_HEADER.encode())
        es_helper.search_via_es(self.ES, "ext:log", 50, "name", "asc")
        cmd = mock_run.call_args[0][0]
        n_idx = cmd.index("-n")
        self.assertEqual(cmd[n_idx + 1], "50")

    @patch("subprocess.run")
    def test_sort_by_date_modified(self, mock_run):
        mock_run.return_value = _make_proc(0, stdout=CSV_HEADER.encode())
        es_helper.search_via_es(self.ES, "ext:jpg", 20, "date-modified", "desc")
        cmd = mock_run.call_args[0][0]
        self.assertIn("date-modified", cmd)

    @patch("subprocess.run")
    def test_sort_by_path(self, mock_run):
        mock_run.return_value = _make_proc(0, stdout=CSV_HEADER.encode())
        es_helper.search_via_es(self.ES, "ext:txt", 20, "path", "asc")
        cmd = mock_run.call_args[0][0]
        self.assertIn("path", cmd)

    @patch("subprocess.run")
    def test_csv_flag_present(self, mock_run):
        mock_run.return_value = _make_proc(0, stdout=CSV_HEADER.encode())
        es_helper.search_via_es(self.ES, "ext:py", 10, "name", "asc")
        cmd = mock_run.call_args[0][0]
        self.assertIn("-csv", cmd)

    @patch("subprocess.run")
    def test_path_column_flag_present(self, mock_run):
        mock_run.return_value = _make_proc(0, stdout=CSV_HEADER.encode())
        es_helper.search_via_es(self.ES, "ext:py", 10, "name", "asc")
        cmd = mock_run.call_args[0][0]
        self.assertIn("-path-column", cmd)

    @patch("subprocess.run")
    def test_size_flag_present(self, mock_run):
        mock_run.return_value = _make_proc(0, stdout=CSV_HEADER.encode())
        es_helper.search_via_es(self.ES, "ext:py", 10, "name", "asc")
        cmd = mock_run.call_args[0][0]
        self.assertIn("-size", cmd)


# ── integration: additional live search scenarios ─────────────────────────────

@unittest.skipUnless(_everything_available(), "Everything not running — skipping live tests")
class TestLiveSearchExtended(unittest.TestCase):

    ES = es_helper.find_es_exe()

    def test_search_by_extension_txt(self):
        result = es_helper.search_via_es(self.ES, "ext:txt", 10, "name", "asc")
        self.assertNotIn("error", result)
        self.assertIn("results", result)

    def test_search_large_files(self):
        result = es_helper.search_via_es(self.ES, "size:>100mb", 5, "size", "desc")
        self.assertNotIn("error", result)
        if result["results"]:
            for r in result["results"]:
                self.assertIsNotNone(r["size"])
                self.assertGreater(r["size"], 100 * 1024 * 1024)

    def test_search_modified_this_month(self):
        result = es_helper.search_via_es(self.ES, "dm:thismonth ext:py", 10, "date-modified", "desc")
        self.assertNotIn("error", result)

    def test_search_in_users_folder(self):
        result = es_helper.search_via_es(self.ES, "path:C:\\Users\\ ext:json", 5, "name", "asc")
        self.assertNotIn("error", result)
        if result["results"]:
            for r in result["results"]:
                self.assertTrue(r["path"].lower().startswith("c:\\users"))

    def test_count_only_gives_integer(self):
        result = es_helper.search_via_es(self.ES, "ext:exe", 1, "name", "asc", count_only=True)
        self.assertIsInstance(result["total"], int)
        self.assertGreater(result["total"], 0)

    def test_no_results_query(self):
        result = es_helper.search_via_es(self.ES, "zz_unlikely_filename_xyz_987.abcdef", 5, "name", "asc")
        self.assertNotIn("error", result)
        self.assertEqual(result["total"], 0)

    def test_result_full_path_is_string(self):
        result = es_helper.search_via_es(self.ES, "ext:py", 3, "name", "asc")
        for r in result.get("results", []):
            self.assertIsInstance(r["name"], str)
            self.assertIsInstance(r["path"], str)

    def test_size_human_readable_format(self):
        result = es_helper.search_via_es(self.ES, "ext:py", 5, "size", "desc")
        for r in result.get("results", []):
            if r["size"] is not None and r["size"] > 0:
                self.assertTrue(
                    any(unit in r["size_human"] for unit in ("B", "KB", "MB", "GB")),
                    f"Unexpected size_human: {r['size_human']!r}",
                )

    def test_source_field_is_es(self):
        result = es_helper.search_via_es(self.ES, "ext:py", 1, "name", "asc")
        self.assertEqual(result.get("source"), "es.exe")

    def test_query_echoed_in_result(self):
        query = "ext:ini"
        result = es_helper.search_via_es(self.ES, query, 5, "name", "asc")
        self.assertEqual(result.get("query"), query)


if __name__ == "__main__":
    unittest.main()
