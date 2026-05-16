"""Effect-size statistics that go alongside a p-value.

A p-value tells you whether an effect is real. An effect size tells you
how big it is in interpretable units. We expose three of the most
common ones:

  cohens_d         the mean difference divided by the pooled SD
                   (the standard "small/medium/large" yardstick)
  cohens_d_paired  the mean of the paired differences divided by the
                   SD of those differences
  cliffs_delta     a non-parametric ordinal effect: the probability that
                   a random B item beats a random A item, minus the
                   reverse. Range [-1, +1].
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class EffectSize:
    name: str
    value: float
    # A short human label like "small", "medium", "large".
    magnitude: str


def _label_cohens_d(d: float) -> str:
    # Cohen's original thresholds. They are a rule of thumb, not law.
    a = abs(d)
    if a < 0.2:
        return "negligible"
    if a < 0.5:
        return "small"
    if a < 0.8:
        return "medium"
    return "large"


def cohens_d(a: np.ndarray, b: np.ndarray) -> EffectSize:
    """Two-sample Cohen's d using a pooled standard deviation."""
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    if a.size < 2 or b.size < 2:
        raise ValueError("need at least 2 observations in each group")
    var_a = a.var(ddof=1)
    var_b = b.var(ddof=1)
    pooled = np.sqrt(((a.size - 1) * var_a + (b.size - 1) * var_b)
                     / (a.size + b.size - 2))
    if pooled == 0:
        return EffectSize("cohens_d", 0.0, "negligible")
    d = float((b.mean() - a.mean()) / pooled)
    return EffectSize("cohens_d", d, _label_cohens_d(d))


def cohens_d_paired(a: np.ndarray, b: np.ndarray) -> EffectSize:
    """Cohen's d for paired data. Uses the SD of the per-item difference,
    which is usually much smaller than the pooled SD when the runs are
    correlated."""
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    if a.shape != b.shape:
        raise ValueError("paired arrays must have the same shape")
    d_arr = b - a
    if d_arr.size < 2:
        raise ValueError("need at least 2 paired observations")
    sd = d_arr.std(ddof=1)
    # Treat any near-zero SD as exactly zero. Without this, floating-
    # point noise on a "constant" diff produces a 1e+15 ratio.
    if sd < 1e-12:
        return EffectSize("cohens_d_paired", 0.0, "negligible")
    d = float(d_arr.mean() / sd)
    return EffectSize("cohens_d_paired", d, _label_cohens_d(d))


def _label_cliff(delta: float) -> str:
    # Romano et al. (2006) thresholds.
    a = abs(delta)
    if a < 0.147:
        return "negligible"
    if a < 0.33:
        return "small"
    if a < 0.474:
        return "medium"
    return "large"


def cliffs_delta(a: np.ndarray, b: np.ndarray) -> EffectSize:
    """Cliff's delta: probability(B > A) - probability(A > B), counted
    over all pairs. Ranges from -1 (B always loses) to +1 (B always wins)
    and is invariant to monotone transforms of the data.

    Computed in O(n + m + r) by sorting and walking the merged sequence,
    so it scales to large inputs without a quadratic blow-up.
    """
    a = np.sort(np.asarray(a, dtype=np.float64))
    b = np.asarray(b, dtype=np.float64)
    if a.size == 0 or b.size == 0:
        raise ValueError("need at least one observation in each group")
    # For each b_i, count how many a's are strictly less than it and how
    # many are strictly greater. The middle band is the ties.
    less = np.searchsorted(a, b, side="left").sum()
    less_or_eq = np.searchsorted(a, b, side="right").sum()
    greater = a.size * b.size - less_or_eq
    delta = float((less - greater) / (a.size * b.size))
    return EffectSize("cliffs_delta", delta, _label_cliff(delta))
