"""Unpaired (two-sample) tests.

Use these only when the two runs were not scored on the same items.
With paired data, prefer evalsig.inference.paired which gives much
tighter intervals.

We provide three flavours:
  unpaired_t_test       Welch's t-test, fastest, normal approximation
  unpaired_permutation  shuffle-the-labels exact-style test
  unpaired_bootstrap    bootstrap CI of the difference of means
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
from scipy import stats

from evalsig.inference._checks import as_rng


Alt = Literal["two-sided", "greater", "less"]


@dataclass(frozen=True)
class UnpairedOutcome:
    delta: float
    ci: tuple[float, float]
    ci_level: float
    p_value: float
    n_a: int
    n_b: int
    method: str


def unpaired_t_test(
    a: np.ndarray,
    b: np.ndarray,
    *,
    alternative: Alt = "two-sided",
    ci_level: float = 0.95,
) -> UnpairedOutcome:
    """Two-sample t-test that does not assume equal variances.

    SciPy handles the test itself; the extra code below just computes a
    matching confidence interval.
    """
    res = stats.ttest_ind(b, a, equal_var=False, alternative=alternative)
    mean_a = float(a.mean())
    mean_b = float(b.mean())
    delta = mean_b - mean_a
    var_a = a.var(ddof=1) / a.size
    var_b = b.var(ddof=1) / b.size
    se = float(np.sqrt(var_a + var_b))
    # Degrees of freedom for the unequal-variance case (the usual formula
    # SciPy uses too).
    df = (var_a + var_b) ** 2 / (
        var_a**2 / (a.size - 1) + var_b**2 / (b.size - 1)
    )
    if alternative == "two-sided":
        crit = stats.t.ppf((1 + ci_level) / 2, df)
        ci = (delta - crit * se, delta + crit * se)
    elif alternative == "greater":
        crit = stats.t.ppf(ci_level, df)
        ci = (delta - crit * se, np.inf)
    else:
        crit = stats.t.ppf(ci_level, df)
        ci = (-np.inf, delta + crit * se)

    return UnpairedOutcome(
        delta=delta, ci=(float(ci[0]), float(ci[1])), ci_level=ci_level,
        p_value=float(res.pvalue), n_a=a.size, n_b=b.size,
        method="unpaired_welch_t",
    )


def unpaired_permutation(
    a: np.ndarray,
    b: np.ndarray,
    *,
    alternative: Alt = "two-sided",
    n_resamples: int = 10_000,
    ci_level: float = 0.95,
    rng: int | np.random.Generator = 0,
) -> UnpairedOutcome:
    """Permutation test on the difference of means.

    Under the null, the labels (which run an item came from) are
    interchangeable. We pool the items, shuffle them many times, split
    back into two groups of the original sizes, and see how often a
    shuffled difference is at least as extreme as the observed one.
    """
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    rng = as_rng(rng)
    pooled = np.concatenate([a, b])
    n_a, n_b = a.size, b.size
    observed = float(b.mean() - a.mean())

    # Vectorised shuffles: each row of `perm` is one fresh permutation
    # of the pooled indices.
    perm = np.empty((n_resamples, n_a + n_b), dtype=np.int64)
    base = np.arange(n_a + n_b)
    for r in range(n_resamples):
        rng.shuffle(base)
        perm[r] = base
    shuffled = pooled[perm]
    means_a = shuffled[:, :n_a].mean(axis=1)
    means_b = shuffled[:, n_a:].mean(axis=1)
    null_diffs = means_b - means_a

    if alternative == "two-sided":
        p = (np.sum(np.abs(null_diffs) >= abs(observed)) + 1) / (n_resamples + 1)
    elif alternative == "greater":
        p = (np.sum(null_diffs >= observed) + 1) / (n_resamples + 1)
    else:
        p = (np.sum(null_diffs <= observed) + 1) / (n_resamples + 1)

    # CI from a separate bootstrap. Permutation does not give one
    # directly.
    ci_lo, ci_hi = _bootstrap_diff_ci(a, b, alternative, ci_level,
                                       n_resamples, rng)
    return UnpairedOutcome(
        delta=observed, ci=(ci_lo, ci_hi), ci_level=ci_level,
        p_value=float(p), n_a=n_a, n_b=n_b,
        method="unpaired_permutation",
    )


def unpaired_bootstrap(
    a: np.ndarray,
    b: np.ndarray,
    *,
    alternative: Alt = "two-sided",
    n_resamples: int = 10_000,
    ci_level: float = 0.95,
    rng: int | np.random.Generator = 0,
) -> UnpairedOutcome:
    """Bootstrap CI for the difference of means, with a matching p-value
    read off the centered bootstrap distribution."""
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    rng = as_rng(rng)
    observed = float(b.mean() - a.mean())

    idx_a = rng.integers(0, a.size, size=(n_resamples, a.size))
    idx_b = rng.integers(0, b.size, size=(n_resamples, b.size))
    boot_diffs = b[idx_b].mean(axis=1) - a[idx_a].mean(axis=1)

    ci_lo, ci_hi = _ci_from_boot(boot_diffs, alternative, ci_level)
    centered = boot_diffs - observed
    if alternative == "two-sided":
        p = float(np.mean(np.abs(centered) >= abs(observed)))
    elif alternative == "greater":
        p = float(np.mean(centered >= observed))
    else:
        p = float(np.mean(centered <= observed))
    p = max(p, 1.0 / (n_resamples + 1))

    return UnpairedOutcome(
        delta=observed, ci=(ci_lo, ci_hi), ci_level=ci_level,
        p_value=p, n_a=a.size, n_b=b.size,
        method="unpaired_bootstrap",
    )


def _bootstrap_diff_ci(
    a: np.ndarray, b: np.ndarray, alternative: Alt,
    ci_level: float, n_resamples: int, rng: np.random.Generator,
) -> tuple[float, float]:
    idx_a = rng.integers(0, a.size, size=(n_resamples, a.size))
    idx_b = rng.integers(0, b.size, size=(n_resamples, b.size))
    boot_diffs = b[idx_b].mean(axis=1) - a[idx_a].mean(axis=1)
    return _ci_from_boot(boot_diffs, alternative, ci_level)


def _ci_from_boot(
    boot: np.ndarray, alternative: Alt, ci_level: float
) -> tuple[float, float]:
    if alternative == "two-sided":
        q = (1 - ci_level) / 2
        return float(np.quantile(boot, q)), float(np.quantile(boot, 1 - q))
    if alternative == "greater":
        return float(np.quantile(boot, 1 - ci_level)), float("inf")
    return float("-inf"), float(np.quantile(boot, ci_level))
