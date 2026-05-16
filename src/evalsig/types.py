"""The data shapes that travel between modules.

The design doc plans for Pydantic. For now we use plain dataclasses to
keep the install down to numpy and scipy. The fields are the same; we
can swap in Pydantic later without changing any call sites.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence


@dataclass(frozen=True)
class ItemResult:
    # One row of an eval: the score on a single item.
    item_id: str
    score: float
    cluster_id: Optional[str] = None
    epoch: int = 0
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class RunFrame:
    """One model's run on one task."""
    run_id: str
    model_id: str
    task_id: str
    metric_name: str
    items: Sequence[ItemResult]
    config_hash: str = ""

    def __post_init__(self) -> None:
        # Even a frozen dataclass can run a post-init check.
        if not self.items:
            raise ValueError(f"RunFrame {self.run_id} has no items")


@dataclass(frozen=True)
class ComparisonResult:
    delta: float
    ci: tuple[float, float]
    ci_level: float
    p_value: float
    significant: bool
    n_pairs: int
    n_clusters: Optional[int]
    method: str
    mde: float
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        # JSON-friendly view, for writing reports.
        return {
            "delta": self.delta,
            "ci": list(self.ci),
            "ci_level": self.ci_level,
            "p_value": self.p_value,
            "significant": self.significant,
            "n_pairs": self.n_pairs,
            "n_clusters": self.n_clusters,
            "method": self.method,
            "mde": self.mde,
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class MDEResult:
    """Result of an MDE computation (and its inputs, for transparency)."""
    mde: float
    alpha: float
    power: float
    n_pairs: int
    sd_diff: float
    n_clusters: Optional[int] = None
    icc: Optional[float] = None      # within-cluster correlation, if clustered
    deff: Optional[float] = None     # design effect = 1 + (m-1)*icc
