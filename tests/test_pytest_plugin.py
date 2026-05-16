"""Tests for the pytest plugin integration.

We exercise the fixture class directly instead of spawning pytest, so
the test suite stays self-contained.
"""
from __future__ import annotations

import unittest

import numpy as np

from evalsig.integrations.pytest_plugin import EvalsigGateFixture
from evalsig.types import ItemResult, RunFrame


def _mk(run_id: str, model: str, lift: float, seed: int) -> RunFrame:
    rng = np.random.default_rng(seed)
    theta = rng.beta(4, 2, size=500)
    c = rng.random(500)
    scores = (c < np.clip(theta + lift, 0, 1)).astype(float)
    return RunFrame(
        run_id=run_id, model_id=model, task_id="t",
        metric_name="accuracy",
        items=[ItemResult(item_id=f"i{i}", score=float(scores[i]))
               for i in range(500)],
    )


class TestEvalsigGateFixture(unittest.TestCase):
    def test_allow_when_lift_real(self) -> None:
        fx = EvalsigGateFixture()
        a = _mk("a", "m1", lift=0.00, seed=1)
        b = _mk("b", "m2", lift=0.05, seed=1)
        # Should NOT raise.
        fx.assert_no_regression(a, b, min_delta=0.01)

    def test_raises_when_no_lift(self) -> None:
        # Same seed = identical scores on every item. Delta is exactly
        # zero, p-value is 1, and the fixture must raise.
        fx = EvalsigGateFixture()
        a = _mk("a", "m1", lift=0.00, seed=42)
        b = _mk("b", "m2", lift=0.00, seed=42)
        with self.assertRaises(AssertionError):
            fx.assert_no_regression(a, b, min_delta=0.01)


if __name__ == "__main__":
    unittest.main()
