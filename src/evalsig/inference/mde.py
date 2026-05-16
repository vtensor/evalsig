"""Minimum detectable effect (MDE) and the inverse: required sample size.

MDE is the smallest true effect your run could reliably detect, given
how many items you have, how spread out the per-item differences are,
and the alpha/power you want.

When items are grouped, items inside a cluster carry less independent
information. We adjust for that by inflating the variance by the "design
effect":  deff = 1 + (m - 1) * icc
where m is the mean cluster size and icc is the correlation of the
differences within a cluster.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
from scipy import stats

from evalsig.types import MDEResult


def _z(alpha: float, one_sided: bool) -> float:
    # Critical value for the requested alpha. One-sided uses the full
    # tail; two-sided splits it.
    if one_sided:
        return float(stats.norm.ppf(1 - alpha))
    return float(stats.norm.ppf(1 - alpha / 2))


def mde(
    sd_diff: float,
    n_pairs: int,
    *,
    alpha: float = 0.05,
    power: float = 0.80,
    one_sided: bool = False,
    n_clusters: Optional[int] = None,
    icc: Optional[float] = None,
) -> MDEResult:
    """Smallest effect detectable at the requested power.

    The formula is:
        MDE = (z_alpha + z_beta) * sd_diff / sqrt(n_eff)
    where n_eff is the sample size after the cluster adjustment (or just
    n_pairs if items are not clustered).
    """
    if sd_diff <= 0:
        return MDEResult(mde=0.0, alpha=alpha, power=power, n_pairs=n_pairs,
                         sd_diff=sd_diff, n_clusters=n_clusters, icc=icc,
                         deff=1.0 if icc is not None else None)
    if n_pairs < 2:
        return MDEResult(mde=float("inf"), alpha=alpha, power=power,
                         n_pairs=n_pairs, sd_diff=sd_diff,
                         n_clusters=n_clusters, icc=icc, deff=None)

    z_a = _z(alpha, one_sided)
    z_b = float(stats.norm.ppf(power))

    deff = None
    n_eff = float(n_pairs)
    if n_clusters and icc is not None and n_clusters > 0:
        m = n_pairs / n_clusters
        deff = 1.0 + (m - 1.0) * max(icc, 0.0)
        n_eff = n_pairs / deff

    mde_val = (z_a + z_b) * sd_diff / np.sqrt(n_eff)
    return MDEResult(
        mde=float(mde_val), alpha=alpha, power=power, n_pairs=n_pairs,
        sd_diff=float(sd_diff), n_clusters=n_clusters, icc=icc, deff=deff,
    )


def required_n(
    target_delta: float,
    sd_diff: float,
    *,
    alpha: float = 0.05,
    power: float = 0.80,
    one_sided: bool = False,
    icc: float = 0.0,
    mean_cluster_size: float = 1.0,
) -> int:
    """How many paired items do we need to detect `target_delta` with
    the requested alpha and power? Inverts the MDE formula."""
    if target_delta <= 0:
        raise ValueError("target_delta must be > 0")
    z_a = _z(alpha, one_sided)
    z_b = float(stats.norm.ppf(power))
    n = ((z_a + z_b) * sd_diff / target_delta) ** 2
    deff = 1.0 + (mean_cluster_size - 1.0) * max(icc, 0.0)
    return int(np.ceil(n * deff))


def estimate_icc(values: np.ndarray, cluster_id: np.ndarray) -> float:
    """Estimate the within-cluster correlation of the per-item diffs.

    Uses the standard one-way ANOVA estimator. Negative estimates are
    clipped to zero, since a negative correlation in this setting almost
    always means sampling noise rather than a real effect.
    """
    clusters, inverse = np.unique(cluster_id, return_inverse=True)
    k = clusters.size
    n = values.size
    if k < 2 or n - k < 1:
        return 0.0
    overall = values.mean()
    ss_between = 0.0
    ss_within = 0.0
    for j in range(k):
        idx = np.where(inverse == j)[0]
        group = values[idx]
        gm = group.mean()
        # Between-group sum of squares and within-group sum of squares.
        ss_between += idx.size * (gm - overall) ** 2
        ss_within += float(((group - gm) ** 2).sum())
    ms_between = ss_between / (k - 1)
    ms_within = ss_within / (n - k) if (n - k) > 0 else 0.0
    m = n / k
    denom = ms_between + (m - 1) * ms_within
    if denom <= 0:
        return 0.0
    icc = (ms_between - ms_within) / denom
    return float(max(icc, 0.0))
