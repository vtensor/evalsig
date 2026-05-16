# Scenario: flakiness detection

You re-ran the same model on the same eval twice with no other change,
and the aggregate score moved by 2 percentage points. Was that
infrastructure noise or a real config drift?

This is exactly the scenario the Anthropic Engineering blog quantified
on Terminal-Bench (a 6pp swing from infra config alone). EVALSIG's
paired test is the right diagnostic.

## The setup

Run the eval twice, with the same model, ideally on identical
hardware:

```bash
your-eval --model claude-x --run-id run-A > run-A.json
your-eval --model claude-x --run-id run-B > run-B.json
```

Then compare:

```python
from evalsig import compare
from evalsig.io import read_runframe_json

a = read_runframe_json("run-A.json")
b = read_runframe_json("run-B.json")
result = compare(a, b, alpha=0.05)
print(result.delta, result.p_value, result.method, result.notes)
```

## What you expect

If the deltas are truly infrastructure noise, the per-item differences
average to roughly zero with high variance (most items agree, a few
flip at random). The paired test gives a large p-value, a CI straddling
zero, and the gate would return REJECT or INCONCLUSIVE.

If the swing is a real config drift (different temperature, different
batch size, different decoder), the per-item differences are
systematically positive or negative for a particular subset of items,
the paired CI excludes zero, and the gate fires.

## A reproducible synthetic example

```python
import numpy as np
from evalsig.types import RunFrame, ItemResult
from evalsig import compare

rng = np.random.default_rng(0)
n = 6000

# Most items deterministic; a fraction borderline.
theta = rng.beta(5, 2, size=n)
is_stoch = rng.random(n) < 0.20
c = rng.random(n)
y_a = (c < theta).astype(float)
y_b = y_a.copy()
n_s = int(is_stoch.sum())
y_a[is_stoch] = (rng.random(n_s) < 0.5).astype(float)
y_b[is_stoch] = (rng.random(n_s) < 0.5).astype(float)

def to_run(model, scores):
    return RunFrame(run_id=f"{model}::tb", model_id=model,
                    task_id="terminal-bench", metric_name="accuracy",
                    items=[ItemResult(item_id=f"i{i}", score=float(scores[i]))
                           for i in range(n)])

result = compare(to_run("config-a", y_a), to_run("config-b", y_b))
print(result.delta, result.p_value, result.significant)
```

Run a few times with different seeds. You will see aggregate deltas of
a few pp, p-values above 0.05, and the gate refusing to ship -- which
is the correct call.

## How EVALSIG's research validation backs this up

The validation script (`research/validate.py`) includes this exact
scenario as `experiment_4_cli_gate.infra_noise`. With 6,000 items and
20% borderline, the CLI gate returns REJECT (delta -0.30pp, p = 0.78).
See [Methodology](../methodology.md) for the full Monte Carlo write-up.

## What you should not do

* **Don't conclude "we have noise" from a single run.** Run it twice
  more with different infra configs to triangulate.
* **Don't switch to a tighter alpha to make the answer look better.**
  Alpha is your false-positive rate; tightening it makes the gate
  conservative, not more correct.

## See also

* [Concepts: paired vs unpaired](../concepts/paired-vs-unpaired.md)
* [Methodology](../methodology.md): the infra-noise simulation results.
