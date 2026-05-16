"""Tests for the HELM scenario reader."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from evalsig.io.helm import read_helm_scenario


def _scenario(n: int = 10) -> dict:
    # Minimal HELM-shaped scenario_state.json.
    return {
        "adapter_spec": {"model": "model-x"},
        "scenario": {"name": "mmlu"},
        "request_states": [
            {
                "instance": {"id": f"q{i}", "category": "stem" if i % 2 else "humanities"},
                "result": {"success": (i % 2 == 0)},
            }
            for i in range(n)
        ],
    }


class TestHelmReader(unittest.TestCase):
    def test_reads_success_field(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "scenario_state.json"
            p.write_text(json.dumps(_scenario(20)))
            run = read_helm_scenario(p)
            self.assertEqual(len(run.items), 20)
            self.assertEqual(run.items[0].score, 1.0)
            self.assertEqual(run.items[1].score, 0.0)
            self.assertEqual(run.model_id, "model-x")
            self.assertEqual(run.task_id, "mmlu")

    def test_cluster_key_pulls_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "scenario_state.json"
            p.write_text(json.dumps(_scenario(20)))
            run = read_helm_scenario(p, cluster_key="category")
            categories = {it.cluster_id for it in run.items}
            self.assertEqual(categories, {"stem", "humanities"})


if __name__ == "__main__":
    unittest.main()
