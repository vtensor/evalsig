# `evalsig.inference`

The statistical core. Pure NumPy and SciPy, no I/O, no globals, fully
reproducible given an RNG.

This module's job is the math. The `compare/` and `cli/` layers exist
only to orchestrate it.

## Paired tests

```python
from evalsig.inference import (
    paired_t_test,
    paired_permutation_test,
    paired_bootstrap_ci,
)
```

| Function | Returns |
|---|---|
| `paired_t_test(a, b, alternative, ci_level)` | `PairedOutcome` |
| `paired_permutation_test(a, b, alternative, ci_level, n_resamples, rng)` | `PairedOutcome` |
| `paired_bootstrap_ci(a, b, alternative, ci_level, n_resamples, rng)` | `PairedOutcome` |

The `PairedOutcome` dataclass has `delta`, `ci`, `ci_level`, `p_value`,
`n_pairs`, `method`, and `sd_diff`.

## Unpaired tests

```python
from evalsig.inference import (
    unpaired_t_test,
    unpaired_permutation,
    unpaired_bootstrap,
)
```

Same returns (an `UnpairedOutcome`). Use these only when the two runs
are not on the same items.

## McNemar's test

```python
from evalsig.inference import mcnemar_test

out = mcnemar_test(a, b, alternative="greater")
print(out.b_wins, out.c_wins)  # discordant pair counts
```

Auto-picks exact binomial vs continuity-corrected chi-squared based on
the number of discordant pairs.

## Cluster bootstrap

```python
from evalsig.inference import cluster_bootstrap_ci

out = cluster_bootstrap_ci(a, b, cluster_id,
                            alternative="two-sided",
                            n_resamples=5_000,
                            rng=0)
print(out.n_clusters)
```

Resamples whole clusters with replacement. Use whenever items belong to
groups.

## MDE / required N

```python
from evalsig.inference import mde, required_n, estimate_icc, power_for_delta
```

* `mde(sd_diff, n_pairs, alpha, power, one_sided, n_clusters, icc)` ->
  `MDEResult`
* `required_n(target_delta, sd_diff, alpha, power, one_sided, icc,
  mean_cluster_size)` -> `int`
* `estimate_icc(values, cluster_id)` -> `float` in `[0, 1]`
* `power_for_delta(delta, sd_diff, n_pairs, alpha, one_sided,
  n_clusters, icc)` -> `float` in `[0, 1]`

## Effect sizes

```python
from evalsig.inference import (
    cohens_d,
    cohens_d_paired,
    cliffs_delta,
    EffectSize,
)
```

All three return an `EffectSize(name, value, magnitude)` dataclass.
Magnitudes follow conventional thresholds (`negligible` / `small` /
`medium` / `large`).

## Sequential testing

```python
from evalsig.inference import confidence_sequence, sequential_gate
```

* `confidence_sequence(diffs, alpha, rho, sigma_bound)` -- one-shot
  always-valid CI on the running mean.
* `sequential_gate(stream, alpha, alternative, rho, min_n,
  sigma_bound)` -- walk a stream and stop when the CI excludes zero.

Returns a `SequentialOutcome` with `stopped`, `delta`, `ci`, `n_pairs`,
`method`, `half_width`.

## Multiplicity corrections

```python
from evalsig.inference import bonferroni, holm, benjamini_hochberg
```

All three take a 1D array of p-values and return a `MultipleTestResult`
with `p_adjusted`, `reject`, and `method`.

## Why a pure-math module

The whole package depends on `inference/` -- it never depends back. That
gives three properties:

* The math is testable in isolation. Property tests verify coverage with
  Monte Carlo; golden tests pin numeric outputs against R and
  statsmodels.
* The math is parallelisable. No globals means no surprise serialisation.
* The math is portable. You can pull `inference/` into another tool and
  use it as a stand-alone library if you want only the primitives.

## See also

* [Concepts: paired vs unpaired](../concepts/paired-vs-unpaired.md)
* [Concepts: clustered standard errors](../concepts/clustering.md)
* [Concepts: MDE and power](../concepts/mde-and-power.md)
* [Concepts: sequential testing](../concepts/sequential-testing.md)
* [Concepts: multiplicity](../concepts/multiplicity.md)
* [Concepts: effect sizes](../concepts/effect-sizes.md)
