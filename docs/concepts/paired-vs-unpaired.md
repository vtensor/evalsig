# Paired vs unpaired

The single biggest design choice in EVALSIG is that the default inference
path is paired. This page explains why, with the math and a worked
example.

## What "paired" actually means

A paired comparison pairs items, not runs. Both models see the same input
on each row of the dataset, and we compute the difference of their scores
per item:

```
item_id   y_a   y_b   d_i = y_b - y_a
q1        1     1     0
q2        0     1     +1
q3        1     0     -1
q4        1     1     0
...
```

Then we test whether the mean of `d_i` is zero. This is structurally
different from an unpaired test, which compares the mean of `y_a` against
the mean of `y_b` while ignoring the row alignment.

## Why pairing is so much tighter

For an unpaired two-sample test the standard error of the difference is

```
SE_unpaired = sqrt( var(y_a) / n_a + var(y_b) / n_b )
```

For a paired test it is

```
SE_paired   = sd(d) / sqrt(n)
            = sqrt( var(y_a) + var(y_b) - 2 * cov(y_a, y_b) ) / sqrt(n)
```

The covariance term is the whole story. When the two runs are correlated
(easy items are easy for both, hard items are hard for both), the
covariance is positive, and the paired standard error shrinks. With
typical 0.3-0.7 correlation on frontier LLM evals, the paired SE is
2-4x smaller than the unpaired SE. Same number of items, much tighter
interval, much more power.

## A 30-line worked example

```python
import numpy as np
from evalsig.inference import paired_permutation_test, unpaired_t_test

rng = np.random.default_rng(0)
n = 500
true_lift = 0.015  # 1.5 percentage points

# Shared per-item luck. Same items, both runs.
theta = rng.beta(4, 2, size=n)
c = rng.random(n)
y_a = (c < theta).astype(float)
y_b = (c < np.clip(theta + true_lift, 0, 1)).astype(float)

paired = paired_permutation_test(y_a, y_b, alternative="greater",
                                  n_resamples=2000, rng=0)
unpaired = unpaired_t_test(y_a, y_b, alternative="greater")

print("paired   p =", round(paired.p_value, 4))
print("unpaired p =", round(unpaired.p_value, 4))
```

Typical output:

```
paired   p = 0.012
unpaired p = 0.317
```

Same items, same effect, two very different conclusions.

## When unpaired is the only option

Sometimes you genuinely cannot pair. Items were sampled differently across
runs, the harness lost the per-item ids, or you are comparing two
populations rather than two scorers. EVALSIG ships `unpaired_t_test`,
`unpaired_permutation`, and `unpaired_bootstrap` for those cases. They
are correct; they just throw away the pairing advantage.

If you are reading from a harness that *does* keep per-item ids (Inspect
AI, lm-eval-harness, HELM, EVALSIG's RunFrame JSON), prefer the paired
path.

## Which paired test to pick

EVALSIG's auto method handles 90% of cases. The full table:

| Method | When to use |
|---|---|
| `mcnemar` | Both runs are 0/1 (right/wrong). Exact under the null. |
| `paired_permutation` | Continuous or 0/1 scores, no clusters. No distributional assumption. |
| `paired_t` | Continuous scores, large n, diffs not too skewed. Fastest. |
| `paired_bootstrap` | When you want a percentile CI rather than a t CI. |
| `cluster_bootstrap` | Items belong to groups (passages, templates). Required for valid inference. |

Pass `--method <name>` on the CLI or `method=` in the Python API to
override the auto selector.

## See also

* [Clustered standard errors](clustering.md): the other big mistake to
  avoid when items are not i.i.d.
* [MDE and power](mde-and-power.md): how the choice of paired vs unpaired
  feeds directly into how many items you need.
* [Effect sizes](effect-sizes.md): Cohen's d and Cliff's delta to go with
  the p-value.
