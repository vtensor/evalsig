# Understanding the output

Every `evalsig compare` and `evalsig gate` invocation produces a
`ComparisonResult` (or a `GateReport` wrapping one). This page is a guided
tour through every field, so you know how to read it without guessing.

## A sample output

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

## delta

The estimated effect: candidate mean minus baseline mean over the aligned
items. Always reported as `(b - a)`, so positive means the candidate is
better.

Units are whatever your metric is. For accuracy, this is a proportion, so
`+0.0124` means "1.24 percentage points better than baseline".

## method

Which underlying statistical test produced the p-value and CI. The
auto-selector picks one of:

| Method | When auto picks it |
|---|---|
| `mcnemar_exact` / `mcnemar_chi2` | Both runs are 0/1 and no cluster id |
| `paired_permutation` | Continuous scores, no cluster id |
| `cluster_bootstrap` | A cluster id is provided |
| `paired_t` | You asked for it explicitly |
| `paired_bootstrap` | You asked for it explicitly |

You can override with `--method` on the CLI or `method=` in the Python API.

## CI

Confidence interval for the delta. Two-sided unless you passed
`--one-sided`, in which case one side is `+inf` (for "greater") or `-inf`
(for "less").

The width of the CI is the practical answer to "how much did we learn?":
narrow means precise, wide means we still have a lot of noise.

## p-value

The probability of observing a delta at least this extreme if the truth
were zero effect. Smaller is stronger evidence against the null. We don't
recommend chasing 0.001 vs 0.01: the policy threshold is your `--alpha`,
typically 0.05.

## significant

`True` when `p_value < alpha`. For a one-sided test we also require the
delta to point in the requested direction. This boolean is the input to
the gate's verdict logic.

## required MDE / min-delta

How big a real effect you said you cared about before running the gate.
Below this threshold, the gate refuses to ship even if the result is
statistically significant. A common policy is 0.5pp for general-purpose
evals, 1pp for higher-noise agentic evals, and lower for very large
human-labeled tests.

## detectable / MDE

The smallest delta you could have detected at the requested power with
this much data. The formula behind it is

```
MDE = (z_alpha + z_beta) * sd_diff / sqrt(n_eff)
```

If MDE is *larger* than min-delta, the run was underpowered: even if a
real effect equal to min-delta existed, you would not have seen it. The
gate flags this as INCONCLUSIVE and tells you roughly how many more items
to collect.

## VERDICT

The release-gate decision. Three possible values:

* **ALLOW** (exit 0). Significant and clears the policy threshold. Ship.
* **REJECT** (exit 1). Either not significant, or significant but below
  the policy threshold. The candidate is not statistically better in the
  way you said you cared about.
* **INCONCLUSIVE** (exit 2). Not significant AND the run was too small to
  detect the policy threshold. Collect more data and re-run.

## Notes

Any time EVALSIG sees something worth flagging during alignment, it adds a
short note:

* `"item-set coverage is 87% (below 95%); 35 items only in candidate, 12
  only in baseline"` -- partial overlap can bias the delta. You probably
  want to figure out why.
* `"3 item(s) have cluster_id mismatch between runs; using baseline's
  cluster assignment"` -- a sign the two harnesses disagree on how items
  are grouped.
* `"RunFrames carry cluster_id; pass cluster=<name> to opt into cluster-
  aware inference"` -- the data has clusters but you didn't ask for the
  cluster bootstrap, so you got item-level inference.

Treat the notes like compiler warnings: not blocking, but worth reading.

## JSON form

Pass `--output json` or `--json report.json` to get the same fields as a
structured object:

```json
{
  "delta": 0.0124,
  "ci": [0.0023, "Infinity"],
  "ci_level": 0.95,
  "p_value": 0.0070,
  "significant": true,
  "n_pairs": 1000,
  "n_clusters": null,
  "method": "paired_permutation",
  "mde": 0.0040,
  "notes": []
}
```

This is the format the SaaS dashboard ingests and the format you should
persist for compliance audits. The schema is part of EVALSIG's public
contract; field names and types are stable across the 0.x line.
