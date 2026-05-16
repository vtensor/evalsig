"""End-to-end tests for the CLI subcommands."""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from evalsig.cli.main import main as cli_main
from evalsig.io.json_runframe import write_runframe_json
from evalsig.types import ItemResult, RunFrame


def _mk(run_id: str, model: str, scores: list[float]) -> RunFrame:
    return RunFrame(
        run_id=run_id, model_id=model, task_id="t",
        metric_name="accuracy",
        items=[
            ItemResult(item_id=f"i{i}", score=s)
            for i, s in enumerate(scores)
        ],
    )


class TestVersion(unittest.TestCase):
    def test_version_command(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = cli_main(["version"])
        self.assertEqual(code, 0)
        self.assertIn("evalsig", buf.getvalue())


class TestDoctor(unittest.TestCase):
    def test_validates_clean_file(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "r.json"
            write_runframe_json(_mk("r", "m", [1.0, 0.0, 1.0]), p)
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = cli_main(["doctor", str(p)])
            self.assertEqual(code, 0)
            self.assertIn("validate cleanly", buf.getvalue())

    def test_flags_broken_file(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "broken.json"
            p.write_text('{"run_id": "r"}')  # missing required fields
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = cli_main(["doctor", str(p)])
            self.assertEqual(code, 65)
            self.assertIn("FAIL", buf.getvalue())


class TestGateExit(unittest.TestCase):
    def test_gate_exit_codes(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            base = Path(d) / "a.json"
            cand = Path(d) / "b.json"
            # Identical scores -> not significant -> REJECT or INCONCLUSIVE
            write_runframe_json(_mk("a", "m1", [0.5] * 50), base)
            write_runframe_json(_mk("b", "m2", [0.5] * 50), cand)
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = cli_main([
                    "gate", "--baseline", str(base), "--candidate", str(cand),
                    "--min-delta", "0.01", "--seed", "0",
                ])
            self.assertIn(code, (1, 2))


class TestMDE(unittest.TestCase):
    def test_mde_command(self) -> None:
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = cli_main([
                "mde", "--sd-diff", "0.3", "--n-pairs", "1000",
                "--alpha", "0.05", "--power", "0.80", "--one-sided",
            ])
        self.assertEqual(code, 0)
        self.assertIn("MDE", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
