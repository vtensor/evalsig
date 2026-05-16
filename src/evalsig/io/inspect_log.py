"""Reader for Inspect AI logs.

Inspect's native log format is binary `.eval`. To avoid pulling in the
full `inspect_ai` package, this reader takes the JSON export produced by
`inspect log export`. The export has `samples` with `id`,
`score.value`, and `metadata`, which is everything we need.
"""
from __future__ import annotations

import json
from pathlib import Path

from evalsig.types import ItemResult, RunFrame


def read_inspect_log(
    path: str | Path,
    *,
    metric_name: str = "accuracy",
    cluster_key: str | None = None,
) -> RunFrame:
    """Load an Inspect AI exported log into a RunFrame."""
    path = Path(path)
    obj = json.loads(path.read_text())
    eval_meta = obj.get("eval", {})
    model_id = eval_meta.get("model", obj.get("model", "unknown"))
    task_id = eval_meta.get("task", obj.get("task", path.stem))
    run_id = obj.get("eval_id", f"{model_id}::{task_id}")

    samples = obj.get("samples", [])
    items: list[ItemResult] = []
    for i, s in enumerate(samples):
        item_id = str(s.get("id", i))
        score_obj = s.get("score", {})
        # Inspect stores the score in several shapes: a string like "C"
        # or "I", a bool, or a number. Map all of them to a float.
        v = score_obj.get("value") if isinstance(score_obj, dict) else score_obj
        if isinstance(v, str):
            score = 1.0 if v.upper() in ("C", "CORRECT", "TRUE", "1") else 0.0
        elif isinstance(v, bool):
            score = 1.0 if v else 0.0
        elif isinstance(v, (int, float)):
            score = float(v)
        else:
            continue
        cluster_id = None
        if cluster_key is not None:
            meta = s.get("metadata", {})
            v = meta.get(cluster_key) if isinstance(meta, dict) else None
            cluster_id = None if v is None else str(v)
        items.append(ItemResult(
            item_id=item_id, score=score, cluster_id=cluster_id, epoch=0,
        ))
    if not items:
        raise ValueError(f"no items decoded from {path}")
    return RunFrame(
        run_id=run_id, model_id=str(model_id), task_id=str(task_id),
        metric_name=metric_name, items=items,
    )
