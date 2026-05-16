"""Tests for the always-valid sequential test."""
from __future__ import annotations

import unittest

import numpy as np

from evalsig.inference.sequential import (
    confidence_sequence,
    sequential_gate,
)


class TestConfidenceSequence(unittest.TestCase):
    def test_width_shrinks_with_n(self) -> None:
        rng = np.random.default_rng(0)
        x = rng.normal(0, 1, 100)
        narrow = confidence_sequence(np.concatenate([x] * 100))  # n=10_000
        wide = confidence_sequence(x)
        narrow_w = narrow.ci[1] - narrow.ci[0]
        wide_w = wide.ci[1] - wide.ci[0]
        self.assertGreater(wide_w, narrow_w * 5)

    def test_zero_data_safe(self) -> None:
        out = confidence_sequence(np.zeros(0))
        # Just make sure it returns without crashing.
        self.assertEqual(out.n_pairs, 0)


class TestSequentialGate(unittest.TestCase):
    def test_stops_on_real_effect(self) -> None:
        rng = np.random.default_rng(0)
        # 2000 i.i.d. diffs with positive mean. Should stop well before
        # the end.
        diffs = rng.normal(0.10, 0.3, 2000)
        out = sequential_gate(diffs, alternative="greater")
        self.assertTrue(out.stopped)
        self.assertLess(out.n_pairs, 2000)

    def test_does_not_stop_under_null(self) -> None:
        # Under the null (mean=0), even very long streams should mostly
        # not stop. We allow one stop in N runs as randomness.
        rng = np.random.default_rng(0)
        stops = 0
        for _ in range(10):
            diffs = rng.normal(0.0, 1.0, 1000)
            out = sequential_gate(diffs, alternative="greater", alpha=0.05)
            stops += int(out.stopped)
        self.assertLessEqual(stops, 2)


if __name__ == "__main__":
    unittest.main()
