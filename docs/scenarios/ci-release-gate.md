# Scenario: CI release gate

You ship an LLM-powered product feature. Each PR triggers a benchmark
run; you want the build to fail if the candidate model is worse than
the baseline, on a statistically defensible basis. This page is the
end-to-end recipe.

## Architecture

```
PR -> CI workflow
  step 1: check out baseline.json from main
  step 2: run the eval on the candidate model -> candidate.json
  step 3: evalsig doctor baseline.json candidate.json
  step 4: evalsig gate --baseline ... --candidate ... --min-delta 0.005
  step 5: comment the Markdown report on the PR
  step 6: exit with the gate's exit code; CI passes iff verdict == ALLOW
```

## The eval harness

EVALSIG does not run your eval. Plug in whatever you already use:

```bash
inspect eval my_task --model=anthropic/claude-x \
    --log-format=eval --log-dir=runs/
inspect log export runs/2026-05-16T10-00-00.eval > candidate.json
```

Or:

```bash
lm_eval --model=hf --model_args=pretrained=... \
        --tasks=mmlu --output_path=samples_mmlu.jsonl --log_samples
```

The point is to end up with a per-item file that EVALSIG can read.

## The GitHub Actions workflow

```yaml title=".github/workflows/eval-gate.yml"
name: Eval gate
on:
  pull_request:
    paths:
      - "src/**"
      - "prompts/**"
      - "models/**"

jobs:
  evalsig:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install evalsig
      - name: Fetch baseline.json from main
        run: |
          git fetch origin main:refs/remotes/origin/main
          git show origin/main:baseline.json > baseline.json
      - name: Run candidate eval
        run: ./scripts/run_eval.sh > candidate.json
      - name: Validate inputs
        run: evalsig doctor baseline.json candidate.json
      - name: Gate
        id: gate
        run: |
          evalsig gate \
            --baseline baseline.json \
            --candidate candidate.json \
            --metric accuracy \
            --cluster passage_id \
            --min-delta 0.005 \
            --alpha 0.05 \
            --power 0.80 \
            --json report.json \
            --output markdown > report.md
        # We capture the exit code without failing the step here so the
        # PR comment always lands.
        continue-on-error: true
      - name: Comment on PR
        if: always() && github.event.pull_request
        run: gh pr comment "$PR" --body-file report.md
        env:
          PR: ${{ github.event.pull_request.number }}
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      - name: Fail the build on REJECT or INCONCLUSIVE
        if: steps.gate.outcome == 'failure'
        run: exit ${{ steps.gate.outputs.exit_code || 1 }}
```

## The PR comment that lands

```markdown
## EVALSIG release gate :white_check_mark: ALLOW

| Field | Value |
|---|---|
| verdict | **ALLOW** |
| min_delta policy | `0.0050` |
| observed delta | `+0.0124` |
| CI (95%) | `[+0.0023, +inf]` |
| p-value | `0.0070` |
| detectable @ 80% power | `0.0040` |
| method | `cluster_bootstrap` |
| n_pairs | 4032 |
```

## Promoting the candidate to baseline

When the PR merges, you usually want the candidate file to become the
new baseline. A separate workflow handles that:

```yaml title=".github/workflows/promote-baseline.yml"
on:
  push:
    branches: [main]
jobs:
  promote:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: |
          ./scripts/run_eval.sh > baseline.json
          git config user.email "ci@example.com"
          git config user.name "ci"
          git add baseline.json
          git commit -m "promote baseline after merge" || echo "no change"
          git push
```

## Common pitfalls

* **Forgetting `--cluster`** when items are grouped. The build will
  look healthy until you hit a false-positive shipment, then a year of
  noisy alerts.
* **`min_delta` too small** for the eval size. Look at the
  `INCONCLUSIVE` rate over a few weeks; if it is high, raise the
  policy or grow the suite.
* **Running the eval inside CI on cheap runners.** Resource config
  alone can cause swings of several pp (the Anthropic Terminal-Bench
  paper is the canonical reference). Pin your runners.

## See also

* [Usage: integrations](../usage/integrations.md): the action.yml
  spec.
* [Concepts: clustered standard errors](../concepts/clustering.md): why
  `--cluster` matters.
* [Compliance audit trail](compliance-audit-trail.md): how to keep the
  reports around for audits.
