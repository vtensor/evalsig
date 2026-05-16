"""Tests for the effect-size estimators."""
from __future__ import annotations

import unittest

import numpy as np

from evalsig.inference.effect_size import (
    cohens_d,
    cohens_d_paired,
    cliffs_delta,
)


class TestCohensD(unittest.TestCase):
    def test_zero_for_equal_means(self) -> None:
        rng = np.random.default_rng(0)
        a = rng.normal(0, 1, 200)
        b = rng.normal(0, 1, 200)
        out = cohens_d(a, b)
        self.assertLess(abs(out.value), 0.3)

    def test_known_value(self) -> None:
        # Two groups with same SD = 1, means differ by 0.5; d should be ~0.5.
        rng = np.random.default_rng(0)
        a = rng.normal(0, 1, 5000)
        b = rng.normal(0.5, 1, 5000)
        out = cohens_d(a, b)
        self.assertAlmostEqual(out.value, 0.5, delta=0.05)
        self.assertEqual(out.magnitude, "medium")


class TestCohensDPaired(unittest.TestCase):
    def test_constant_diff_returns_zero(self) -> None:
        # When the paired diff is exactly constant, SD is zero and d is
        # undefined. We map it to zero / negligible by convention.
        a = np.arange(100, dtype=float)
        b = a + 0.3
        out = cohens_d_paired(a, b)
        self.assertEqual(out.value, 0.0)
        self.assertEqual(out.magnitude, "negligible")

    def test_noisy_lift(self) -> None:
        rng = np.random.default_rng(0)
        a = rng.normal(0, 1, 500)
        b = a + rng.normal(0.5, 0.5, 500)
        out = cohens_d_paired(a, b)
        # mean diff ~0.5, sd diff ~0.5  =>  d ~ 1.0
        self.assertAlmostEqual(out.value, 1.0, delta=0.15)


class TestCliffsDelta(unittest.TestCase):
    def test_b_strictly_greater(self) -> None:
        # If every B is strictly greater than every A, delta = +1.
        a = np.array([1, 2, 3])
        b = np.array([10, 11, 12])
        out = cliffs_delta(a, b)
        self.assertAlmostEqual(out.value, 1.0)

    def test_identical_distributions(self) -> None:
        rng = np.random.default_rng(0)
        a = rng.normal(0, 1, 500)
        b = rng.normal(0, 1, 500)
        out = cliffs_delta(a, b)
        self.assertLess(abs(out.value), 0.1)


if __name__ == "__main__":
    unittest.main()
