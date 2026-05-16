"""Release gate. Turns a ComparisonResult plus a policy into a verdict.

Verdicts and their exit codes (BSD sysexits style):
   ALLOW         -> 0   candidate is significantly better than baseline
                        at the requested minimum effect size
   REJECT        -> 1   the data does not support shipping
   INCONCLUSIVE  -> 2   the run is too small to detect the requested effect
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

import numpy as np

from evalsig.types import ComparisonResult, RunFrame
from evalsig.compare.compare import compare


class GateVerdict(str, Enum):
    ALLOW = "ALLOW"
    REJECT = "REJECT"
    INCONCLUSIVE = "INCONCLUSIVE"


@dataclass(frozen=True)
class GateReport:
    verdict: GateVerdict
    exit_code: int
    comparison: ComparisonResult
    min_delta: float
    alpha: float
    power: float
    suggestion: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict.value,
            "exit_code": self.exit_code,
            "comparison": self.comparison.to_dict(),
            "min_delta": self.min_delta,
            "alpha": self.alpha,
            "power": self.power,
            "suggestion": self.suggestion,
        }


# Verdict to exit-code map. Sorted so the success path is first.
_VERDICT_EXIT = {
    GateVerdict.ALLOW: 0,
    GateVerdict.REJECT: 1,
    GateVerdict.INCONCLUSIVE: 2,
}


def gate(
    a: RunFrame,
    b: RunFrame,
    *,
    min_delta: float,
    alpha: float = 0.05,
    power: float = 0.80,
    method: str = "auto",
    cluster: Optional[str] = None,
    one_sided: bool = True,
    n_resamples: int = 10_000,
    rng: int | np.random.Generator = 0,
) -> GateReport:
    """Should candidate `b` ship over baseline `a`?

    Decision rules, in order:
      1. If the result is significant and the observed delta clears the
         policy threshold: ALLOW.
      2. If the result is not significant and the run was too small to
         detect `min_delta` even if it existed: INCONCLUSIVE.
      3. Otherwise: REJECT (with a note when the effect is real but
         below the policy threshold).
    """
    comp = compare(
        a, b, method=method, cluster=cluster, alpha=alpha, one_sided=one_sided,
        target_power=power, n_resamples=n_resamples, rng=rng,
    )

    suggestion: Optional[str] = None
    if comp.significant and comp.delta >= min_delta:
        verdict = GateVerdict.ALLOW
    elif not comp.significant and comp.mde > min_delta:
        verdict = GateVerdict.INCONCLUSIVE
        # How many items would have been needed? Required N scales with
        # (current_MDE / target_MDE)^2.
        scale = (comp.mde / min_delta) ** 2
        suggested = int(np.ceil(comp.n_pairs * scale))
        suggestion = (
            f"underpowered: detectable effect at {power:.0%} power is "
            f"{comp.mde:.4f}, but you asked to detect {min_delta:.4f}. "
            f"collect ~{suggested - comp.n_pairs:,} more paired items "
            f"(total ~{suggested:,}) and re-run."
        )
    else:
        verdict = GateVerdict.REJECT
        if comp.significant and comp.delta < min_delta:
            suggestion = (
                f"effect is statistically real (p={comp.p_value:.4f}) but "
                f"below the minimum-delta policy of {min_delta:.4f}."
            )

    return GateReport(
        verdict=verdict, exit_code=_VERDICT_EXIT[verdict], comparison=comp,
        min_delta=min_delta, alpha=alpha, power=power, suggestion=suggestion,
    )
