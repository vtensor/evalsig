"""Readers and writers for every input format evalsig accepts."""
from evalsig.io.base import (
    Reader,
    available_formats,
    get_reader,
    register_reader,
)
from evalsig.io.json_runframe import (
    read_runframe_json,
    write_runframe_json,
    RUNFRAME_SCHEMA,
)
from evalsig.io.lm_eval import read_lm_eval_json
from evalsig.io.inspect_log import read_inspect_log
from evalsig.io.helm import read_helm_scenario
from evalsig.io.parquet import (
    read_runframe_parquet,
    write_runframe_parquet,
    runframe_to_table,
    PARQUET_SCHEMA,
)
from evalsig.io.normalize import normalize


# Wire all built-in readers into the registry so the CLI and other code
# can resolve them by name.
register_reader("runframe", read_runframe_json)
register_reader("lm_eval", lambda p, **kw: read_lm_eval_json(
    p,
    model_id=kw.get("model_id") or "model",
    task_id=kw.get("task_id") or "task",
    metric_name=kw.get("metric_name", "acc"),
    cluster_key=kw.get("cluster_key"),
))
register_reader("inspect", read_inspect_log)
register_reader("helm", read_helm_scenario)
register_reader("parquet", read_runframe_parquet)


__all__ = [
    "Reader",
    "available_formats",
    "get_reader",
    "register_reader",
    "read_runframe_json",
    "write_runframe_json",
    "RUNFRAME_SCHEMA",
    "read_lm_eval_json",
    "read_inspect_log",
    "read_helm_scenario",
    "read_runframe_parquet",
    "write_runframe_parquet",
    "runframe_to_table",
    "PARQUET_SCHEMA",
    "normalize",
]
