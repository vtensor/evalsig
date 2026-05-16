"""Multiple-comparison corrections.

When you run k tests at once (k tasks in a release suite, k subgroups in
an audit), the chance of at least one false positive grows with k. The
two standard remedies are:

  Family-wise error rate (FWER) control: keep the chance of any false
  positive below alpha. Methods: Bonferroni (simple, conservative), Holm
  (step-down, uniformly more powerful than Bonferroni).

  False discovery rate (FDR) control: keep the *expected fraction* of
  false positives among rejections below alpha. Method:
  Benjamini-Hochberg (BH).

Each function takes a 1D array of p-values and returns adjusted p-values
the same length, plus a boolean array marking which to reject at the
given alpha.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class MultipleTestResult:
    method: str
    p_adjusted: np.ndarray
    reject: np.ndarray
    alpha: float


def bonferroni(p_values: np.ndarray, *, alpha: float = 0.05) -> MultipleTestResult:
    """Multiply every p-value by the number of tests, capping at 1.

    Controls the family-wise error rate at `alpha`.
    """
    p = np.asarray(p_values, dtype=np.float64)
    m = p.size
    adj = np.minimum(p * m, 1.0)
    return MultipleTestResult("bonferroni", adj, adj < alpha, alpha)


def holm(p_values: np.ndarray, *, alpha: float = 0.05) -> MultipleTestResult:
    """Holm step-down. Sort p-values ascending, multiply the i-th smallest
    by (m - i), then enforce monotone non-decreasing adjusted p-values.

    More powerful than Bonferroni while keeping the same FWER guarantee.
    """
    p = np.asarray(p_values, dtype=np.float64)
    m = p.size
    order = np.argsort(p)
    sorted_p = p[order]
    # Multiplier shrinks from m down to 1 as we walk through ordered p's.
    multipliers = np.arange(m, 0, -1)
    adj_sorted = np.minimum(sorted_p * multipliers, 1.0)
    # Enforce non-decreasing: each adjusted p must be >= the previous.
    adj_sorted = np.maximum.accumulate(adj_sorted)
    adj = np.empty_like(adj_sorted)
    adj[order] = adj_sorted
    return MultipleTestResult("holm", adj, adj < alpha, alpha)


def benjamini_hochberg(p_values: np.ndarray, *, alpha: float = 0.05
                       ) -> MultipleTestResult:
    """Benjamini-Hochberg FDR control.

    Sort p ascending. For the i-th smallest (1-indexed), the adjusted
    p-value is min over j >= i of (m / j) * p_(j), all clipped to [0, 1].
    """
    p = np.asarray(p_values, dtype=np.float64)
    m = p.size
    order = np.argsort(p)
    sorted_p = p[order]
    ranks = np.arange(1, m + 1)
    raw = sorted_p * m / ranks
    # Walk from the largest rank backwards, taking the running minimum.
    adj_sorted = np.minimum.accumulate(raw[::-1])[::-1]
    adj_sorted = np.minimum(adj_sorted, 1.0)
    adj = np.empty_like(adj_sorted)
    adj[order] = adj_sorted
    return MultipleTestResult("benjamini_hochberg", adj, adj < alpha, alpha)
