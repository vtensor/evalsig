"""Compute the power achieved at a given true effect and sample size.

Power is the chance the test will return "significant" when the effect
really exists. We use the normal approximation: it matches the closed-
form MDE formula and is plenty accurate for the sample sizes we care
about.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
from scipy import stats


def power_for_delta(
    delta: float,
    sd_diff: float,
    n_pairs: int,
    *,
    alpha: float = 0.05,
    one_sided: bool = False,
    n_clusters: Optional[int] = None,
    icc: Optional[float] = None,
) -> float:
    """Probability the test fires at significance level `alpha` when the
    true effect is `delta`."""
    if sd_diff <= 0 or n_pairs < 2:
        return 1.0 if delta != 0 else float(alpha)

    # Cluster adjustment, same as in mde.py.
    deff = 1.0
    if n_clusters and icc is not None and n_clusters > 0:
        m = n_pairs / n_clusters
        deff = 1.0 + (m - 1.0) * max(icc, 0.0)
    n_eff = n_pairs / deff

    # Critical value and the shift of the alternative distribution
    # (how many standard errors away from zero the true effect sits).
    z_a = stats.norm.ppf(1 - alpha) if one_sided else stats.norm.ppf(1 - alpha / 2)
    shift = delta * np.sqrt(n_eff) / sd_diff
    if one_sided:
        return float(stats.norm.sf(z_a - shift))
    return float(stats.norm.sf(z_a - shift) + stats.norm.cdf(-z_a - shift))
