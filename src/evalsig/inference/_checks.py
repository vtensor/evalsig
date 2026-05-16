"""Small input checks used by the inference functions."""
from __future__ import annotations
import numpy as np


def check_paired(a: np.ndarray, b: np.ndarray) -> None:
    # Both sides must line up: same length, 1D, at least two items.
    if a.shape != b.shape:
        raise ValueError(f"paired arrays have mismatched shapes: {a.shape} vs {b.shape}")
    if a.ndim != 1:
        raise ValueError(f"expected 1D arrays, got {a.ndim}D")
    if a.size < 2:
        raise ValueError(f"need at least 2 paired observations, got {a.size}")


def check_clusters(values: np.ndarray, clusters: np.ndarray | None) -> None:
    # If clusters are given, there must be one cluster id per item.
    if clusters is None:
        return
    if clusters.shape != values.shape:
        raise ValueError(f"cluster_id shape {clusters.shape} != values shape {values.shape}")


def as_rng(seed: int | np.random.Generator) -> np.random.Generator:
    # Accept either an int seed or an existing Generator. Always return
    # a Generator so the caller can sample from it.
    if isinstance(seed, np.random.Generator):
        return seed
    return np.random.default_rng(seed)
