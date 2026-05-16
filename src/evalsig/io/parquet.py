"""Parquet reader and writer for the canonical RunFrame schema.

Parquet is the on-disk format for long-term storage. One row per
(run, item, epoch). Predicate pushdown on (project_id, task_id,
model_id) is cheap, so the store layer can answer historical queries
without scanning every file.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import pyarrow as pa
import pyarrow.parquet as pq

from evalsig.types import ItemResult, RunFrame


# Public schema. Keep stable across v1; only backward-compatible
# additions are allowed.
PARQUET_SCHEMA = pa.schema([
    ("project_id", pa.string()),
    ("run_id", pa.string()),
    ("model_id", pa.string()),
    ("task_id", pa.string()),
    ("metric_name", pa.string()),
    ("item_id", pa.string()),
    ("cluster_id", pa.string()),
    ("epoch", pa.int32()),
    ("score", pa.float64()),
    ("config_hash", pa.string()),
    ("ts", pa.timestamp("us", tz="UTC")),
    ("metadata_json", pa.string()),
])


def runframe_to_table(run: RunFrame, *, project_id: str = "default",
                     ts: Optional[pa.TimestampScalar] = None) -> pa.Table:
    """Convert a RunFrame to a PyArrow Table matching PARQUET_SCHEMA."""
    n = len(run.items)
    if n == 0:
        raise ValueError("cannot serialise a RunFrame with no items")
    if ts is None:
        ts = pa.scalar(0, type=pa.timestamp("us", tz="UTC"))

    columns = {
        "project_id":  pa.array([project_id] * n, type=pa.string()),
        "run_id":      pa.array([run.run_id] * n, type=pa.string()),
        "model_id":    pa.array([run.model_id] * n, type=pa.string()),
        "task_id":     pa.array([run.task_id] * n, type=pa.string()),
        "metric_name": pa.array([run.metric_name] * n, type=pa.string()),
        "item_id":     pa.array([it.item_id for it in run.items], type=pa.string()),
        "cluster_id":  pa.array([it.cluster_id for it in run.items], type=pa.string()),
        "epoch":       pa.array([it.epoch for it in run.items], type=pa.int32()),
        "score":       pa.array([float(it.score) for it in run.items], type=pa.float64()),
        "config_hash": pa.array([run.config_hash] * n, type=pa.string()),
        "ts":          pa.array([ts.as_py()] * n, type=pa.timestamp("us", tz="UTC")),
        "metadata_json": pa.array(
            [json.dumps(it.metadata or {}) for it in run.items],
            type=pa.string(),
        ),
    }
    return pa.Table.from_pydict(columns, schema=PARQUET_SCHEMA)


def write_runframe_parquet(run: RunFrame, path: str | Path, *,
                          project_id: str = "default") -> None:
    """Write a RunFrame to a Parquet file using the canonical schema."""
    table = runframe_to_table(run, project_id=project_id)
    pq.write_table(table, str(path), compression="snappy")


def read_runframe_parquet(path: str | Path, *,
                          run_id: Optional[str] = None) -> RunFrame:
    """Read a RunFrame from Parquet.

    If the file holds multiple runs, pass `run_id` to filter. Otherwise
    we use the first (and only) run found.
    """
    table = pq.read_table(str(path))
    if run_id is not None:
        mask = pa.compute.equal(table["run_id"], run_id)
        table = table.filter(mask)
        if table.num_rows == 0:
            raise ValueError(f"run_id={run_id} not found in {path}")

    run_ids = table["run_id"].unique().to_pylist()
    if len(run_ids) > 1:
        raise ValueError(
            f"{path} contains {len(run_ids)} runs; pass run_id to disambiguate"
        )
    items = []
    for i in range(table.num_rows):
        meta_raw = table["metadata_json"][i].as_py()
        meta = json.loads(meta_raw) if meta_raw else {}
        items.append(ItemResult(
            item_id=table["item_id"][i].as_py(),
            score=float(table["score"][i].as_py()),
            cluster_id=table["cluster_id"][i].as_py(),
            epoch=int(table["epoch"][i].as_py()),
            metadata=meta,
        ))
    return RunFrame(
        run_id=table["run_id"][0].as_py(),
        model_id=table["model_id"][0].as_py(),
        task_id=table["task_id"][0].as_py(),
        metric_name=table["metric_name"][0].as_py(),
        config_hash=table["config_hash"][0].as_py(),
        items=items,
    )
