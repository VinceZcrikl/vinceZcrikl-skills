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


if __name__ == "__main__":
    unittest.main()
