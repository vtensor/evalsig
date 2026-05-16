"""Cluster bootstrap for the paired mean difference.

When items belong to groups (a passage with several questions, a template
that spawns many problems), items inside the same group tend to move
together. A normal bootstrap that picks items one by one pretends they
are independent and gives confidence intervals that are too narrow.

The fix is simple: resample whole groups instead of individual items.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

from evalsig.inference._checks import as_rng, check_clusters, check_paired


Alt = Literal["two-sided", "greater", "less"]


@dataclass(frozen=True)
class ClusterBootstrapOutcome:
    delta: float
    ci: tuple[float, float]
    ci_level: float
    p_value: float
    n_pairs: int
    n_clusters: int
    method: str
    sd_diff: float


def cluster_bootstrap_ci(
    a: np.ndarray,
    b: np.ndarray,
    cluster_id: np.ndarray,
    *,
    alternative: Alt = "two-sided",
    ci_level: float = 0.95,
    n_resamples: int = 5_000,
    rng: int | np.random.Generator = 0,
) -> ClusterBootstrapOutcome:
    """Bootstrap CI and p-value where each resample picks whole groups
    of items with replacement."""
    check_paired(a, b)
    check_clusters(a, cluster_id)
    rng = as_rng(rng)

    d = b - a
    observed = float(d.mean())
    sd_d = float(d.std(ddof=1))

    # Build a lookup once: for each unique cluster, the indices that
    # belong to it.
    clusters, inverse = np.unique(cluster_id, return_inverse=True)
    n_clusters = clusters.size
    groups: list[np.ndarray] = [np.where(inverse == k)[0] for k in range(n_clusters)]

    boot_means = np.empty(n_resamples, dtype=np.float64)
    for r in range(n_resamples):
        # Pick `n_clusters` clusters with replacement.
        chosen = rng.integers(0, n_clusters, size=n_clusters)
        # Glue together the diffs from the chosen clusters and take the
        # mean. Each cluster is small so this stays fast.
        sample = np.concatenate([d[groups[k]] for k in chosen])
        boot_means[r] = sample.mean()

    if alternative == "two-sided":
        a_q = (1 - ci_level) / 2
        lo = float(np.quantile(boot_means, a_q))
        hi = float(np.quantile(boot_means, 1 - a_q))
    elif alternative == "greater":
        lo = float(np.quantile(boot_means, 1 - ci_level))
        hi = np.inf
    else:
        lo = -np.inf
        hi = float(np.quantile(boot_means, ci_level))

    # Shift the bootstrap draws to be centered at zero, then count how
    # often a null draw is at least as extreme as what we observed.
    centered = boot_means - observed
    if alternative == "two-sided":
        p = float(np.mean(np.abs(centered) >= abs(observed)))
    elif alternative == "greater":
        p = float(np.mean(centered >= observed))
    else:
        p = float(np.mean(centered <= observed))
    p = max(p, 1.0 / (n_resamples + 1))

    return ClusterBootstrapOutcome(
        delta=observed, ci=(lo, hi), ci_level=ci_level, p_value=p,
        n_pairs=int(a.size), n_clusters=int(n_clusters),
        method="cluster_bootstrap", sd_diff=sd_d,
    )
