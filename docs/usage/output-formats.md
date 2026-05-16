# Output formats

EVALSIG renders a `ComparisonResult` or `GateReport` in three formats.
Pick the one that fits your downstream system.

## TTY (default)

Designed for humans reading logs. Plain ASCII, ANSI colors when stdout
is a terminal.

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

Render from Python:

```python
from evalsig import to_tty
print(to_tty(report))
```

## JSON

The format for dashboards, audit trails, and dashboards-as-code.

```bash
evalsig gate ... --output json
```

```json
{
  "verdict": "ALLOW",
  "exit_code": 0,
  "min_delta": 0.005,
  "alpha": 0.05,
  "power": 0.8,
  "comparison": {
    "delta": 0.0124,
    "ci": [0.0023, "Infinity"],
    "ci_level": 0.95,
    "p_value": 0.007,
    "significant": true,
    "n_pairs": 4032,
    "n_clusters": 1008,
    "method": "paired_permutation",
    "mde": 0.0040,
    "notes": []
  },
  "suggestion": null
}
```

The schema is part of the public API and is stable across the 0.x line.

Render from Python:

```python
from evalsig import to_json
text = to_json(report)
```

## Markdown

The format for PR comments, status checks, and compliance exports.

```bash
evalsig gate ... --output markdown
```

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
| method | `paired_permutation` |
| n_pairs | 4032 |
```

Pipe into a GitHub PR comment:

```bash
evalsig gate ... --output markdown | gh pr comment $PR --body-file -
```

Render from Python:

```python
from evalsig import to_markdown
text = to_markdown(report)
```

## Writing JSON alongside any renderer

Pass `--json path` and EVALSIG writes a JSON copy at the same time it
prints the chosen renderer. Useful when you want the human output in the
logs *and* the machine output in a downstream pipeline.

```bash
evalsig gate ... --output tty --json $RUN_DIR/report.json
```

## What gets serialised

`ComparisonResult.to_dict()` returns:

```python
{
  "delta": float,
  "ci": [float, float],
  "ci_level": float,
  "p_value": float,
  "significant": bool,
  "n_pairs": int,
  "n_clusters": int | None,
  "method": str,
  "mde": float,
  "notes": [str, ...],
}
```

`GateReport.to_dict()` wraps that plus the policy and suggestion:

```python
{
  "verdict": "ALLOW" | "REJECT" | "INCONCLUSIVE",
  "exit_code": 0 | 1 | 2,
  "min_delta": float,
  "alpha": float,
  "power": float,
  "comparison": ComparisonResult.to_dict(),
  "suggestion": str | None,
}
```

Infinity in confidence intervals is rendered as `"Infinity"` /
`"-Infinity"` so the JSON stays valid (the standard does not allow
`Infinity` as a number).

## See also

* [CLI reference](cli.md): the `--output` and `--json` flags.
* [Python API](python-api.md): the `to_json`, `to_markdown`, `to_tty`
  functions.
* [Compliance audit trail](../scenarios/compliance-audit-trail.md):
  a worked example of persisting signed reports.
