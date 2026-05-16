"""McNemar's test for two runs scored 0/1 on the same items.

Only the items where the two runs disagree carry information. We call
them "discordant pairs":
   b = items where A got it right and B got it wrong
   c = items where A got it wrong and B got it right
If neither model is really better, b and c should be about equal. We use
the exact binomial test when (b + c) is small and a chi-squared
approximation when it is large.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
from scipy import stats


Alt = Literal["two-sided", "greater", "less"]


@dataclass(frozen=True)
class McNemarOutcome:
    delta: float
    b_wins: int
    c_wins: int
    p_value: float
    n_pairs: int
    method: str
    ci: tuple[float, float]
    ci_level: float


def mcnemar_test(
    a: np.ndarray,
    b: np.ndarray,
    *,
    alternative: Alt = "two-sided",
    ci_level: float = 0.95,
    exact_threshold: int = 25,
) -> McNemarOutcome:
    """Run McNemar on two 0/1 score arrays of the same length."""
    a = np.asarray(a).astype(int)
    b = np.asarray(b).astype(int)
    if not (np.isin(a, [0, 1]).all() and np.isin(b, [0, 1]).all()):
        raise ValueError("McNemar requires binary {0,1} scores on both sides")

    b_wins = int(np.sum((a == 1) & (b == 0)))
    c_wins = int(np.sum((a == 0) & (b == 1)))
    n = a.size
    discordant = b_wins + c_wins
    delta = float(b.mean() - a.mean())

    if discordant == 0:
        # Both runs agree on every item: no signal in either direction.
        p = 1.0
    elif discordant <= exact_threshold:
        # Small number of disagreements: use the exact binomial. Under
        # the null, the count of B-wins among the discordant pairs is
        # Binomial(discordant, 0.5).
        alt = {"two-sided": "two-sided", "greater": "greater", "less": "less"}[alternative]
        p = float(stats.binomtest(c_wins, discordant, p=0.5, alternative=alt).pvalue)
    else:
        # Plenty of disagreements: use the chi-squared approximation
        # with the continuity correction for two-sided, normal-Z for
        # one-sided.
        if alternative == "two-sided":
            chi2 = (abs(b_wins - c_wins) - 1) ** 2 / discordant
            p = float(stats.chi2.sf(chi2, df=1))
        else:
            z = (c_wins - b_wins) / np.sqrt(discordant)
            p = float(stats.norm.sf(z) if alternative == "greater" else stats.norm.cdf(z))

    # CI for delta = (c - b) / n, using the standard Wald formula.
    diff = (c_wins - b_wins) / n
    var = (discordant - (c_wins - b_wins) ** 2 / n) / (n ** 2)
    se = float(np.sqrt(max(var, 0.0)))
    if alternative == "two-sided":
        z = stats.norm.ppf((1 + ci_level) / 2)
        ci = (diff - z * se, diff + z * se)
    elif alternative == "greater":
        z = stats.norm.ppf(ci_level)
        ci = (diff - z * se, np.inf)
    else:
        z = stats.norm.ppf(ci_level)
        ci = (-np.inf, diff + z * se)

    return McNemarOutcome(
        delta=delta, b_wins=b_wins, c_wins=c_wins, p_value=p, n_pairs=n,
        method="mcnemar_exact" if discordant <= exact_threshold else "mcnemar_chi2",
        ci=(float(ci[0]), float(ci[1])), ci_level=ci_level,
    )
