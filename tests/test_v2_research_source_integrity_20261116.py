"""Research-only provenance guard: source code must not contain remote shell output."""
from __future__ import annotations
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE_DIRS = ("research", "tests")


def tracked_py():
    return [p for dirname in MODULE_DIRS for p in sorted((ROOT / dirname).rglob("*.py"))]


class ResearchSourceIntegrity(unittest.TestCase):
    def test_all_research_and_test_modules_parse(self):
        modules = tracked_py()
        self.assertGreaterEqual(len(modules), 300)
        for p in modules:
            with self.subTest(path=str(p.relative_to(ROOT))):
                ast.parse(p.read_text(encoding="utf-8"), filename=str(p))

    def test_no_copied_remote_tool_footer(self):
        marker = "[executed" + " on device:"
        for p in tracked_py():
            with self.subTest(path=str(p.relative_to(ROOT))):
                self.assertNotIn(marker, p.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
