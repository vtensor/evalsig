# EVALSIG

**Know whether your LLM eval gains are real or just noise. Catch it in CI, before shipping.**

EVALSIG sits between any LLM eval harness (Inspect AI, lm-eval-harness, HELM,
simple-evals, your internal pipeline) and the decision to ship a model. It
applies the statistical machinery the academic literature has spent the last
two years recommending but no commercial tool ships end-to-end: paired-
difference testing, clustered standard errors, permutation tests, minimum-
detectable-effect / power analysis, always-valid sequential monitoring, and
multiple-comparison corrections.

## The problem in one sentence

> Frontier labs ship model updates on 1 to 3 percentage-point eval deltas,
> and Anthropic measured a 6 percentage-point swing on Terminal-Bench from
> infrastructure config alone. EVALSIG is the release gate that tells those
> two cases apart.

## Why now

* **Item-level noise.** Apple's GSM-Symbolic showed up to 65pp accuracy drops
  from adding an irrelevant clause to a math problem with the same answer.
  Zhao et al. showed swapping two few-shot examples can drop accuracy from
  88.5% to 51.3%.
* **Infrastructure noise.** Anthropic published a 6pp swing on Terminal-Bench
  2.0 from resource config alone, and 1.54pp on SWE-bench from a 5x RAM
  change. Even at temperature 0, batch size and kernel fusion produce
  different outputs.
* **No paired inference in the field.** Frontier models correlate 0.3 to 0.7
  question-to-question. Comparing two models on the same items has 2 to 4
  times lower variance than independent samples. Every commercial eval tool
  today stops at "bootstrap CI on a single run".

## What you get

| You want to... | Reach for |
|---|---|
| Decide if a 1.2pp delta is real | `evalsig.compare(a, b)` -> `ComparisonResult` |
| Block a CI build on a bad release | `evalsig gate --baseline a.json --candidate b.json --min-delta 0.005` |
| Plan how many items you actually need | `evalsig.required_n(target_delta, sd_diff)` |
| Stop early on expensive evals without alpha inflation | `evalsig.sequential_gate(stream)` |
| Audit a third-party "X is +3pp better" claim | `evalsig compare --output markdown ...` |
| Keep an append-only history per project | `evalsig.store.write_run(...)` + `evalsig history` |

## Quickstart

Install:

```bash
pip install evalsig
```

Compare two runs from the CLI:

```bash
evalsig gate \
  --baseline baseline.eval \
  --candidate candidate.eval \
  --metric accuracy \
  --cluster passage_id \
  --min-delta 0.005 \
  --alpha 0.05 \
  --power 0.80
```

Or from Python:

```python
from evalsig import compare
from evalsig.io import read_inspect_log

a = read_inspect_log("baseline.eval")
b = read_inspect_log("candidate.eval")

result = compare(a, b, cluster="passage_id", alpha=0.05, one_sided=True)
print(result.delta)         # +0.0124
print(result.ci)            # (-0.003, +0.027)
print(result.p_value)       # 0.082
print(result.significant)   # False
print(result.mde)           # 0.018 (would have needed to detect ~1.8pp at 80% power)
```

## Where to go next

* New to EVALSIG? Start with [Quickstart](get-started/quickstart.md).
* Want the conceptual map? Read [What EVALSIG solves](concepts/what-evalsig-solves.md)
  and [Paired vs unpaired](concepts/paired-vs-unpaired.md).
* Building automation? Jump to [CLI reference](usage/cli.md) and
  [Integrations](usage/integrations.md).
* Plugging into your own harness? See [Modules: evalsig.io](modules/io.md)
  and [Configuration](usage/configuration.md).
* Want to know why the statistics work? [Methodology](methodology.md) is the
  long-form story with citations.

## Project status

* Version: 0.1.0
* Python: 3.10+
* License: Apache-2.0
* Tests: 45 unit + 4 end-to-end Monte-Carlo experiments, all passing.
