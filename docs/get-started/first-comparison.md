# Your first comparison

This page walks you through a full release-gate comparison, step by step,
with explanations of every choice. By the end you will:

1. Understand what fields a RunFrame needs.
2. Run a comparison with the Python API.
3. Read the output and know what to do with it.
4. Wire the comparison into a CI job.

Total time: about 15 minutes.

## 1. The data shape

EVALSIG works with two runs at a time: a baseline and a candidate. Each run
is a `RunFrame`, the canonical in-memory and on-disk shape:

```python
from evalsig.types import RunFrame, ItemResult

baseline = RunFrame(
    run_id="claude-x::mmlu-pro",
    model_id="claude-x",
    task_id="mmlu-pro",
    metric_name="accuracy",
    items=[
        ItemResult(item_id="q1", score=1.0, cluster_id="stem"),
        ItemResult(item_id="q2", score=0.0, cluster_id="stem"),
        ItemResult(item_id="q3", score=1.0, cluster_id="humanities"),
    ],
)
```

Three fields matter for inference:

* `item_id` lines the two runs up. EVALSIG pairs items by id, not by
  position. If the candidate skipped an item, that is fine; we work with
  the intersection.
* `score` is the per-item metric. 0/1 binary is the most common case, but
  any float works.
* `cluster_id` is optional. Set it whenever items belong to a group that
  moves together (a passage with several questions, a template that spawns
  many problems). Cluster-aware inference will widen the confidence interval
  to reflect the within-group correlation.

For the rest of this page we'll generate two synthetic runs so you can
follow along even without an eval harness on hand.

## 2. Make two runs

We'll build a baseline and a candidate where the candidate is genuinely
2 percentage points better, on the same items.

```python
import numpy as np
from evalsig.types import RunFrame, ItemResult

rng = np.random.default_rng(0)
n = 1000
theta = rng.beta(4, 2, size=n)        # per-item difficulty
c = rng.random(size=n)                # shared per-item luck

base_scores = (c < theta).astype(float)
cand_scores = (c < np.clip(theta + 0.02, 0, 1)).astype(float)

def to_run(model: str, scores):
    return RunFrame(
        run_id=f"{model}::demo",
        model_id=model,
        task_id="demo",
        metric_name="accuracy",
        items=[
            ItemResult(item_id=f"q{i:04d}", score=float(scores[i]))
            for i in range(n)
        ],
    )

baseline = to_run("model-A", base_scores)
candidate = to_run("model-B", cand_scores)
```

In real life you would substitute one of the IO readers:

```python
from evalsig.io import read_inspect_log, read_lm_eval_json, read_helm_scenario
baseline = read_inspect_log("baseline.eval")
candidate = read_inspect_log("candidate.eval")
```

## 3. Run the comparison

```python
from evalsig import compare

result = compare(baseline, candidate, alpha=0.05, one_sided=True)

print(result.delta)         # 0.0218   (2.18pp)
print(result.ci)            # (0.0151, +inf)
print(result.p_value)       # 6e-09 or similar
print(result.significant)   # True
print(result.method)        # 'mcnemar_exact' (auto-chosen for binary)
print(result.mde)           # 0.0096
```

A handful of things just happened:

* EVALSIG aligned the two runs on `item_id`.
* It detected that both runs are 0/1, with no cluster ids, and picked
  McNemar's exact test as the auto method.
* It computed the delta, a one-sided 95% confidence interval, and the
  smallest delta you could have detected at 80% power. The MDE here is
  0.96pp; our 2.18pp observed delta is well above that, so the run is
  adequately powered.
* It returned a frozen `ComparisonResult` so the same number cannot drift
  out from under you.

## 4. Run the gate

The gate adds a policy: how big does the effect have to be to ship?

```python
from evalsig import gate

report = gate(baseline, candidate, min_delta=0.01, alpha=0.05, power=0.80)
print(report.verdict.value)   # 'ALLOW'
print(report.exit_code)       # 0
print(report.suggestion)      # None (no remedial action needed)
```

Three possible verdicts:

| Verdict | When | Exit code |
|---|---|---|
| `ALLOW` | significant and observed delta >= min_delta | 0 |
| `REJECT` | not significant (or significant but below min_delta) | 1 |
| `INCONCLUSIVE` | not significant AND the run was too small to detect min_delta | 2 |

`INCONCLUSIVE` is the most useful one: it tells the user that more data
would actually help. EVALSIG prints how many more items they would need to
collect to reach the requested MDE.

## 5. CLI version

Everything above is also a one-liner from the shell:

```bash
evalsig gate \
  --baseline baseline.json \
  --candidate candidate.json \
  --metric accuracy \
  --min-delta 0.01 \
  --alpha 0.05 \
  --power 0.80 \
  --one-sided
```

The exit code matches the verdict, so CI systems can branch off it.

## Next

* [Understanding the output](understanding-output.md) explains every field
  on a `ComparisonResult`.
* [Paired vs unpaired](../concepts/paired-vs-unpaired.md) explains why the
  paired test is so much tighter than the obvious alternatives.
* [CLI reference](../usage/cli.md) lists every flag, subcommand, and exit
  code.
