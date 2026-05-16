"""Tests for the Parquet reader/writer at the io layer."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from evalsig.io import read_runframe_parquet, write_runframe_parquet
from evalsig.types import ItemResult, RunFrame


class TestParquetRoundTrip(unittest.TestCase):
    def test_round_trip_preserves_fields(self) -> None:
        run = RunFrame(
            run_id="r1", model_id="m1", task_id="t1", metric_name="acc",
            items=[
                ItemResult(item_id=f"item-{i}", score=float(i) / 10,
                           cluster_id=f"c{i % 4}", metadata={"k": i})
                for i in range(50)
            ],
            config_hash="abc123",
        )
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "r.parquet"
            write_runframe_parquet(run, p)
            back = read_runframe_parquet(p)
            self.assertEqual(back.run_id, run.run_id)
            self.assertEqual(back.model_id, run.model_id)
            self.assertEqual(back.config_hash, run.config_hash)
            self.assertEqual(len(back.items), 50)
            # Spot-check item-level fields.
            self.assertEqual(back.items[3].item_id, "item-3")
            self.assertAlmostEqual(back.items[3].score, 0.3)
            self.assertEqual(back.items[3].cluster_id, "c3")
            self.assertEqual(back.items[3].metadata, {"k": 3})


if __name__ == "__main__":
    unittest.main()
