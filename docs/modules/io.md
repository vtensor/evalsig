# `evalsig.io`

Readers and writers for every input format EVALSIG accepts. Each reader
returns a `RunFrame`.

## Reader registry

```python
from evalsig.io import register_reader, get_reader, available_formats
```

* `register_reader(name, reader)` -- add a new format under a short
  name.
* `get_reader(name)` -- look one up.
* `available_formats()` -- list everything currently registered.

The built-in registrations happen at import time: `runframe`, `lm_eval`,
`inspect`, `helm`, `parquet`.

## `read_runframe_json` / `write_runframe_json`

EVALSIG's own JSON format, the canonical exchange shape.

```python
from evalsig.io import read_runframe_json, write_runframe_json
run = read_runframe_json("baseline.json")
write_runframe_json(run, "out.json")
```

The schema is exported as `RUNFRAME_SCHEMA` (JSON Schema draft 2020-12).
The validator is lightweight and runs before any RunFrame is
constructed, so bad inputs fail fast with a clear message.

## `read_lm_eval_json`

Reads `samples_*.jsonl` from EleutherAI's `lm-evaluation-harness`.

```python
run = read_lm_eval_json(
    "samples_mmlu_2026-05-16.jsonl",
    model_id="claude-x",
    task_id="mmlu",
    metric_name="acc",         # or 'exact_match', 'is_correct', etc.
    cluster_key="subject",     # optional; field on the doc to group by
)
```

Resilient to several variants of the format (a list of dicts, a
samples-wrapping dict, JSONL).

## `read_inspect_log`

Reads JSON exports of Inspect AI `.eval` logs. Run
`inspect log export run.eval > run.json` first.

```python
run = read_inspect_log("run.json",
                       metric_name="accuracy",
                       cluster_key="passage_id")
```

Handles the common `score.value` shapes (`"C"`/`"I"`, booleans,
numbers).

## `read_helm_scenario`

Reads HELM's `scenario_state.json`.

```python
run = read_helm_scenario("scenario_state.json",
                         metric_name="accuracy",
                         cluster_key="category")
```

Pulls `result.success` (bool) by default, falls back to a numeric
metric in `result[metric_name]` or `result.stats[metric_name]`.

## `read_runframe_parquet` / `write_runframe_parquet`

The long-term storage format. One row per (run, item, epoch). Use the
canonical `PARQUET_SCHEMA` (also exported) when writing your own
ingestion paths.

```python
from evalsig.io import read_runframe_parquet, write_runframe_parquet
write_runframe_parquet(run, "run.parquet")
back = read_runframe_parquet("run.parquet")
```

If a file holds multiple runs, pass `run_id=` to disambiguate.

## `normalize`

Convenience wrapper for callers that want to import the alignment
helper from `evalsig.io.normalize` rather than `evalsig.compare.compare`.
Returns the aligned arrays plus any warning notes.

## Writing your own reader

Any function that turns a path into a `RunFrame` is a reader.

```python
from evalsig.io import register_reader
from evalsig.types import RunFrame, ItemResult

def read_my_format(path: str, **kw) -> RunFrame:
    rows = my_parser(path)
    return RunFrame(
        run_id=kw.get("run_id", path),
        model_id=kw.get("model_id", "unknown"),
        task_id=kw.get("task_id", "unknown"),
        metric_name=kw.get("metric_name", "accuracy"),
        items=[
            ItemResult(item_id=str(r["id"]),
                       score=float(r["score"]),
                       cluster_id=r.get("group"))
            for r in rows
        ],
    )

register_reader("my_format", read_my_format)
```

The CLI's `--format` will then accept `my_format`.

## See also

* [Configuration](../usage/configuration.md) for format selection on
  the command line.
* [Methodology](../methodology.md) for the schema rationale.
