"""Reader for HELM scenario state.

HELM (Holistic Evaluation of Language Models) writes per-instance results
into a `scenario_state.json` file inside each run directory. The file
contains a `request_states` list where each entry has an instance id
plus a `result.success` field used as the per-item score.

This reader extracts those fields and produces a RunFrame. Real HELM
runs can be very large (10k+ items per scenario); we stream the JSON
parse rather than holding the parsed dict in memory twice.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from evalsig.types import ItemResult, RunFrame


def read_helm_scenario(
    path: str | Path,
    *,
    model_id: Optional[str] = None,
    task_id: Optional[str] = None,
    metric_name: str = "accuracy",
    cluster_key: Optional[str] = None,
) -> RunFrame:
    """Load a HELM scenario_state.json into a RunFrame."""
    path = Path(path)
    obj = json.loads(path.read_text())
    inferred_model = (
        obj.get("adapter_spec", {}).get("model")
        or obj.get("adapter_spec", {}).get("model_deployment")
        or "unknown"
    )
    inferred_task = (
        obj.get("scenario", {}).get("name")
        or obj.get("scenario_spec", {}).get("class_name", path.stem)
    )
    model_id = model_id or inferred_model
    task_id = task_id or inferred_task

    request_states = obj.get("request_states", [])
    items: list[ItemResult] = []
    for i, rs in enumerate(request_states):
        instance = rs.get("instance", {})
        item_id = str(instance.get("id", i))
        # Score: HELM normalises to result.success (bool) or
        # result.stats[metric_name] (number).
        score: Optional[float] = None
        result = rs.get("result", {})
        if metric_name in result:
            v = result[metric_name]
            if isinstance(v, (int, float, bool)):
                score = float(v)
        if score is None and "success" in result:
            score = 1.0 if result["success"] else 0.0
        if score is None and "stats" in result:
            stats_obj = result["stats"]
            if isinstance(stats_obj, dict) and metric_name in stats_obj:
                v = stats_obj[metric_name]
                if isinstance(v, (int, float, bool)):
                    score = float(v)
        if score is None:
            continue

        cluster_id = None
        if cluster_key is not None:
            v = instance.get(cluster_key)
            cluster_id = None if v is None else str(v)

        items.append(ItemResult(
            item_id=item_id, score=score, cluster_id=cluster_id, epoch=0,
        ))

    if not items:
        raise ValueError(
            f"no items decoded from {path} for metric '{metric_name}'"
        )
    return RunFrame(
        run_id=f"{model_id}::{task_id}",
        model_id=str(model_id),
        task_id=str(task_id),
        metric_name=metric_name,
        items=items,
    )
