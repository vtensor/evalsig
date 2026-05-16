"""Top-level `compare()` function.

It takes two RunFrames, lines them up on item id, picks the right test
based on the data, and returns a single ComparisonResult. The CLI and
the SaaS dashboard both go through this entry point.
"""
from __future__ import annotations

from typing import Literal, Optional

import numpy as np

from evalsig.types import ComparisonResult, RunFrame
from evalsig.inference.paired import (
    paired_t_test,
    paired_permutation_test,
    paired_bootstrap_ci,
)
from evalsig.inference.mcnemar import mcnemar_test
from evalsig.inference.cluster_bootstrap import cluster_bootstrap_ci
from evalsig.inference.mde import mde as compute_mde, estimate_icc


Method = Literal[
    "auto",
    "paired_t",
    "paired_permutation",
    "paired_bootstrap",
    "mcnemar",
    "cluster_bootstrap",
]


def align_runs(
    a: RunFrame, b: RunFrame
) -> tuple[np.ndarray, np.ndarray, np.ndarray | None, list[str]]:
    """Line up two runs by item id.

    Returns four things: the baseline scores, the candidate scores, the
    cluster ids (or None if neither run carries them), and any warning
    notes for the caller.
    """
    notes: list[str] = []

    def index(run: RunFrame) -> dict[str, tuple[float, Optional[str]]]:
        # Build {item_id -> (score, cluster_id)}. v1 only uses epoch 0.
        out: dict[str, tuple[float, Optional[str]]] = {}
        for it in run.items:
            if it.epoch != 0:
                continue
            out[it.item_id] = (float(it.score), it.cluster_id)
        return out

    ia = index(a)
    ib = index(b)
    common = sorted(set(ia) & set(ib))
    if not common:
        raise ValueError("no overlapping item_ids between the two runs")
    missing_in_b = len(ia) - len(common)
    missing_in_a = len(ib) - len(common)
    coverage = len(common) / max(len(ia), len(ib))
    if coverage < 0.95:
        notes.append(
            f"item-set coverage is {coverage:.1%} (below 95%); "
            f"{missing_in_a} items only in candidate, {missing_in_b} only in baseline"
        )

    sa = np.array([ia[k][0] for k in common], dtype=np.float64)
    sb = np.array([ib[k][0] for k in common], dtype=np.float64)
    # Trust baseline's cluster assignment when the two runs disagree,
    # and warn the caller.
    ca_raw = [ia[k][1] for k in common]
    cb_raw = [ib[k][1] for k in common]
    mismatches = sum(1 for x, y in zip(ca_raw, cb_raw) if x != y)
    if mismatches:
        notes.append(
            f"{mismatches} item(s) have cluster_id mismatch between runs; "
            "using baseline's cluster assignment"
        )
    if all(c is None for c in ca_raw):
        clusters: np.ndarray | None = None
    else:
        clusters = np.array(["__none__" if c is None else c for c in ca_raw])
    return sa, sb, clusters, notes


def _is_binary(arr: np.ndarray) -> bool:
    # True if every value is 0 or 1.
    return np.array_equal(np.unique(arr), np.array([0.0, 1.0])) or np.array_equal(
        np.unique(arr), np.array([0.0])
    ) or np.array_equal(np.unique(arr), np.array([1.0]))


def _auto_method(
    sa: np.ndarray, sb: np.ndarray, clusters: np.ndarray | None
) -> Method:
    """Pick a sensible default test based on the data.

    Rules:
      - If items are grouped, use the cluster bootstrap.
      - If both runs are 0/1 and items are not grouped, use McNemar.
      - Otherwise, use the paired permutation test (no distributional
        assumptions).
    """
    if clusters is not None:
        return "cluster_bootstrap"
    if _is_binary(sa) and _is_binary(sb):
        return "mcnemar"
    return "paired_permutation"


def compare(
    a: RunFrame,
    b: RunFrame,
    *,
    method: Method = "auto",
    cluster: Optional[str] = None,
    alpha: float = 0.05,
    one_sided: bool = False,
    target_power: float = 0.80,
    n_resamples: int = 10_000,
    rng: int | np.random.Generator = 0,
) -> ComparisonResult:
    """Compare two runs and return delta, CI, p-value, MDE, and verdict."""
    sa, sb, clusters, notes = align_runs(a, b)

    # Reconcile the user's cluster choice with what the data carries.
    if cluster is not None and clusters is None:
        notes.append(f"cluster='{cluster}' requested but RunFrames carry no cluster_id; ignoring")
    if cluster is None and clusters is not None:
        notes.append(
            "RunFrames carry cluster_id; pass cluster=<name> to opt into cluster-aware inference"
        )
        clusters = None

    chosen = _auto_method(sa, sb, clusters) if method == "auto" else method
    alternative = "greater" if one_sided else "two-sided"
    ci_level = 1.0 - alpha

    if chosen == "paired_t":
        out = paired_t_test(sa, sb, alternative=alternative, ci_level=ci_level)
        sd = out.sd_diff
        n_clusters: Optional[int] = None
        icc: Optional[float] = None
    elif chosen == "paired_permutation":
        out = paired_permutation_test(sa, sb, alternative=alternative,
                                      ci_level=ci_level, n_resamples=n_resamples, rng=rng)
        sd = out.sd_diff; n_clusters = None; icc = None
    elif chosen == "paired_bootstrap":
        out = paired_bootstrap_ci(sa, sb, alternative=alternative,
                                  ci_level=ci_level, n_resamples=n_resamples, rng=rng)
        sd = out.sd_diff; n_clusters = None; icc = None
    elif chosen == "mcnemar":
        out = mcnemar_test(sa, sb, alternative=alternative, ci_level=ci_level)
        # SD of the per-item diff (binary case), used for MDE.
        sd = float((sb - sa).std(ddof=1)) if sa.size > 1 else 0.0
        n_clusters = None; icc = None
    elif chosen == "cluster_bootstrap":
        if clusters is None:
            raise ValueError("cluster_bootstrap requires cluster_id on both runs")
        out = cluster_bootstrap_ci(sa, sb, clusters, alternative=alternative,
                                   ci_level=ci_level, n_resamples=n_resamples, rng=rng)
        sd = out.sd_diff
        n_clusters = out.n_clusters
        icc = estimate_icc(sb - sa, clusters)
    else:
        raise ValueError(f"unknown method: {chosen}")

    mde_res = compute_mde(
        sd_diff=sd, n_pairs=int(sa.size),
        alpha=alpha, power=target_power, one_sided=one_sided,
        n_clusters=n_clusters, icc=icc,
    )

    significant = out.p_value < alpha
    # For a one-sided "B better than A" test, also require a positive
    # observed delta. Otherwise a tiny p-value paired with a negative
    # delta would look "significant" but in the wrong direction.
    if one_sided and out.delta <= 0:
        significant = False

    return ComparisonResult(
        delta=float(out.delta),
        ci=(float(out.ci[0]), float(out.ci[1])),
        ci_level=ci_level,
        p_value=float(out.p_value),
        significant=bool(significant),
        n_pairs=int(sa.size),
        n_clusters=n_clusters,
        method=out.method,
        mde=float(mde_res.mde),
        notes=tuple(notes),
    )
