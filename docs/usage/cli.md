# CLI reference

The `evalsig` command exposes seven subcommands. Every subcommand respects
the same exit-code convention so CI systems can branch on the result
without parsing stdout.

| Exit code | Meaning |
|---|---|
| 0 | ALLOW or successful command |
| 1 | REJECT |
| 2 | INCONCLUSIVE (run too small to detect the requested effect) |
| 64 | bad command-line arguments |
| 65 | bad input data |
| 70 | internal error |

Run `evalsig <subcommand> --help` for the full per-command help.

## `evalsig compare`

Compare two runs and print the statistics. Does not impose a policy.

```bash
evalsig compare \
  --baseline baseline.json \
  --candidate candidate.json \
  --metric accuracy \
  --cluster passage_id \
  --alpha 0.05 \
  --power 0.80 \
  --method auto \
  --resamples 10000 \
  --seed 0 \
  --output tty
```

Common flags:

| Flag | Default | Meaning |
|---|---|---|
| `--baseline`, `--candidate` | required | Paths to the two runs |
| `--format` | `auto` | One of `auto`, `runframe`, `lm_eval`, `inspect`, `helm`, `parquet` |
| `--metric` | `accuracy` | Metric to extract from the file (used by lm-eval/HELM readers) |
| `--cluster` | none | Field name of the cluster id on each item |
| `--alpha` | 0.05 | Significance level |
| `--power` | 0.80 | Target power (for the MDE computation) |
| `--method` | `auto` | One of `auto`, `paired_t`, `paired_permutation`, `paired_bootstrap`, `mcnemar`, `cluster_bootstrap` |
| `--resamples` | 10000 | Number of permutation / bootstrap resamples |
| `--seed` | 0 | Random seed for reproducibility |
| `--one-sided` | off | One-sided "candidate > baseline" test |
| `--json` | none | Path to also write a JSON report |
| `--output` | `tty` | Stdout renderer: `tty`, `json`, or `markdown` |

## `evalsig gate`

Same as `compare`, plus a release policy. Adds:

| Flag | Default | Meaning |
|---|---|---|
| `--min-delta` | required | Smallest effect the policy accepts |
| `--two-sided` | off | Switch from default one-sided to two-sided |

Exit code is the gate verdict (0 / 1 / 2).

```bash
evalsig gate \
  --baseline baseline.json \
  --candidate candidate.json \
  --metric accuracy \
  --min-delta 0.005 \
  --alpha 0.05 \
  --power 0.80
```

Pipe `--output markdown` into a PR comment with `gh pr comment`, or
`--output json` into your own dashboard.

## `evalsig mde`

Compute the MDE or the required sample size. Useful in eval-planning
sessions.

```bash
# Given a sample size, what is the smallest detectable effect?
evalsig mde --sd-diff 0.30 --n-pairs 1000 --alpha 0.05 --power 0.80 --one-sided

# Given a target effect, how many items do you need?
evalsig mde --sd-diff 0.30 --target-delta 0.01 --alpha 0.05 --power 0.80 \
  --icc 0.20 --cluster-size 8
```

## `evalsig watch`

Run an always-valid sequential test over the paired differences of two
runs. Exits 0 if the test fires (rejects the null), 2 if it walks the
whole stream without rejection.

```bash
evalsig watch \
  --baseline baseline.json \
  --candidate candidate.json \
  --metric accuracy \
  --alternative greater \
  --alpha 0.05 \
  --min-n 30
```

See [Sequential testing](../concepts/sequential-testing.md) for when this
is the right tool.

## `evalsig doctor`

Validate one or more RunFrame JSON files against the published schema.
Returns 0 if everything is clean, 65 otherwise.

```bash
evalsig doctor baseline.json candidate.json
```

## `evalsig history`

List or filter the runs in the local store.

```bash
evalsig history --root .evalsig/store --project mmlu-pro --model-id claude-x \
  --since 2026-01-01 --until 2026-06-30
```

| Flag | Meaning |
|---|---|
| `--root` | Store root directory |
| `--project` | Project id (default `default`) |
| `--model-id`, `--task-id`, `--metric-name` | Equality filters |
| `--since`, `--until` | ISO-8601 timestamp bounds |

## `evalsig version`

Print the package version. Useful in scripts that want to gate on a
minimum version.

```bash
evalsig version  # 'evalsig 0.1.0'
evalsig --version  # same thing
```

## Putting them together

A realistic CI block:

```bash
# 1. Validate that both inputs are well-formed.
evalsig doctor baseline.json candidate.json || exit 1

# 2. Run the gate.
evalsig gate \
  --baseline baseline.json \
  --candidate candidate.json \
  --metric accuracy \
  --cluster passage_id \
  --min-delta 0.005 \
  --alpha 0.05 \
  --power 0.80 \
  --json $RUN_DIR/report.json \
  --output markdown > $RUN_DIR/report.md
verdict_exit=$?

# 3. Archive into the local store.
evalsig history --root .evalsig/store --project $TASK | tee $RUN_DIR/history.txt

exit $verdict_exit
```
