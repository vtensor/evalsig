# Effect sizes

A p-value tells you whether an effect is real. An effect size tells you
how big it is in units a human can interpret. EVALSIG ships three of
the most common effect sizes.

## Why you want both

Report a p-value alone and you encourage chasing significance even on
practically trivial differences. Report an effect size alone and you
have no signal-vs-noise control. The pair is what you want on every
release decision.

## Cohen's d (two-sample)

The mean difference divided by the pooled standard deviation:

```
d = (mean_b - mean_a) / sd_pooled
```

The conventional yardstick:

| |d| | label |
|---|---|
| < 0.2 | negligible |
| 0.2 - 0.5 | small |
| 0.5 - 0.8 | medium |
| > 0.8 | large |

```python
from evalsig.inference import cohens_d
out = cohens_d(scores_a, scores_b)
print(out.value, out.magnitude)
```

Use it when the two runs are not paired or when you want the most
familiar effect-size unit.

## Cohen's d for paired data

Same idea, but uses the standard deviation of the *paired difference*
rather than the pooled SD:

```
d_paired = mean(b - a) / sd(b - a)
```

When the runs are correlated this is usually much larger than the
two-sample d, because the paired SD is much smaller than the pooled SD:

```python
from evalsig.inference import cohens_d_paired
out = cohens_d_paired(scores_a, scores_b)
```

For an eval that compares two models on the same items, this is the
right effect size.

## Cliff's delta

A non-parametric effect size. For every pair `(a_i, b_j)`, count how
often `b > a` minus how often `a > b`. The result is in [-1, +1] and is
invariant to monotone transforms of the data:

```python
from evalsig.inference import cliffs_delta
out = cliffs_delta(scores_a, scores_b)
```

Romano et al. (2006) thresholds: |delta| < 0.147 negligible, < 0.33
small, < 0.474 medium, otherwise large.

Use Cliff's delta when scores are ordinal (a 5-point judge rating, a
graded rubric) or when you do not trust the assumption that mean
differences are meaningful.

## What returns

All three return an `EffectSize` dataclass:

```python
@dataclass(frozen=True)
class EffectSize:
    name: str        # e.g. "cohens_d_paired"
    value: float
    magnitude: str   # "negligible" / "small" / "medium" / "large"
```

## Pairing it with the gate

The release gate reports the delta on its native scale. If your team
wants effect sizes alongside, compute them separately and attach them
to the report:

```python
from evalsig import compare
from evalsig.inference import cohens_d_paired

result = compare(a, b)
es = cohens_d_paired(
    np.array([it.score for it in a.items]),
    np.array([it.score for it in b.items]),
)
print(f"delta={result.delta:+.4f} (paired d = {es.value:.2f}, {es.magnitude})")
```

## See also

* [Paired vs unpaired](paired-vs-unpaired.md): which version of d to pick.
* [What evalsig solves](what-evalsig-solves.md): the case for reporting
  both p-values and effect sizes.
