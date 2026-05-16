"""Smoke tests for the inference primitives.

Each test pins one property the math has to satisfy. Run with:
    python -m unittest tests.test_smoke
"""
from __future__ import annotations

import unittest

import numpy as np
from scipy import stats

from evalsig.inference.paired import (
    paired_t_test,
    paired_permutation_test,
    paired_bootstrap_ci,
)
from evalsig.inference.mcnemar import mcnemar_test
from evalsig.inference.cluster_bootstrap import cluster_bootstrap_ci
from evalsig.inference.mde import mde, required_n, estimate_icc
from evalsig.inference.power import power_for_delta


class TestPairedT(unittest.TestCase):
    def test_matches_scipy_ttest_rel(self) -> None:
        # Our p-value should match SciPy's reference paired t-test.
        rng = np.random.default_rng(0)
        a = rng.normal(0, 1, 200)
        b = a + 0.3 + rng.normal(0, 0.1, 200)
        ours = paired_t_test(a, b, alternative="two-sided")
        ref = stats.ttest_rel(b, a, alternative="two-sided")
        self.assertAlmostEqual(ours.p_value, float(ref.pvalue), places=6)
        self.assertAlmostEqual(ours.delta, float((b - a).mean()), places=10)


class TestPairedPermutation(unittest.TestCase):
    def test_zero_effect_high_p(self) -> None:
        # No real effect: p should be far from significant.
        rng = np.random.default_rng(0)
        a = rng.normal(0, 1, 200)
        b = a + rng.normal(0, 0.05, 200)
        out = paired_permutation_test(a, b, alternative="two-sided",
                                       n_resamples=2000, rng=0)
        self.assertGreater(out.p_value, 0.10)

    def test_big_effect_low_p(self) -> None:
        # Big effect: p should be tiny.
        rng = np.random.default_rng(0)
        a = rng.normal(0, 1, 200)
        b = a + 0.5
        out = paired_permutation_test(a, b, alternative="greater",
                                       n_resamples=2000, rng=0)
        self.assertLess(out.p_value, 1e-3)


class TestMcNemar(unittest.TestCase):
    def test_exact_branch_matches_binomtest(self) -> None:
        # Build a known table: 20 concordant correct, 5 concordant wrong,
        # b = 3 (A wins), c = 7 (B wins). The exact p-value should match
        # SciPy's binomtest on the discordant pairs.
        a = np.array([1]*20 + [0]*5 + [1]*3 + [0]*7)
        b = np.array([1]*20 + [0]*5 + [0]*3 + [1]*7)
        out = mcnemar_test(a, b, alternative="two-sided")
        ref = stats.binomtest(7, 10, p=0.5, alternative="two-sided").pvalue
        self.assertAlmostEqual(out.p_value, float(ref), places=6)
        self.assertEqual(out.b_wins, 3)
        self.assertEqual(out.c_wins, 7)


class TestClusterBootstrap(unittest.TestCase):
    def test_widens_ci_under_clustering(self) -> None:
        # When items are grouped, the cluster bootstrap CI must be
        # noticeably wider than the naive one.
        rng = np.random.default_rng(0)
        n_clusters, m = 30, 10
        n = n_clusters * m
        cluster_id = np.repeat(np.arange(n_clusters), m)
        w = rng.normal(0, 0.2, size=n_clusters)
        eps = rng.normal(0, 0.05, size=n)
        d = w[cluster_id] + eps
        a = np.zeros(n)
        b = a + d
        naive = paired_bootstrap_ci(a, b, n_resamples=2000, rng=0)
        clust = cluster_bootstrap_ci(a, b, cluster_id, n_resamples=2000, rng=0)
        naive_w = naive.ci[1] - naive.ci[0]
        clust_w = clust.ci[1] - clust.ci[0]
        self.assertGreater(clust_w, naive_w * 1.5)


class TestMDE(unittest.TestCase):
    def test_required_n_round_trip(self) -> None:
        # If we compute the N needed to detect `target`, then plug that N
        # back into the MDE formula, we should get an MDE no bigger than
        # the target (plus a small rounding allowance).
        target = 0.01
        sd = 0.3
        n = required_n(target, sd, alpha=0.05, power=0.80, one_sided=True)
        m = mde(sd_diff=sd, n_pairs=n, alpha=0.05, power=0.80, one_sided=True)
        self.assertLessEqual(m.mde, target * 1.05)

    def test_deff_inflates_required_n(self) -> None:
        # With 10-item clusters and ICC = 0.20, the design effect is
        # 1 + 9 * 0.20 = 2.8. Required N should grow by roughly that.
        base = required_n(0.01, 0.3, icc=0.0, mean_cluster_size=1)
        clustered = required_n(0.01, 0.3, icc=0.20, mean_cluster_size=10)
        self.assertGreater(clustered, base * 2.5)
        self.assertLess(clustered, base * 3.1)


class TestPower(unittest.TestCase):
    def test_power_at_mde_equals_target(self) -> None:
        # Plugging the MDE back into the power formula should return the
        # power that was originally requested.
        sd, n, alpha, target = 0.3, 1000, 0.05, 0.80
        m = mde(sd_diff=sd, n_pairs=n, alpha=alpha, power=target,
                one_sided=True).mde
        p = power_for_delta(m, sd, n, alpha=alpha, one_sided=True)
        self.assertAlmostEqual(p, target, delta=0.005)


class TestICC(unittest.TestCase):
    def test_icc_zero_for_iid(self) -> None:
        # Independent values should give an ICC near zero.
        rng = np.random.default_rng(0)
        n = 500
        cluster_id = np.repeat(np.arange(50), 10)
        d = rng.normal(0, 1, size=n)
        icc = estimate_icc(d, cluster_id)
        self.assertLess(icc, 0.05)

    def test_icc_high_for_correlated(self) -> None:
        # When every item in a cluster shares a big offset, ICC should
        # be high.
        rng = np.random.default_rng(0)
        cluster_id = np.repeat(np.arange(50), 10)
        w = rng.normal(0, 1, 50)
        d = w[cluster_id] + rng.normal(0, 0.1, 500)
        icc = estimate_icc(d, cluster_id)
        self.assertGreater(icc, 0.7)


if __name__ == "__main__":
    unittest.main()
