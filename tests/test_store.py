"""Tests for the append-only Parquet store."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from evalsig.types import ItemResult, RunFrame
from evalsig.store.writer import RunStoreWriter, write_run
from evalsig.store.reader import list_runs, load_run, query_runs


def _mk(run_id: str, model: str = "m1", task: str = "t1",
        n: int = 20) -> RunFrame:
    return RunFrame(
        run_id=run_id, model_id=model, task_id=task, metric_name="acc",
        items=[
            ItemResult(item_id=str(i), score=float(i % 2),
                       cluster_id=f"c{i % 3}")
            for i in range(n)
        ],
    )


class TestStoreRoundTrip(unittest.TestCase):
    def test_write_then_load(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            write_run(d, _mk("r1"), project_id="proj",
                      delta=0.02, verdict="ALLOW")
            back = load_run(d, "r1", project_id="proj")
            self.assertEqual(back.run_id, "r1")
            self.assertEqual(len(back.items), 20)
            self.assertEqual(back.items[0].cluster_id, "c0")


class TestStoreQuery(unittest.TestCase):
    def test_filters_by_model_and_task(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            write_run(d, _mk("r1", "m1", "t1"), project_id="proj")
            write_run(d, _mk("r2", "m1", "t2"), project_id="proj")
            write_run(d, _mk("r3", "m2", "t1"), project_id="proj")
            m1 = query_runs(d, project_id="proj", model_id="m1")
            self.assertEqual({h.record.run_id for h in m1}, {"r1", "r2"})
            t1 = query_runs(d, project_id="proj", task_id="t1")
            self.assertEqual({h.record.run_id for h in t1}, {"r1", "r3"})


class TestStoreManifestPersists(unittest.TestCase):
    def test_writer_appends_and_reopens(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            with RunStoreWriter(d, project_id="proj") as w:
                w.write(_mk("r1"))
            # Re-open and add another run.
            with RunStoreWriter(d, project_id="proj") as w:
                w.write(_mk("r2"))
            self.assertEqual(len(list_runs(d, project_id="proj")), 2)


if __name__ == "__main__":
    unittest.main()
