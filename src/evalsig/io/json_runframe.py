"""Reader and writer for EVALSIG's own JSON format.

A hand-rolled validator runs first, so bad inputs fail fast with a clear
message. Any harness can emit this format; it's the canonical exchange
shape.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from evalsig.types import ItemResult, RunFrame


# The schema we accept. Published as run.v1.json once the package goes
# out; only backward-compatible additions are allowed past v1.
RUNFRAME_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "EVALSIG RunFrame v1",
    "type": "object",
    "required": ["run_id", "model_id", "task_id", "metric_name", "items"],
    "properties": {
        "run_id": {"type": "string"},
        "model_id": {"type": "string"},
        "task_id": {"type": "string"},
        "metric_name": {"type": "string"},
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["item_id", "score"],
                "properties": {
                    "item_id": {"type": "string"},
                    "cluster_id": {"type": ["string", "null"]},
                    "epoch": {"type": "integer", "minimum": 0},
                    "score": {"type": "number"},
                    "metadata": {"type": "object"},
                },
            },
        },
        "config_hash": {"type": "string"},
    },
}


class SchemaError(ValueError):
    pass


def _validate(obj: dict[str, Any]) -> None:
    # Lightweight check that all required fields are there with the
    # right types. We don't pull in a full JSON-Schema library for v1.
    required = RUNFRAME_SCHEMA["required"]
    for key in required:
        if key not in obj:
            raise SchemaError(f"missing required field: {key}")
    if not isinstance(obj["items"], list) or not obj["items"]:
        raise SchemaError("'items' must be a non-empty array")
    for i, it in enumerate(obj["items"]):
        if "item_id" not in it or "score" not in it:
            raise SchemaError(f"item[{i}] missing item_id or score")
        if not isinstance(it["score"], (int, float)):
            raise SchemaError(f"item[{i}].score must be a number, got {type(it['score']).__name__}")


def read_runframe_json(path: str | Path) -> RunFrame:
    """Load a RunFrame from EVALSIG's JSON format."""
    path = Path(path)
    obj = json.loads(path.read_text())
    _validate(obj)
    items = [
        ItemResult(
            item_id=str(it["item_id"]),
            score=float(it["score"]),
            cluster_id=it.get("cluster_id"),
            epoch=int(it.get("epoch", 0)),
            metadata=it.get("metadata", {}),
        )
        for it in obj["items"]
    ]
    return RunFrame(
        run_id=str(obj["run_id"]),
        model_id=str(obj["model_id"]),
        task_id=str(obj["task_id"]),
        metric_name=str(obj["metric_name"]),
        items=items,
        config_hash=str(obj.get("config_hash", "")),
    )


def write_runframe_json(run: RunFrame, path: str | Path) -> None:
    """Write a RunFrame to disk in the canonical JSON format."""
    payload = {
        "run_id": run.run_id,
        "model_id": run.model_id,
        "task_id": run.task_id,
        "metric_name": run.metric_name,
        "config_hash": run.config_hash,
        "items": [
            {
                "item_id": it.item_id,
                "score": it.score,
                "cluster_id": it.cluster_id,
                "epoch": it.epoch,
                "metadata": it.metadata,
            }
            for it in run.items
        ],
    }
    Path(path).write_text(json.dumps(payload, indent=2))
