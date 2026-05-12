"""
Structural tests for skills/patent-builder.

Validates SKILL.md frontmatter, bilingual description, language directive,
and the presence / shape of reference/zh.md.
"""

import pathlib
import re
import unittest

SKILL_ROOT = pathlib.Path(__file__).resolve().parent.parent / "skills" / "patent-builder"
SKILL_MD   = SKILL_ROOT / "SKILL.md"
ZH_MD      = SKILL_ROOT / "reference" / "zh.md"


# ── frontmatter helpers ───────────────────────────────────────────────────────

def _parse_frontmatter(text: str) -> dict[str, str]:
    """Extract key: value pairs from the first YAML frontmatter block."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    result = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" in line:
            key, _, val = line.partition(":")
            result[key.strip()] = val.strip()
    return result


def _body(text: str) -> str:
    """Return text after the closing --- of the frontmatter block."""
    parts = text.split("---", maxsplit=2)
    return parts[2] if len(parts) >= 3 else text


# ── SKILL.md tests ────────────────────────────────────────────────────────────

class TestSkillMd(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.text = SKILL_MD.read_text(encoding="utf-8")
        cls.fm   = _parse_frontmatter(cls.text)
        cls.body = _body(cls.text)

    def test_file_exists(self):
        self.assertTrue(SKILL_MD.exists(), f"{SKILL_MD} not found")

    def test_frontmatter_has_name(self):
        self.assertIn("name", self.fm)
        self.assertEqual(self.fm["name"], "patent-builder")

    def test_frontmatter_has_description(self):
        self.assertIn("description", self.fm)
        self.assertTrue(self.fm["description"].strip())

    def test_description_contains_english(self):
        desc = self.fm.get("description", "")
        # Simple heuristic: must contain ASCII words
        self.assertTrue(re.search(r"[A-Za-z]{4,}", desc), "description has no English text")

    def test_description_contains_chinese(self):
        desc = self.fm.get("description", "")
        self.assertTrue(re.search(r"[一-鿿]", desc), "description has no Chinese text")

    def test_language_directive_references_zh(self):
        self.assertIn("reference/zh.md", self.body,
                      "SKILL.md body must reference reference/zh.md for Chinese users")

    def test_no_frontmatter_in_body(self):
        # Body should not start another --- block
        self.assertNotRegex(self.body.strip()[:10], r"^---")

    def test_not_empty_body(self):
        self.assertGreater(len(self.body.strip()), 200)


# ── reference/zh.md tests ─────────────────────────────────────────────────────

class TestZhReference(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.text = ZH_MD.read_text(encoding="utf-8") if ZH_MD.exists() else ""

    def test_file_exists(self):
        self.assertTrue(ZH_MD.exists(), f"{ZH_MD} not found")

    def test_no_yaml_frontmatter(self):
        # zh.md is a reference file, not a skill definition — no --- block expected
        self.assertFalse(
            self.text.strip().startswith("---"),
            "reference/zh.md should not have YAML frontmatter"
        )

    def test_contains_chinese(self):
        self.assertTrue(re.search(r"[一-鿿]", self.text),
                        "reference/zh.md contains no Chinese characters")

    def test_has_substantial_content(self):
        self.assertGreater(len(self.text.strip()), 500)

    def test_contains_mode_sections(self):
        self.assertIn("模式 A", self.text)
        self.assertIn("模式 B", self.text)
        self.assertIn("模式 C", self.text)

    def test_contains_disclosure_structure(self):
        self.assertIn("交底书", self.text)

    def test_contains_quality_check(self):
        self.assertIn("质量检查", self.text)


if __name__ == "__main__":
    unittest.main()
