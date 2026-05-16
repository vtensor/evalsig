# Integrations

EVALSIG plugs into existing pipelines through three first-class
integrations and a Python-API path that works anywhere.

## GitHub Actions

The repo ships an `action.yml` so you can drop the gate into a workflow:

```yaml
name: Eval gate

on: pull_request

jobs:
  evalsig:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install evalsig
      - name: Run baseline and candidate evals
        run: |
          your-eval --model baseline > baseline.json
          your-eval --model candidate > candidate.json
      - uses: vtensor/evalsig@v0.1
        id: gate
        with:
          baseline: baseline.json
          candidate: candidate.json
          metric: accuracy
          min_delta: "0.005"
          alpha: "0.05"
          power: "0.80"
      - name: Comment verdict on PR
        if: always()
        run: gh pr comment $PR --body "${{ steps.gate.outputs.verdict }}"
        env:
          PR: ${{ github.event.pull_request.number }}
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

The action publishes four outputs (`verdict`, `delta`, `p_value`, `mde`)
so downstream steps can read them via `${{ steps.gate.outputs.* }}`. It
also writes a Markdown summary to `$GITHUB_STEP_SUMMARY` so the verdict
shows up in the workflow run page.

## Pytest

Treat the gate as a test. Add the plugin to your `conftest.py`:

```python
# conftest.py
pytest_plugins = ["evalsig.integrations.pytest_plugin"]
```

Then write tests that fail with the full Markdown report on a regression:

```python
def test_no_regression_on_mmlu(evalsig_gate):
    a = evalsig_gate.load("baseline.json", format="runframe")
    b = evalsig_gate.load("candidate.json", format="runframe")
    evalsig_gate.assert_no_regression(
        a, b,
        metric="accuracy",
        min_delta=0.005,
        alpha=0.05,
        power=0.80,
        cluster="passage_id",
    )
```

When the assertion fails, pytest shows the rendered Markdown report so
the developer sees the verdict, the delta, and the suggested next step
without re-running.

## Pre-commit

A pre-commit hook is overkill for most teams (full evals take time and
should not block local commits), but EVALSIG ships a hook config for
the `doctor` subcommand: validate any RunFrame JSON file that changes.

```yaml
# .pre-commit-config.yaml
- repo: https://github.com/vtensor/evalsig
  rev: v0.1.0
  hooks:
    - id: evalsig-doctor
      files: '\.json$'
```

## Braintrust

If you publish runs to Braintrust, you can attach the EVALSIG verdict as
an experiment record:

```python
from evalsig.integrations.braintrust import publish_comparison

publish_comparison(
    baseline_run, candidate_run,
    project="my-eval-suite",
    experiment="run-2026-05-16",
    min_delta=0.005,
)
```

The Braintrust SDK is an optional dependency; install with
`pip install evalsig[braintrust]`.

## Python API in your own pipeline

If none of the above fit, the public `gate()` function returns a typed
`GateReport`. Wire it into anything:

```python
from evalsig import gate
from evalsig.io import read_inspect_log

a = read_inspect_log("baseline.eval")
b = read_inspect_log("candidate.eval")
report = gate(a, b, min_delta=0.005, alpha=0.05, power=0.80)

if report.verdict.value == "ALLOW":
    promote_candidate()
elif report.verdict.value == "INCONCLUSIVE":
    schedule_more_items(report.suggestion)
else:
    notify_humans(report)
```

## Slack, email, dashboards

EVALSIG does not ship a Slack or email integration directly. The
recommended pattern is:

1. Run the gate.
2. Capture the JSON report (`--json report.json`).
3. Render the Markdown form (`--output markdown`).
4. Post both to whatever destination you already use (Slack webhook,
   sendgrid, a dashboard ingestion endpoint).

The JSON schema is stable across the 0.x line, so downstream parsers
will not break on minor upgrades.

## See also

* [CI release gate](../scenarios/ci-release-gate.md): a full GitHub
  Actions example with PR comments.
* [Compliance audit trail](../scenarios/compliance-audit-trail.md): how
  to persist signed reports for audits.
