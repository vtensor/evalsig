# EVALSIG

**Know whether your LLM eval gains are real or just noise. Catch it in CI, before shipping.**

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache--2.0-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-45%2F45%20passing-brightgreen.svg)](VERIFICATION.md)

[Quickstart](docs/get-started/quickstart.md) | [CLI reference](docs/usage/cli.md) | [Methodology](docs/methodology.md) | [Design doc](EVALSIG.md) | [Verification](VERIFICATION.md)

* * *

## What this is

EVALSIG sits between any LLM eval harness (Inspect AI, lm-eval-harness,
HELM, simple-evals, your internal pipeline) and the decision to ship a
model. It applies the statistical machinery the academic literature has
spent the last two years recommending but no commercial tool ships
end-to-end: paired-difference testing, clustered standard errors,
permutation tests, minimum-detectable-effect / power analysis,
always-valid sequential monitoring, and multiple-comparison corrections.

> Frontier labs ship model updates on 1 to 3 percentage-point eval
> deltas, and Anthropic measured a 6 percentage-point swing on
> Terminal-Bench from infrastructure config alone. EVALSIG is the
> release gate that tells those two cases apart.

Read [Methodology](docs/methodology.md) for the citations and the
Monte Carlo validation.

## Quickstart

Install from source (not yet published to PyPI):

```bash
git clone https://github.com/vtensor/evalsig.git
cd evalsig
pip install -e .
```

Compare two runs:

```bash
evalsig gate \
  --baseline baseline.json \
  --candidate candidate.json \
  --metric accuracy \
  --cluster passage_id \
  --min-delta 0.005 \
  --alpha 0.05 \
  --power 0.80
```

```
EVALSIG release gate
====================
delta:         +0.0124  (cluster_bootstrap)
CI (95%):      [+0.0023, +inf]
p-value:       0.0070
required MDE:  0.0050
detectable:    0.0040 at 80% power

VERDICT: ALLOW
```

Exit code is `0` for ALLOW, `1` for REJECT, `2` for INCONCLUSIVE.

## If you want to...

| You want to... | Go here |
|---|---|
| Install and run your first comparison | [Quickstart](docs/get-started/quickstart.md) |
| Understand every field in the output | [Understanding the output](docs/get-started/understanding-output.md) |
| Pick the right test for your data | [Paired vs unpaired](docs/concepts/paired-vs-unpaired.md) |
| Handle clustered items | [Clustered standard errors](docs/concepts/clustering.md) |
| Plan how many items you need | [MDE and power](docs/concepts/mde-and-power.md) |
| Stop expensive runs early | [Sequential testing](docs/concepts/sequential-testing.md) |
| Gate on a multi-task suite | [Multiple comparisons](docs/concepts/multiplicity.md) |
| Look up a function | [Modules](docs/modules/types.md) |
| Wire into CI | [CI release gate](docs/scenarios/ci-release-gate.md) |
| Keep an audit trail | [Compliance audit trail](docs/scenarios/compliance-audit-trail.md) |

## Features

* **Paired-difference inference** -- paired t, paired permutation,
  paired bootstrap, McNemar exact / chi-squared.
* **Clustered standard errors** -- block bootstrap on any cluster id
  the harness provides.
* **MDE and power analysis** -- closed-form MDE, required-N inverse,
  Kish design-effect adjustment for clustered designs.
* **Always-valid sequential testing** -- Howard 2021 confidence
  sequence, stop whenever the CI excludes zero.
* **Multiple-comparison corrections** -- Bonferroni, Holm, Benjamini-
  Hochberg.
* **Effect sizes** -- Cohen's d (two-sample and paired), Cliff's
  delta.
* **One CLI invocation gates CI** -- exit code 0 / 1 / 2 maps to
  ALLOW / REJECT / INCONCLUSIVE.
* **Reads every common eval format** -- Inspect AI `.eval` exports,
  lm-eval-harness `samples_*.jsonl`, HELM `scenario_state.json`,
  Parquet, and EVALSIG's own JSON schema.
* **Append-only run history** -- Parquet store with a JSON manifest;
  query via the `history` subcommand.
* **GitHub Action + pytest plugin** -- drop-in CI integrations.
* **Three output formats** -- TTY for logs, JSON for dashboards,
  Markdown for PR comments.

## Configuration

```toml title="pyproject.toml"
[tool.evalsig]
alpha = 0.05
power = 0.80
min_delta = 0.005
method = "auto"          # or "paired_t" / "paired_permutation" / ...
cluster = "passage_id"
one_sided = true
resamples = 10000
seed = 0
```

(Configuration in `pyproject.toml` is on the v0.2 roadmap; for v0.1
pass the same values as CLI flags or function arguments.)

## Integrations

### GitHub Actions

```yaml
- uses: vtensor/evalsig@v0.1
  with:
    baseline: baseline.json
    candidate: candidate.json
    metric: accuracy
    min_delta: '0.005'
```

### Pytest

```python
def test_no_regression(evalsig_gate):
    a = evalsig_gate.load("baseline.json")
    b = evalsig_gate.load("candidate.json")
    evalsig_gate.assert_no_regression(a, b, min_delta=0.005)
```

### Pre-commit

```yaml
- repo: https://github.com/vtensor/evalsig
  rev: v0.1.0
  hooks:
    - id: evalsig-doctor
```

## CLI cheat sheet

```bash
evalsig compare   --baseline a.json --candidate b.json
evalsig gate      --baseline a.json --candidate b.json --min-delta 0.005
evalsig mde       --sd-diff 0.30 --target-delta 0.01 --power 0.80
evalsig watch     --baseline a.json --candidate b.json --alternative greater
evalsig doctor    a.json b.json
evalsig history   --root .evalsig/store --project mmlu-pro
evalsig version
```

Run `evalsig <subcommand> --help` for every flag.

## Python API

```python
from evalsig import compare, gate, mde
from evalsig.io import read_runframe_json

a = read_runframe_json("baseline.json")
b = read_runframe_json("candidate.json")

result = compare(a, b, alpha=0.05, one_sided=True)
print(result.delta, result.p_value, result.significant)

report = gate(a, b, min_delta=0.005, alpha=0.05, power=0.80)
print(report.verdict.value)   # 'ALLOW' / 'REJECT' / 'INCONCLUSIVE'
```

Full API: [docs/usage/python-api.md](docs/usage/python-api.md).

## Why this exists

Surveyed every credible eval tool in May 2026. The whole field maxes
out at "bootstrap CI on a single run". Inspect AI is the only player
shipping clustered SE. Nobody ships paired-difference inference,
permutation tests, MDE / power, or sequential testing. The academic
recipes have been public for 18+ months and remain unimplemented
commercially.

EVALSIG closes that gap.

References:

* Miller (2024), "Adding Error Bars to Evals". arXiv:2411.00640.
* Anthropic Engineering (2025), "Quantifying infrastructure noise in
  agentic coding evals".
* Howard et al. (2021), "Time-uniform, nonparametric, nonasymptotic
  confidence sequences," Annals of Statistics.
* Benjamini & Hochberg (1995), "Controlling the False Discovery Rate,"
  JRSS-B.

## Project status

* Version: 0.1.0
* Python: 3.10+
* Tests: 45 unit + 4 end-to-end Monte Carlo experiments, all passing.
* License: [Apache-2.0](LICENSE).

## Contributing

Bug reports, feature requests, and PRs welcome. See
[CONTRIBUTING.md](CONTRIBUTING.md) and
[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

Security issues should follow [SECURITY.md](SECURITY.md).
