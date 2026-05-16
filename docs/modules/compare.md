# `evalsig.compare`

The orchestration layer. Picks a test, runs the inference primitives,
and shapes the output.

## `compare()`

The top-level function. 80% of users only ever touch this and `gate()`.

```python
from evalsig import compare

result = compare(
    a, b,
    method="auto",
    cluster=None,
    alpha=0.05,
    one_sided=False,
    target_power=0.80,
    n_resamples=10_000,
    rng=0,
)
```

Returns a `ComparisonResult`.

The auto-method rules:

* both runs 0/1, no clusters -> `mcnemar`
* clusters provided -> `cluster_bootstrap`
* otherwise -> `paired_permutation`

## `gate()`

Wraps `compare()` with a release policy.

```python
from evalsig import gate

report = gate(
    a, b,
    min_delta=0.005,
    alpha=0.05,
    power=0.80,
    method="auto",
    cluster=None,
    one_sided=True,
    n_resamples=10_000,
    rng=0,
)
```

Returns a `GateReport(verdict, exit_code, comparison, min_delta, alpha,
power, suggestion)`.

Verdict logic:

| Condition | Verdict |
|---|---|
| significant and `delta >= min_delta` | `ALLOW` (exit 0) |
| not significant and `mde > min_delta` | `INCONCLUSIVE` (exit 2) |
| anything else | `REJECT` (exit 1) |

The `suggestion` field is populated only for `INCONCLUSIVE` (with the
required-N estimate) and `REJECT` (when a real but tiny effect was
detected).

## `align_runs()`

Lines up two RunFrames on `item_id`.

```python
from evalsig.compare import align_runs
sa, sb, clusters, notes = align_runs(a, b)
```

Returns four things:

* `sa` -- baseline scores as a numpy array.
* `sb` -- candidate scores, aligned.
* `clusters` -- cluster ids, or `None` if neither run carries them.
* `notes` -- warnings to surface to the user (coverage below 95%,
  cluster mismatches, etc.).

## Renderers

```python
from evalsig.compare import to_json, to_markdown, to_tty
```

Each takes either a `ComparisonResult` or a `GateReport`. See
[Output formats](../usage/output-formats.md) for examples of all three.

## Why orchestration is a separate module

The `compare/` layer is the only place a method is *chosen*. Everything
underneath (`inference/`) just *does* the math. Pulling the choice up
keeps the math testable and keeps the decision logic in one place.

## See also

* [Python API](../usage/python-api.md): the typed function signatures.
* [Modules: inference](inference.md): what gets dispatched to.
* [Output formats](../usage/output-formats.md): the renderers.
