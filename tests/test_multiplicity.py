"""Tests for the multiple-comparison corrections."""
from __future__ import annotations

import unittest

import numpy as np

from evalsig.inference.multiplicity import (
    bonferroni,
    holm,
    benjamini_hochberg,
)


class TestBonferroni(unittest.TestCase):
    def test_scales_by_m(self) -> None:
        # p-values 0.01 and 0.04, m=4. Adjusted should be 0.04 and 0.16.
        p = np.array([0.01, 0.04, 0.06, 0.20])
        out = bonferroni(p)
        np.testing.assert_allclose(out.p_adjusted, [0.04, 0.16, 0.24, 0.80])

    def test_caps_at_one(self) -> None:
        out = bonferroni(np.array([0.3, 0.4, 0.5]))
        self.assertTrue((out.p_adjusted <= 1.0).all())


class TestHolm(unittest.TestCase):
    def test_step_down(self) -> None:
        # Sorted p: 0.01, 0.04, 0.06, 0.20 with multipliers 4, 3, 2, 1.
        # Raw adjusted: 0.04, 0.12, 0.12, 0.20. Enforce non-decreasing
        # (already non-decreasing here).
        out = holm(np.array([0.01, 0.04, 0.06, 0.20]))
        np.testing.assert_allclose(out.p_adjusted, [0.04, 0.12, 0.12, 0.20])

    def test_more_powerful_than_bonferroni(self) -> None:
        # Same input: Holm's adjusted p's should be <= Bonferroni's,
        # element-wise.
        p = np.array([0.001, 0.01, 0.02, 0.04, 0.07])
        h = holm(p).p_adjusted
        b = bonferroni(p).p_adjusted
        self.assertTrue((h <= b + 1e-12).all())


class TestBenjaminiHochberg(unittest.TestCase):
    def test_known_values(self) -> None:
        # Standard BH example. p = [0.01, 0.04, 0.06, 0.20].
        # Sorted with rank: (0.01, 1), (0.04, 2), (0.06, 3), (0.20, 4).
        # Raw adjusted = sorted * m / rank = 0.04, 0.08, 0.08, 0.20.
        out = benjamini_hochberg(np.array([0.01, 0.04, 0.06, 0.20]))
        np.testing.assert_allclose(out.p_adjusted, [0.04, 0.08, 0.08, 0.20])

    def test_controls_fdr_on_mixture(self) -> None:
        # Mostly-null sample: tiny p's drawn for "true effects", uniform
        # p's drawn for nulls. BH should reject some of the small ones
        # without exploding the false discovery rate.
        rng = np.random.default_rng(0)
        m_null = 100
        m_true = 20
        nulls = rng.uniform(size=m_null)
        trues = rng.beta(0.5, 50, size=m_true)
        p = np.concatenate([nulls, trues])
        out = benjamini_hochberg(p, alpha=0.05)
        # No more than alpha*m false rejections in the long run; we just
        # check that the rejection set is non-empty for our planted true
        # effects.
        rejected_trues = out.reject[m_null:].sum()
        self.assertGreater(rejected_trues, 5)


if __name__ == "__main__":
    unittest.main()
