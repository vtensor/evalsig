"""Normalize anything readable into a RunFrame and align two RunFrames.

This is the single entry point for the rest of the package whenever it
needs item-level scores. Readers feed in; aligned numpy arrays feed out.
"""
from __future__ import annotations

import numpy as np

from evalsig.types import RunFrame
from evalsig.compare.compare import align_runs as _align_runs


def normalize(
    a: RunFrame, b: RunFrame
) -> tuple[np.ndarray, np.ndarray, np.ndarray | None, list[str]]:
    """Wrapper that mirrors `align_runs` for callers that prefer to
    import from `evalsig.io.normalize`.

    Returns four things: baseline scores, candidate scores, cluster ids
    (or None), and a list of warning notes.
    """
    return _align_runs(a, b)
