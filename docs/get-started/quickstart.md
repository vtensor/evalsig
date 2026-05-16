# Quickstart

This page gets you from `pip install` to a working release gate in 30
seconds. For a longer, hand-held walkthrough, see [Your first comparison](first-comparison.md).

## 1. Install

```bash
pip install evalsig
```

## 2. Write two runs as RunFrame JSON

EVALSIG's native format is one JSON file per run. Each item carries an id,
a score, and optionally a `cluster_id` (for example a passage or template).

```json title="baseline.json"
{
  "run_id": "claude-x::mmlu-pro",
  "model_id": "claude-x",
  "task_id": "mmlu-pro",
  "metric_name": "accuracy",
  "items": [
    {"item_id": "q1", "score": 1.0, "cluster_id": "stem"},
    {"item_id": "q2", "score": 0.0, "cluster_id": "stem"},
    {"item_id": "q3", "score": 1.0, "cluster_id": "humanities"}
  ]
}
```

You can also read native [Inspect AI](../modules/io.md#read_inspect_log) `.eval`
logs, [lm-eval-harness](../modules/io.md#read_lm_eval_json) `samples_*.jsonl`,
or [HELM](../modules/io.md#read_helm_scenario) `scenario_state.json` files
without any conversion.

## 3. Gate the release from the CLI

```bash
evalsig gate \
  --baseline baseline.json \
  --candidate candidate.json \
  --metric accuracy \
  --min-delta 0.005 \
  --alpha 0.05 \
  --power 0.80
```

You'll see something like:

```
EVALSIG release gate
====================
delta:         +0.0124  (paired_permutation)
CI (95%):      [+0.0023, +inf]
p-value:       0.0070
required MDE:  0.0050
detectable:    0.0040 at 80% power

VERDICT: ALLOW
```

The exit code is `0` (ALLOW), `1` (REJECT), or `2` (INCONCLUSIVE), so CI
systems can read the verdict without parsing stdout. See
[Understanding the output](understanding-output.md) for what each field means.

## 4. Or use the Python API

```python
from evalsig import compare, gate
from evalsig.io import read_runframe_json

a = read_runframe_json("baseline.json")
b = read_runframe_json("candidate.json")

result = compare(a, b, alpha=0.05, one_sided=True)
print(result.delta, result.p_value, result.significant)

report = gate(a, b, min_delta=0.005, alpha=0.05, power=0.80)
print(report.verdict.value)  # 'ALLOW' / 'REJECT' / 'INCONCLUSIVE'
```

## 5. Wire it into CI

The shipped GitHub Action runs the same gate and writes a Markdown summary
into the workflow run:

```yaml
- uses: vtensor/evalsig@v0.1
  with:
    baseline: baseline.json
    candidate: candidate.json
    metric: accuracy
    min_delta: '0.005'
    alpha: '0.05'
    power: '0.80'
```

Or use the pytest plugin, which fails the test with the full Markdown report
when the gate refuses to ship:

```python
def test_no_regression(evalsig_gate):
    a = evalsig_gate.load("baseline.json")
    b = evalsig_gate.load("candidate.json")
    evalsig_gate.assert_no_regression(a, b, min_delta=0.005)
```

## What just happened

EVALSIG aligned the two runs on `item_id`, picked a paired statistical test
based on the data shape (binary scores -> McNemar, continuous -> paired
permutation, clustered -> cluster bootstrap), computed the delta, the
confidence interval, the p-value, and the minimum detectable effect, then
compared the result to your `--min-delta` policy.

For the full reasoning chain see [Concepts](../concepts/what-evalsig-solves.md).
For every knob, see [CLI reference](../usage/cli.md) and
[Python API](../usage/python-api.md).
