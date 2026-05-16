"""Reader for lm-evaluation-harness output files.

lm-eval-harness writes per-task `samples_*.jsonl` files. We pull item id,
score, and (optionally) a cluster key from each record. The reader is
forgiving because the exact field name for the score varies by task.
"""
from __future__ import annotations

import json
from pathlib import Path

from evalsig.types import ItemResult, RunFrame


def _coerce_score(rec: dict, metric_name: str) -> float | None:
    # First try the metric the user asked for. If it isn't there, fall
    # back to the common names lm-eval-harness uses.
    if metric_name in rec:
        v = rec[metric_name]
        if isinstance(v, (int, float)):
            return float(v)
    for key in ("acc", "exact_match", "score", "is_correct"):
        if key in rec and isinstance(rec[key], (int, float, bool)):
            return float(rec[key])
    return None


def read_lm_eval_json(
    path: str | Path,
    *,
    model_id: str,
    task_id: str,
    metric_name: str = "acc",
    cluster_key: str | None = None,
) -> RunFrame:
    """Load a single-task samples file from lm-evaluation-harness.

    `cluster_key`, if given, is the metadata field on each sample that
    names its cluster (for example 'category', 'subject', 'passage_id').
    """
    path = Path(path)
    text = path.read_text()
    # JSONL files have one record per line. A single JSON document may
    # be either a list of records or an object with a 'samples' field.
    records: list[dict] = []
    if path.suffix == ".jsonl" or "\n{" in text.strip():
        for line in text.splitlines():
            line = line.strip()
            if line:
                records.append(json.loads(line))
    else:
        obj = json.loads(text)
        if isinstance(obj, list):
            records = obj
        elif isinstance(obj, dict) and "samples" in obj:
            records = obj["samples"]
        else:
            # results.json with no item-level data. Tell the user where
            # to look instead.
            raise ValueError(
                f"{path} does not contain item-level samples; "
                "pass the samples_*.jsonl file instead"
            )

    items: list[ItemResult] = []
    for i, rec in enumerate(records):
        item_id = str(rec.get("doc_id", rec.get("idx", i)))
        score = _coerce_score(rec, metric_name)
        if score is None:
            continue
        cluster_id = None
        if cluster_key is not None:
            meta = rec.get("doc", rec)
            v = meta.get(cluster_key) if isinstance(meta, dict) else None
            cluster_id = None if v is None else str(v)
        items.append(ItemResult(
            item_id=item_id, score=score, cluster_id=cluster_id, epoch=0,
        ))
    if not items:
        raise ValueError(
            f"no items with metric '{metric_name}' found in {path}"
        )
    return RunFrame(
        run_id=f"{model_id}::{task_id}",
        model_id=model_id, task_id=task_id, metric_name=metric_name,
        items=items,
    )
