# Python API

The public surface follows the design-doc commitment: three names cover
80% of usage, and submodules cover the rest.

```python
from evalsig import compare, gate, mde
```

For everything else, reach into the submodules. Each one is documented
under [Modules](../modules/types.md).

## The five-line tutorial

```python
from evalsig import compare
from evalsig.io import read_runframe_json

a = read_runframe_json("baseline.json")
b = read_runframe_json("candidate.json")
result = compare(a, b, alpha=0.05, one_sided=True)
print(result.delta, result.p_value, result.significant)
```

## Reading runs

The IO layer ships readers for every common format. Each one returns a
`RunFrame`.

```python
from evalsig.io import (
    read_runframe_json,    # EVALSIG's native JSON
    read_lm_eval_json,     # lm-evaluation-harness samples_*.jsonl
    read_inspect_log,      # Inspect AI JSON export
    read_helm_scenario,    # HELM scenario_state.json
    read_runframe_parquet, # EVALSIG Parquet
)

a = read_inspect_log("baseline.eval")
b = read_lm_eval_json("samples_mmlu.jsonl",
                      model_id="claude-x", task_id="mmlu",
                      metric_name="acc", cluster_key="subject")
```

If you have a custom harness, write a small reader that returns a
`RunFrame` and register it:

```python
from evalsig.io import register_reader
from evalsig.types import RunFrame, ItemResult

def read_my_format(path, **kw) -> RunFrame:
    ...

register_reader("my_format", read_my_format)
```

The CLI will then accept `--format my_format`.

## Comparing two runs

```python
from evalsig import compare

result = compare(
    a, b,
    method="auto",                # or 'paired_permutation' / 'mcnemar' / ...
    cluster="passage_id",         # opt into cluster-aware inference
    alpha=0.05,
    one_sided=True,               # candidate > baseline
    target_power=0.80,
    n_resamples=10_000,
    rng=42,
)
```

The returned `ComparisonResult` is a frozen dataclass:

```python
result.delta            # 0.0124
result.ci               # (0.0023, +inf)
result.p_value          # 0.0070
result.significant      # True
result.n_pairs          # 4032
result.n_clusters       # 1008 or None
result.method           # 'paired_permutation'
result.mde              # 0.0040
result.notes            # ()
result.to_dict()        # JSON-friendly view
```

## Gating a release

```python
from evalsig import gate

report = gate(
    a, b,
    min_delta=0.005,
    alpha=0.05,
    power=0.80,
    method="auto",
    cluster="passage_id",
    one_sided=True,
)

report.verdict          # GateVerdict.ALLOW / REJECT / INCONCLUSIVE
report.exit_code        # 0 / 1 / 2
report.comparison       # the underlying ComparisonResult
report.suggestion       # human-readable next step, or None
report.to_dict()        # JSON-friendly view
```

## Computing MDE and required N

```python
from evalsig import mde, required_n

# Given a run, what's the smallest detectable effect?
out = mde(sd_diff=0.30, n_pairs=1000, alpha=0.05, power=0.80,
          one_sided=True, n_clusters=100, icc=0.15)
print(out.mde, out.deff)

# Given a target effect, how many items do you need?
n = required_n(target_delta=0.01, sd_diff=0.30,
               icc=0.15, mean_cluster_size=10,
               alpha=0.05, power=0.80, one_sided=True)
print(n)
```

## Effect sizes

```python
from evalsig import cohens_d, cohens_d_paired, cliffs_delta
import numpy as np

a = np.array([it.score for it in run_a.items])
b = np.array([it.score for it in run_b.items])

print(cohens_d_paired(a, b))   # paired d (use when items are paired)
print(cliffs_delta(a, b))       # ordinal effect size
```

## Multiple comparisons

```python
from evalsig import bonferroni, holm, benjamini_hochberg
import numpy as np

p = np.array([0.001, 0.008, 0.03, 0.04, 0.18])
out = holm(p, alpha=0.05)
print(out.p_adjusted)
print(out.reject)
```

## Sequential testing

```python
from evalsig import sequential_gate

stream = (b - a for a, b in paired_scores())   # any iterable of floats
out = sequential_gate(stream, alpha=0.05, alternative="greater", min_n=30)
print(out.stopped, out.n_pairs, out.delta)
```

## Writing to the store

```python
from evalsig.store import write_run, RunStoreWriter

write_run("/path/to/store", run, project_id="mmlu-pro",
          delta=0.012, p_value=0.04, verdict="ALLOW")

# Or batch writes with a context manager:
with RunStoreWriter("/path/to/store", project_id="mmlu-pro") as w:
    for run in many_runs:
        w.write(run)
```

## Reading reports back as JSON / Markdown / TTY

```python
from evalsig import to_json, to_markdown, to_tty

print(to_markdown(report))      # PR comment
print(to_json(report))          # dashboards
print(to_tty(report))           # logs
```

## See also

* [CLI reference](cli.md): every subcommand and flag.
* [Configuration](configuration.md): defaults, environment variables.
* [Modules](../modules/types.md): every public type and function.
