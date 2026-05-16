# MDE and power

A p-value answers "is the effect significant?". MDE and power answer the
prior question: "could we have detected an effect of this size at all?".

If you skip this step, "not significant" is ambiguous: maybe there is no
effect, or maybe your run was too small to see it. EVALSIG's gate uses
MDE to disambiguate, returning INCONCLUSIVE for the second case.

## Definitions

**Power** (also written 1 - beta) is the probability that the test fires
when there really is an effect of a given size.

**Minimum detectable effect (MDE)** is the smallest true effect the test
can detect with a chosen power, given the sample size and the variance.

For a paired-difference test the formula is

```
MDE = (z_alpha + z_beta) * sd_diff / sqrt(n_eff)
```

where `sd_diff` is the standard deviation of the per-item paired
difference, `n_eff` is the effective sample size (after the cluster
design-effect adjustment, if any), and the z's are normal quantiles.

By default we use alpha = 0.05 and power = 0.80, which match the
literature defaults. You can change them with `--alpha` and `--power`.

## Computing MDE in EVALSIG

From Python:

```python
from evalsig.inference import mde

result = mde(sd_diff=0.3, n_pairs=1000, alpha=0.05, power=0.80,
             one_sided=True)
print(result.mde)        # 0.0226
print(result.deff)       # None  (no clustering)
```

From the CLI:

```bash
evalsig mde --sd-diff 0.3 --n-pairs 1000 --alpha 0.05 --power 0.80 --one-sided
```

## The inverse: required N

When planning a new eval, the practical question is the inverse: how many
paired items do I need to detect `target_delta`?

```python
from evalsig.inference import required_n

n = required_n(target_delta=0.01, sd_diff=0.3, alpha=0.05, power=0.80,
               one_sided=True)
print(n)  # 6173 paired items
```

From the CLI:

```bash
evalsig mde --sd-diff 0.3 --target-delta 0.01 --alpha 0.05 --power 0.80 --one-sided
```

## How the gate uses MDE

The gate's decision rule:

| Result | Verdict | Reasoning |
|---|---|---|
| Significant and delta >= min_delta | ALLOW | Real and big enough |
| Significant and delta < min_delta | REJECT (with note) | Real but below policy |
| Not significant and MDE > min_delta | INCONCLUSIVE | Run was too small |
| Not significant and MDE <= min_delta | REJECT | Properly powered null |

The INCONCLUSIVE branch is the value-add. Without it, a small-N run with
a noisy 1pp delta could come back "not significant" and you would have no
way to know whether to ship, reject, or collect more data.

## Calibration check

We verified the MDE formula matches Monte Carlo. With `sd_diff = 0.4`,
`n = 1000`, alpha = 0.05, power = 0.80, the computed MDE is 0.0315. We
then ran 500 simulations with true delta = 0.0315 and observed an
empirical detection rate of 81%, within 1pp of the target. See
`experiment_3_mde_calibration` in `research/validate.py`.

## Design effect for clustered data

When items are clustered, the effective N drops by the design effect:

```
deff = 1 + (mean_cluster_size - 1) * icc
```

With ICC = 0.20 and 10-item clusters, deff = 2.8, so a 1000-item run
behaves like a 357-item run for the purposes of inference. EVALSIG
estimates ICC from the data automatically; you can also pass an explicit
value to `required_n` for planning.

## A common gotcha

People sometimes pick `min_delta` based on what they hope to detect, then
discover later that their MDE is bigger and the gate keeps returning
INCONCLUSIVE. The fix is to plan first:

1. Estimate the SD of paired differences from a pilot run (or from
   historical data).
2. Pick the smallest delta you care about (the policy threshold).
3. Compute `required_n` for that delta.
4. Either collect at least that many items, or relax `min_delta`.

If you cannot afford the required N, you cannot afford the gate at that
strictness. The honest answer is to ship with a wider tolerance, not to
pretend the run is bigger than it is.

## See also

* [Paired vs unpaired](paired-vs-unpaired.md): the choice that drives
  `sd_diff` the most.
* [Clustered standard errors](clustering.md): the design effect.
* [Sequential testing](sequential-testing.md): the always-valid
  alternative when you cannot pick a sample size in advance.
