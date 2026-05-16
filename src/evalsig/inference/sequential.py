"""Always-valid sequential testing for paired differences.

The usual t-test loses its alpha guarantee if you peek at the data and
stop early. Sequential tests fix that by giving you a confidence
sequence that is valid at every sample size, so you can stop as soon as
the interval excludes zero without inflating false positives.

We implement the Howard et al. (2021) "asymptotic confidence sequence"
for the running mean of bounded i.i.d. observations. The half-width at
time t is

    width(t) = sigma * sqrt( (2 * (t + rho^2) * log( sqrt(t + rho^2) / (alpha * rho) )) / t^2 )

where `rho` is a tuning parameter chosen so the bound is sharpest near
the "expected stopping time". A default rho works well in practice; users
can override it.

When the lower edge of the CI rises above zero (or the upper edge falls
below zero, depending on direction), you stop and report "significant".
The alpha is spent globally, so this is safe even if you check after
every new item.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal

import numpy as np


Alt = Literal["two-sided", "greater", "less"]


@dataclass(frozen=True)
class SequentialOutcome:
    delta: float
    ci: tuple[float, float]
    ci_level: float
    n_pairs: int
    stopped: bool
    method: str
    half_width: float


def _half_width(t: int, sigma: float, alpha: float, rho: float) -> float:
    """Howard 2021 mixture-supermartingale half-width.

    For t < 1 the bound is infinite; we treat that as "not enough data".
    """
    if t < 1 or sigma <= 0:
        return float("inf")
    tt = t + rho ** 2
    arg = max(np.sqrt(tt) / (alpha * rho), 1.0 + 1e-12)
    return float(sigma * np.sqrt(2 * tt * np.log(arg)) / t)


def confidence_sequence(
    diffs: np.ndarray,
    *,
    alpha: float = 0.05,
    rho: float = 1.0,
    sigma_bound: float | None = None,
) -> SequentialOutcome:
    """Compute the running CI at the *current* sample size only.

    Use this for batch use; for streaming, prefer `sequential_gate`.
    """
    d = np.asarray(diffs, dtype=np.float64)
    n = d.size
    mean = float(d.mean()) if n > 0 else 0.0
    # Estimate sigma from data unless caller supplied a bound (the
    # theoretical guarantees require an upper bound on the per-item SD).
    sigma = float(d.std(ddof=1)) if n > 1 else 1.0
    if sigma_bound is not None:
        sigma = max(sigma, sigma_bound)
    hw = _half_width(n, sigma, alpha, rho)
    return SequentialOutcome(
        delta=mean,
        ci=(mean - hw, mean + hw),
        ci_level=1 - alpha,
        n_pairs=n,
        stopped=(hw < abs(mean)) if n > 0 else False,
        method="howard_2021_acs",
        half_width=hw,
    )


def sequential_gate(
    stream: Iterable[float],
    *,
    alpha: float = 0.05,
    alternative: Alt = "greater",
    rho: float = 1.0,
    min_n: int = 30,
    sigma_bound: float | None = None,
) -> SequentialOutcome:
    """Walk through `stream` of paired differences one at a time. Stop
    as soon as the confidence sequence excludes zero in the requested
    direction (or runs out of items).

    Returns the outcome at the stopping point. `stopped=True` means the
    test fired; `stopped=False` means we walked the whole stream without
    crossing the boundary.

    `min_n` is a small warm-up: we never claim significance below this
    sample size, because the early bound is essentially infinite.
    """
    seen: list[float] = []
    last: SequentialOutcome | None = None
    for x in stream:
        seen.append(float(x))
        if len(seen) < min_n:
            continue
        out = confidence_sequence(np.array(seen), alpha=alpha, rho=rho,
                                  sigma_bound=sigma_bound)
        last = out
        lo, hi = out.ci
        if alternative == "greater" and lo > 0:
            return SequentialOutcome(
                delta=out.delta, ci=out.ci, ci_level=out.ci_level,
                n_pairs=out.n_pairs, stopped=True, method=out.method,
                half_width=out.half_width,
            )
        if alternative == "less" and hi < 0:
            return SequentialOutcome(
                delta=out.delta, ci=out.ci, ci_level=out.ci_level,
                n_pairs=out.n_pairs, stopped=True, method=out.method,
                half_width=out.half_width,
            )
        if alternative == "two-sided" and (lo > 0 or hi < 0):
            return SequentialOutcome(
                delta=out.delta, ci=out.ci, ci_level=out.ci_level,
                n_pairs=out.n_pairs, stopped=True, method=out.method,
                half_width=out.half_width,
            )
    # Stream exhausted with no rejection.
    if last is None:
        # Stream was too short for the warm-up; return a no-op result.
        arr = np.array(seen) if seen else np.zeros(0)
        return confidence_sequence(arr, alpha=alpha, rho=rho,
                                   sigma_bound=sigma_bound)
    return last
