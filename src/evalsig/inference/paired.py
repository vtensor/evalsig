"""Paired-difference tests: t, permutation, bootstrap.

We focus on paired tests because both runs see the same items, so item-
level luck cancels out. That gives much tighter results than treating the
two runs as independent samples.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
from scipy import stats

from evalsig.inference._checks import as_rng, check_paired


Alt = Literal["two-sided", "greater", "less"]


@dataclass(frozen=True)
class PairedOutcome:
    delta: float
    ci: tuple[float, float]
    ci_level: float
    p_value: float
    n_pairs: int
    method: str
    sd_diff: float


def _ci_from_alt(level: float, alt: Alt) -> tuple[float, float]:
    # Pick the right quantiles for the requested confidence interval.
    # Two-sided is symmetric; one-sided pushes one tail to plus or minus
    # infinity.
    if alt == "two-sided":
        a = (1 - level) / 2
        return (a, 1 - a)
    if alt == "greater":
        return (1 - level, 1.0)
    return (0.0, level)


def paired_t_test(
    a: np.ndarray,
    b: np.ndarray,
    *,
    alternative: Alt = "two-sided",
    ci_level: float = 0.95,
) -> PairedOutcome:
    """Standard paired t-test on the per-item differences `b - a`.

    Cheap and correct when there are enough items and the differences
    are not too skewed. For small or skewed samples the auto-selector
    will pick the permutation test instead.
    """
    check_paired(a, b)
    d = b - a
    n = d.size
    mean_d = float(d.mean())
    sd_d = float(d.std(ddof=1))
    se = sd_d / np.sqrt(n)
    df = n - 1

    if se == 0.0:
        # No variance at all: every pair has the same difference. There's
        # nothing to test; return the observed value with p = 1 (or 0 if
        # the diff itself is nonzero).
        p = 1.0 if mean_d == 0.0 else 0.0
        return PairedOutcome(
            delta=mean_d, ci=(mean_d, mean_d), ci_level=ci_level,
            p_value=p, n_pairs=n, method="paired_t", sd_diff=0.0,
        )

    t_stat = mean_d / se
    if alternative == "two-sided":
        p = float(2 * stats.t.sf(abs(t_stat), df))
    elif alternative == "greater":
        p = float(stats.t.sf(t_stat, df))
    else:
        p = float(stats.t.cdf(t_stat, df))

    lo_q, hi_q = _ci_from_alt(ci_level, alternative)
    lo = mean_d + stats.t.ppf(lo_q, df) * se if np.isfinite(lo_q) and lo_q > 0 else -np.inf
    hi = mean_d + stats.t.ppf(hi_q, df) * se if np.isfinite(hi_q) and hi_q < 1 else np.inf
    return PairedOutcome(
        delta=mean_d, ci=(float(lo), float(hi)), ci_level=ci_level,
        p_value=p, n_pairs=n, method="paired_t", sd_diff=sd_d,
    )


def paired_permutation_test(
    a: np.ndarray,
    b: np.ndarray,
    *,
    alternative: Alt = "two-sided",
    ci_level: float = 0.95,
    n_resamples: int = 10_000,
    rng: int | np.random.Generator = 0,
) -> PairedOutcome:
    """Permutation test on the per-item differences.

    If there is no real effect, the sign of each difference is just as
    likely to be + as -. So we flip the signs at random many times,
    recompute the mean difference each time, and see how often a random
    flip beats the real one. That fraction is the p-value.

    The CI is built from a separate paired bootstrap because permutation
    alone does not give you one.
    """
    check_paired(a, b)
    rng = as_rng(rng)
    d = b - a
    n = d.size
    observed = float(d.mean())
    sd_d = float(d.std(ddof=1))

    # Vectorised sign flips. Each row is one "what if" sample of size n.
    signs = rng.choice(np.array([-1.0, 1.0]), size=(n_resamples, n))
    null_means = (signs * d).mean(axis=1)

    if alternative == "two-sided":
        # The "+1" in the numerator avoids reporting p = 0 from finite
        # resampling. It is the standard small-sample correction.
        p = float((np.sum(np.abs(null_means) >= abs(observed)) + 1) / (n_resamples + 1))
    elif alternative == "greater":
        p = float((np.sum(null_means >= observed) + 1) / (n_resamples + 1))
    else:
        p = float((np.sum(null_means <= observed) + 1) / (n_resamples + 1))

    # Bootstrap CI: resample the diffs with replacement, take quantiles.
    idx = rng.integers(0, n, size=(n_resamples, n))
    boot_means = d[idx].mean(axis=1)
    lo_q, hi_q = _ci_from_alt(ci_level, alternative)
    lo = float(np.quantile(boot_means, lo_q)) if lo_q > 0 else -np.inf
    hi = float(np.quantile(boot_means, hi_q)) if hi_q < 1 else np.inf

    return PairedOutcome(
        delta=observed, ci=(lo, hi), ci_level=ci_level, p_value=p,
        n_pairs=n, method="paired_permutation", sd_diff=sd_d,
    )


def paired_bootstrap_ci(
    a: np.ndarray,
    b: np.ndarray,
    *,
    alternative: Alt = "two-sided",
    ci_level: float = 0.95,
    n_resamples: int = 10_000,
    rng: int | np.random.Generator = 0,
) -> PairedOutcome:
    """Bootstrap CI for the paired mean difference.

    Resample the per-item differences with replacement, recompute the
    mean each time, then take quantiles of those means as the CI.
    The p-value is read off the bootstrap distribution shifted to zero.
    """
    check_paired(a, b)
    rng = as_rng(rng)
    d = b - a
    n = d.size
    observed = float(d.mean())
    sd_d = float(d.std(ddof=1))

    idx = rng.integers(0, n, size=(n_resamples, n))
    boot_means = d[idx].mean(axis=1)

    lo_q, hi_q = _ci_from_alt(ci_level, alternative)
    lo = float(np.quantile(boot_means, lo_q)) if lo_q > 0 else -np.inf
    hi = float(np.quantile(boot_means, hi_q)) if hi_q < 1 else np.inf

    # Shift the bootstrap draws to be centered at zero, then ask how
    # often those "null" draws are at least as extreme as the observed
    # difference. That fraction is the p-value.
    centered = boot_means - observed
    if alternative == "two-sided":
        p = float(np.mean(np.abs(centered) >= abs(observed)))
    elif alternative == "greater":
        p = float(np.mean(centered >= observed))
    else:
        p = float(np.mean(centered <= observed))
    # Floor p so it is never exactly zero with finite resamples.
    p = max(p, 1.0 / (n_resamples + 1))

    return PairedOutcome(
        delta=observed, ci=(lo, hi), ci_level=ci_level, p_value=p,
        n_pairs=n, method="paired_bootstrap", sd_diff=sd_d,
    )
