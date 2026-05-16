# `evalsig.integrations`

Optional adapters for the systems people already use. Each submodule
imports its target lazily so missing dependencies do not block the
package install.

## `pytest_plugin`

Exposes an `evalsig_gate` fixture that lets you treat a release gate
as a test.

Enable in your `conftest.py`:

```python
pytest_plugins = ["evalsig.integrations.pytest_plugin"]
```

Use in a test body:

```python
def test_no_regression(evalsig_gate):
    a = evalsig_gate.load("baseline.json", format="runframe")
    b = evalsig_gate.load("candidate.json", format="runframe")
    evalsig_gate.assert_no_regression(
        a, b,
        metric="accuracy",
        min_delta=0.005,
        alpha=0.05,
        power=0.80,
        cluster="passage_id",
        method="auto",
    )
```

On REJECT or INCONCLUSIVE, the fixture raises `AssertionError` with the
full Markdown report embedded, so pytest's failure message tells the
developer exactly what to do next.

`load()` accepts `format="runframe" | "lm_eval" | "inspect" | "helm" |
"parquet"` and forwards any extra kwargs to the matching reader.

## `github_action`

The Python entry point the published GitHub Action calls. Reads inputs
from environment variables (the actions/core convention), runs the gate,
writes a Markdown summary to `$GITHUB_STEP_SUMMARY`, emits structured
outputs to `$GITHUB_OUTPUT`, and exits with the gate's exit code.

You normally do not call this directly. Use the action:

```yaml
- uses: vtensor/evalsig@v0.1
  with:
    baseline: baseline.json
    candidate: candidate.json
    metric: accuracy
    min_delta: '0.005'
```

If you want to script it yourself:

```bash
INPUT_BASELINE=baseline.json \
INPUT_CANDIDATE=candidate.json \
INPUT_METRIC=accuracy \
INPUT_MIN_DELTA=0.005 \
INPUT_ALPHA=0.05 \
INPUT_POWER=0.80 \
python -m evalsig.integrations.github_action
```

## `braintrust`

Publishes a comparison result to Braintrust as an experiment record.
Imports the `braintrust` SDK lazily; raises `IntegrationError` if it
isn't installed.

```python
from evalsig.integrations.braintrust import publish_comparison

publish_comparison(
    baseline, candidate,
    project="my-eval-suite",
    experiment="release-2026-05-16",
    min_delta=0.005,
)
```

Install with `pip install evalsig[braintrust]` (when the extra is
available) or `pip install braintrust` separately.

## Writing your own integration

Every integration follows the same pattern:

1. Import EVALSIG primitives at module top level.
2. Import the target system's SDK inside the function that needs it.
3. Wrap the call in a `try/except ImportError` that raises
   `IntegrationError` with an install hint.

This keeps the package import side-effect-free and lets users `pip
install evalsig` without dragging in every possible target SDK.

## See also

* [Usage: integrations](../usage/integrations.md) for the workflow-level
  view.
* [Scenarios: CI release gate](../scenarios/ci-release-gate.md) for a
  full GitHub Actions example.
