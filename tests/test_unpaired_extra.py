"""Tests for the new unpaired permutation and bootstrap tests."""
from __future__ import annotations

import unittest

import numpy as np

from evalsig.inference.unpaired import (
    unpaired_permutation,
    unpaired_bootstrap,
)


class TestUnpairedPermutation(unittest.TestCase):
    def test_no_effect_high_p(self) -> None:
        rng = np.random.default_rng(0)
        a = rng.normal(0, 1, 100)
        b = rng.normal(0, 1, 100)
        out = unpaired_permutation(a, b, n_resamples=1000, rng=0)
        self.assertGreater(out.p_value, 0.05)

    def test_large_effect_low_p(self) -> None:
        rng = np.random.default_rng(0)
        a = rng.normal(0, 1, 100)
        b = rng.normal(1.0, 1, 100)
        out = unpaired_permutation(a, b, alternative="greater",
                                   n_resamples=1000, rng=0)
        self.assertLess(out.p_value, 0.01)


class TestUnpairedBootstrap(unittest.TestCase):
    def test_ci_covers_true_diff(self) -> None:
        rng = np.random.default_rng(0)
        a = rng.normal(0, 1, 500)
        b = rng.normal(0.4, 1, 500)
        out = unpaired_bootstrap(a, b, n_resamples=2000, rng=0)
        lo, hi = out.ci
        self.assertLess(lo, 0.4)
        self.assertGreater(hi, 0.4)


if __name__ == "__main__":
    unittest.main()
