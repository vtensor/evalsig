"""Tests for the report renderers (JSON, Markdown, TTY)."""
from __future__ import annotations

import json
import unittest

from evalsig.types import ComparisonResult
from evalsig.compare.report import to_json, to_markdown, to_tty


def _sample() -> ComparisonResult:
    return ComparisonResult(
        delta=0.0124,
        ci=(-0.003, 0.027),
        ci_level=0.95,
        p_value=0.082,
        significant=False,
        n_pairs=4032,
        n_clusters=1008,
        method="paired_permutation",
        mde=0.018,
        notes=("note one", "note two"),
    )


class TestJsonRenderer(unittest.TestCase):
    def test_valid_json_with_expected_keys(self) -> None:
        s = to_json(_sample())
        obj = json.loads(s)
        for k in ("delta", "ci", "p_value", "significant", "method", "mde"):
            self.assertIn(k, obj)
        self.assertAlmostEqual(obj["delta"], 0.0124)


class TestMarkdownRenderer(unittest.TestCase):
    def test_contains_table_and_notes(self) -> None:
        md = to_markdown(_sample())
        self.assertIn("EVALSIG comparison", md)
        self.assertIn("| Field | Value |", md)
        self.assertIn("note one", md)
        self.assertIn("note two", md)


class TestTTYRenderer(unittest.TestCase):
    def test_no_color_yields_plain_text(self) -> None:
        out = to_tty(_sample(), use_color=False)
        self.assertIn("EVALSIG comparison", out)
        self.assertNotIn("\033[", out)


if __name__ == "__main__":
    unittest.main()
