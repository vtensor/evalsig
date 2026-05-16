# `evalsig.store`

An append-only run history on top of Parquet plus a small JSON
manifest. Optional: the gates work fine without it. Use it when you
want history, trend analysis, or a compliance trail.

## Layout

```
{root}/{project}/year=YYYY/month=MM/run_id={run_id}.parquet
{root}/{project}/manifest.json
```

The manifest is a single JSON file with one record per run. We keep it
flat because manifests stay small (one row per run, not per item) and
JSON is friendliest for git-tracked stores.

## Writing

```python
from evalsig.store import write_run, RunStoreWriter

# One-shot write:
write_run(
    "/path/to/store",
    run,
    project_id="mmlu-pro",
    delta=0.012,
    p_value=0.04,
    verdict="ALLOW",
)

# Many-shot writes share a manifest open:
with RunStoreWriter("/path/to/store", project_id="mmlu-pro") as w:
    for run in many_runs:
        w.write(run, delta=..., verdict=...)
```

`RunStoreWriter` flushes the manifest on `__exit__` (or when you call
`commit()` explicitly).

## Reading

```python
from evalsig.store import list_runs, load_run, query_runs

# List everything in a project:
for h in list_runs("/path/to/store", project_id="mmlu-pro"):
    print(h.record.run_id, h.record.delta, h.record.verdict)

# Filtered query:
runs = query_runs(
    "/path/to/store",
    project_id="mmlu-pro",
    model_id="claude-x",
    since="2026-01-01T00:00:00+00:00",
)

# Pull the full RunFrame back:
rf = load_run("/path/to/store", "claude-x::mmlu-pro::run-42",
              project_id="mmlu-pro")
```

`list_runs` and `query_runs` return `RunHistoryRecord` (a manifest
record plus the absolute path).

## The CLI

`evalsig history` wraps the read side:

```bash
evalsig history --root .evalsig/store --project mmlu-pro --model-id claude-x
```

## Schema stability

The Parquet schema (exposed as `evalsig.io.PARQUET_SCHEMA`) is part of
the public API and is stable across the 0.x line. Manifest fields
follow the same rule.

## When not to use the store

* You already have a data warehouse and want to push there directly.
  Skip the store and pipe `--output json` into your ingestion pipeline.
* You're running one-off gates in CI with no history requirement. The
  store is dead weight in that case.

The pattern we recommend is: SaaS dashboards or your warehouse for
shared history, the local store for per-project per-machine archives
that survive `git clean`.

## See also

* [Modules: io.parquet](io.md#read_runframe_parquet-write_runframe_parquet)
  for the read/write primitives the store sits on.
* [Scenarios: compliance audit trail](../scenarios/compliance-audit-trail.md)
  for a worked end-to-end example.
