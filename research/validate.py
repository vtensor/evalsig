"""End-to-end check that EVALSIG does what the design doc promises.

The doc says: "frontier labs ship model updates on 1 to 3 percentage-point
eval deltas, and Anthropic measured a 6pp swing on Terminal-Bench from
infrastructure config alone. EVALSIG is the release gate that tells those
two cases apart."

This script runs four small experiments. Each one is a Monte Carlo
simulation that compares EVALSIG to the simpler test that other tools ship.

  E1 - Power. When there is a real but small effect, the paired test
       should find it much more often than the unpaired t-test on the
       same data.

  E2 - Type-I error under clustering. When items are grouped (passages,
       templates), the naive item-level test rejects the null way too
       often. The cluster bootstrap should keep the false-positive rate
       near 5%.

  E3 - MDE calibration. When the real effect equals the computed MDE,
       the test should fire ~80% of the time (matching the target power).

  E4 - CLI release gate. Run the shipped CLI on three realistic JSON
       inputs and check that the verdicts come out right:
         - infra-noise run -> REJECT
         - real improvement -> ALLOW
         - tiny sample      -> INCONCLUSIVE

Run with:   python research/validate.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

from evalsig import RunFrame, ItemResult
from evalsig.compare.gate import GateVerdict
from evalsig.inference.paired import (
    paired_permutation_test,
    paired_bootstrap_ci,
)
from evalsig.inference.unpaired import unpaired_t_test
from evalsig.inference.cluster_bootstrap import cluster_bootstrap_ci
from evalsig.inference.mde import mde, estimate_icc
from evalsig.io.json_runframe import write_runframe_json


# Small helpers used by the experiments below.

class Pass:
    OK = "\033[92m[OK]\033[0m"
    FAIL = "\033[91m[FAIL]\033[0m"


def banner(title: str) -> None:
    # Plain ASCII rule, easy on the eyes and on diff tools.
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def report(claim: str, ok: bool, detail: str) -> bool:
    mark = Pass.OK if ok else Pass.FAIL
    print(f"  {mark} {claim}  --  {detail}")
    return ok


def make_run(model_id: str, scores: np.ndarray,
             clusters: np.ndarray | None = None,
             task: str = "synthetic", metric: str = "accuracy") -> RunFrame:
    # Wraps a numpy score array as a RunFrame the rest of the package can
    # consume.
    items = []
    for i, s in enumerate(scores):
        c = None if clusters is None else str(clusters[i])
        items.append(ItemResult(item_id=f"item_{i:05d}", score=float(s),
                                cluster_id=c))
    return RunFrame(run_id=f"{model_id}::{task}", model_id=model_id,
                    task_id=task, metric_name=metric, items=items)


# E1: paired test should beat unpaired test when items are paired.

def experiment_1_power(n_items: int = 500, true_lift: float = 0.015,
                       n_sims: int = 400, alpha: float = 0.05,
                       seed: int = 0) -> dict:
    """Both runs see the same items and the same per-item luck draw `c`.
    That mimics the real world: an easy item is easy for both models, a
    hard item is hard for both. The candidate just gets a small +1.5pp
    boost on top.

    Because the two runs are correlated, paired inference should detect
    the lift far more often than the unpaired t-test that ignores the
    pairing.
    """
    rng = np.random.default_rng(seed)
    paired_sig = 0
    unpaired_sig = 0
    paired_deltas = []

    for _ in range(n_sims):
        theta = rng.beta(4, 2, size=n_items)
        # Shared luck per item: both runs see the same random draw.
        c = rng.random(n_items)
        y_a = (c < theta).astype(np.float64)
        y_b = (c < np.clip(theta + true_lift, 0.0, 1.0)).astype(np.float64)

        res_paired = paired_permutation_test(
            y_a, y_b, alternative="greater", n_resamples=2000,
            rng=rng.integers(0, 2**31 - 1),
        )
        res_unpaired = unpaired_t_test(
            y_a, y_b, alternative="greater",
        )
        paired_sig += int(res_paired.p_value < alpha)
        unpaired_sig += int(res_unpaired.p_value < alpha)
        paired_deltas.append(res_paired.delta)

    return {
        "n_items": n_items,
        "true_lift": true_lift,
        "n_sims": n_sims,
        "paired_power": paired_sig / n_sims,
        "unpaired_power": unpaired_sig / n_sims,
        "mean_delta": float(np.mean(paired_deltas)),
    }


# E2: when items are grouped, the cluster bootstrap should keep false
# positives at the 5% target.

def experiment_2_clustered_typeI(n_clusters: int = 50, cluster_size: int = 10,
                                 sigma_w: float = 0.08, sigma_e: float = 0.05,
                                 n_sims: int = 600, alpha: float = 0.05,
                                 seed: int = 1) -> dict:
    """Under the null (no real effect), each item's paired difference is
        d_i = w_{cluster(i)} + e_i
    `w_k` is a shared "passage-level" shift that pushes every item in the
    same cluster the same way. `e_i` is small per-item noise. The mean of
    d is zero in expectation, but any single eval run sees one realization
    of `w`, which biases item-level tests toward rejecting the null.

    The naive bootstrap treats items as independent and overcounts the
    sample size, so it rejects too often. The cluster bootstrap resamples
    whole clusters and gets the right answer.
    """
    rng = np.random.default_rng(seed)
    n_items = n_clusters * cluster_size
    cluster_id = np.repeat(np.arange(n_clusters), cluster_size)

    naive_sig = 0
    clustered_sig = 0
    iccs = []

    for _ in range(n_sims):
        w = rng.normal(0, sigma_w, size=n_clusters)
        eps = rng.normal(0, sigma_e, size=n_items)
        d = w[cluster_id] + eps
        # Build a fake (a, b) pair that gives the desired diff `d`.
        y_a = rng.normal(0.65, 0.1, size=n_items)
        y_b = y_a + d

        res_naive = paired_bootstrap_ci(
            y_a, y_b, alternative="two-sided", n_resamples=1500,
            rng=rng.integers(0, 2**31 - 1),
        )
        res_clustered = cluster_bootstrap_ci(
            y_a, y_b, cluster_id, alternative="two-sided", n_resamples=1500,
            rng=rng.integers(0, 2**31 - 1),
        )
        naive_sig += int(res_naive.p_value < alpha)
        clustered_sig += int(res_clustered.p_value < alpha)
        iccs.append(estimate_icc(d, cluster_id))

    return {
        "n_clusters": n_clusters, "cluster_size": cluster_size,
        "n_sims": n_sims, "alpha": alpha,
        "naive_typeI": naive_sig / n_sims,
        "clustered_typeI": clustered_sig / n_sims,
        "mean_icc": float(np.mean(iccs)),
    }


# E3: the MDE formula should match what we see in simulation.

def experiment_3_mde_calibration(n_items: int = 1000, sd_diff: float = 0.4,
                                 n_sims: int = 500, alpha: float = 0.05,
                                 power: float = 0.80, seed: int = 2) -> dict:
    """Compute the MDE for a given (n, sd, alpha, power). Then run the
    test many times with the true effect set equal to that MDE. The
    fraction of runs that come back significant should match `power`.
    """
    target_mde = mde(sd_diff=sd_diff, n_pairs=n_items, alpha=alpha,
                     power=power, one_sided=True).mde

    rng = np.random.default_rng(seed)
    rejections = 0
    for _ in range(n_sims):
        d = rng.normal(target_mde, sd_diff, size=n_items)
        # Any baseline works; only the paired difference matters.
        y_a = rng.normal(0.65, 0.1, size=n_items)
        y_b = y_a + d
        res = paired_permutation_test(
            y_a, y_b, alternative="greater", n_resamples=1500,
            rng=rng.integers(0, 2**31 - 1),
        )
        rejections += int(res.p_value < alpha)
    return {
        "n_items": n_items, "sd_diff": sd_diff, "target_power": power,
        "computed_mde": target_mde,
        "empirical_power": rejections / n_sims,
    }


# E4: CLI gate on three realistic JSON inputs.

def make_infra_noise_pair(n_items: int = 6000, base_acc: float = 0.65,
                          stochastic_frac: float = 0.20,
                          seed: int = 3) -> tuple[RunFrame, RunFrame]:
    """Two runs of the SAME model on different infra. Most items are
    answered the same way both times. A small share of items are
    borderline, so each run independently flips a coin on them. The
    aggregate accuracies differ by a few pp, but only from those coin
    flips. The paired test should not be fooled.
    """
    rng = np.random.default_rng(seed)
    theta = rng.beta(5, 5 * (1 - base_acc) / base_acc, size=n_items)
    is_stoch = rng.random(n_items) < stochastic_frac
    c = rng.random(n_items)
    y_a = (c < theta).astype(np.float64)
    y_b = y_a.copy()
    n_s = int(is_stoch.sum())
    y_a[is_stoch] = (rng.random(n_s) < 0.5).astype(np.float64)
    y_b[is_stoch] = (rng.random(n_s) < 0.5).astype(np.float64)
    return (
        make_run("claude-x-config-A", y_a, task="terminal-bench"),
        make_run("claude-x-config-B", y_b, task="terminal-bench"),
    )


def make_real_improvement_pair(n_items: int = 2000, base_acc: float = 0.65,
                               lift: float = 0.025, seed: int = 4
                               ) -> tuple[RunFrame, RunFrame]:
    """Baseline vs candidate with a real +2.5pp lift on every item.
    Shared per-item luck keeps the paired variance small, so the lift is
    easy to detect at this sample size.
    """
    rng = np.random.default_rng(seed)
    theta = rng.beta(5, 5 * (1 - base_acc) / base_acc, size=n_items)
    c = rng.random(n_items)
    y_a = (c < theta).astype(np.float64)
    y_b = (c < np.clip(theta + lift, 0.0, 1.0)).astype(np.float64)
    return (
        make_run("claude-x", y_a, task="mmlu-pro"),
        make_run("claude-x-rlhf", y_b, task="mmlu-pro"),
    )


def make_underpowered_pair(n_items: int = 80, base_acc: float = 0.65,
                           lift: float = 0.025, seed: int = 5
                           ) -> tuple[RunFrame, RunFrame]:
    """Same +2.5pp lift but only 80 items, and each run draws its own
    luck. The lift is real but the run is too small to confirm it.
    """
    rng = np.random.default_rng(seed)
    theta = rng.beta(5, 5 * (1 - base_acc) / base_acc, size=n_items)
    c_a = rng.random(n_items)
    c_b = rng.random(n_items)
    y_a = (c_a < theta).astype(np.float64)
    y_b = (c_b < np.clip(theta + lift, 0.0, 1.0)).astype(np.float64)
    return (
        make_run("claude-x", y_a, task="gpqa"),
        make_run("claude-x-rlhf", y_b, task="gpqa"),
    )


def experiment_4_cli_gate(out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    scenarios = {
        "infra_noise": make_infra_noise_pair(),
        "real_improvement": make_real_improvement_pair(),
        "underpowered": make_underpowered_pair(),
    }
    results: dict = {}
    for name, (a, b) in scenarios.items():
        a_path = out_dir / f"{name}_baseline.json"
        b_path = out_dir / f"{name}_candidate.json"
        report_path = out_dir / f"{name}_report.json"
        write_runframe_json(a, a_path)
        write_runframe_json(b, b_path)
        proc = subprocess.run(
            [sys.executable, "-m", "evalsig.cli.main", "gate",
             "--baseline", str(a_path),
             "--candidate", str(b_path),
             "--metric", "accuracy",
             "--min-delta", "0.015",
             "--alpha", "0.05",
             "--power", "0.80",
             "--method", "paired_permutation",
             "--resamples", "5000",
             "--seed", "0",
             "--json", str(report_path)],
            capture_output=True, text=True,
        )
        rep = json.loads(report_path.read_text())
        results[name] = {
            "exit_code": proc.returncode,
            "verdict": rep["verdict"],
            "delta": rep["comparison"]["delta"],
            "p_value": rep["comparison"]["p_value"],
            "mde": rep["comparison"]["mde"],
            "ci": rep["comparison"]["ci"],
            "n_pairs": rep["comparison"]["n_pairs"],
            "stdout_excerpt": proc.stdout.strip().splitlines()[-1] if proc.stdout else "",
        }
    return results


# Main: run all four experiments and print a summary.

def main() -> int:
    print()
    print("=" * 72)
    print("  EVALSIG end-to-end research validation")
    print()
    print("  Checks whether the library can tell real eval signal apart")
    print("  from infrastructure noise, the way the design doc promises.")
    print("=" * 72)

    all_ok = True
    summary: dict = {}

    banner("E1: paired inference beats unpaired Welch on the same data")
    t0 = time.time()
    r1 = experiment_1_power()
    summary["E1_power"] = r1
    print(f"  setup: {r1['n_sims']} simulations, n_items={r1['n_items']}, "
          f"true lift = {r1['true_lift']*100:.2f}pp (in the 1-3pp range "
          "the doc cites)")
    print(f"  mean observed delta across sims: {r1['mean_delta']*100:+.2f}pp")
    print(f"  unpaired Welch t-test power:     {r1['unpaired_power']*100:5.1f}%   "
          "(what most commercial tools ship)")
    print(f"  paired permutation power:        {r1['paired_power']*100:5.1f}%   "
          "(what EVALSIG ships)")
    ratio = r1['paired_power'] / max(r1['unpaired_power'], 1e-6)
    print(f"  ratio paired/unpaired = {ratio:.2f}x")
    ok = report(
        "paired test wins by at least 1.5x on the same data",
        r1["paired_power"] >= 1.5 * r1["unpaired_power"],
        f"{r1['paired_power']*100:.1f}% vs {r1['unpaired_power']*100:.1f}%",
    )
    all_ok &= ok
    print(f"  ({time.time()-t0:.1f}s)")

    banner("E2: cluster bootstrap keeps false positives near 5% on grouped data")
    t0 = time.time()
    r2 = experiment_2_clustered_typeI()
    summary["E2_clustered_typeI"] = r2
    print(f"  setup: {r2['n_sims']} simulations under the null, "
          f"{r2['n_clusters']} clusters x {r2['cluster_size']} items, "
          f"mean ICC={r2['mean_icc']:.3f}")
    print(f"  target false-positive rate:           5.0%")
    print(f"  naive paired_bootstrap rate:         {r2['naive_typeI']*100:5.1f}%   "
          "(rejects too often, ships false wins)")
    print(f"  cluster_bootstrap rate:              {r2['clustered_typeI']*100:5.1f}%   "
          "(near 5%, correct)")
    ok1 = report(
        "naive item-level test is way off when items are grouped",
        r2["naive_typeI"] > 0.10,
        f"naive false-positive rate = {r2['naive_typeI']*100:.1f}% (way above 5%)",
    )
    ok2 = report(
        "cluster_bootstrap keeps false positives near 5%",
        abs(r2["clustered_typeI"] - 0.05) <= 0.025,
        f"clustered rate = {r2['clustered_typeI']*100:.1f}% (within +/-2.5pp of 5%)",
    )
    all_ok &= ok1 and ok2
    print(f"  ({time.time()-t0:.1f}s)")

    banner("E3: MDE formula matches the empirical detection rate")
    t0 = time.time()
    r3 = experiment_3_mde_calibration()
    summary["E3_mde"] = r3
    print(f"  setup: sd_diff={r3['sd_diff']}, n={r3['n_items']}, target power "
          f"{r3['target_power']*100:.0f}%")
    print(f"  computed MDE:        {r3['computed_mde']:.4f}")
    print(f"  empirical power at delta = MDE:  "
          f"{r3['empirical_power']*100:.1f}%  (target: "
          f"{r3['target_power']*100:.0f}%)")
    ok = report(
        "empirical power is within +/-5pp of the requested power",
        abs(r3["empirical_power"] - r3["target_power"]) <= 0.05,
        f"|empirical - target| = "
        f"{abs(r3['empirical_power']-r3['target_power'])*100:.1f}pp",
    )
    all_ok &= ok
    print(f"  ({time.time()-t0:.1f}s)")

    banner("E4: `evalsig gate` returns the right verdict end-to-end")
    t0 = time.time()
    out_dir = Path("/tmp/evalsig_validate")
    r4 = experiment_4_cli_gate(out_dir)
    summary["E4_cli_gate"] = r4
    print(f"  (RunFrame JSON inputs written to {out_dir}/*.json)")
    print()
    print(f"  {'scenario':<22}{'delta':>10}{'p-value':>10}{'MDE':>10}  "
          f"{'verdict':<14}exit")
    # Plain ASCII rule for the table header.
    print(f"  {'-'*22}{'-'*10}{'-'*10}{'-'*10}  {'-'*14}{'-'*4}")
    for name, r in r4.items():
        print(f"  {name:<22}{r['delta']*100:+8.2f}pp{r['p_value']:>10.4f}"
              f"{r['mde']*100:>8.2f}pp  {r['verdict']:<14}{r['exit_code']:>4}")

    print()
    expected = {
        "infra_noise":      GateVerdict.REJECT.value,
        "real_improvement": GateVerdict.ALLOW.value,
        "underpowered":     GateVerdict.INCONCLUSIVE.value,
    }
    e4_ok = True
    for scenario, expected_verdict in expected.items():
        actual = r4[scenario]["verdict"]
        ok = report(
            f"{scenario}: {expected_verdict}",
            actual == expected_verdict,
            f"got {actual} (exit {r4[scenario]['exit_code']})",
        )
        e4_ok &= ok
    all_ok &= e4_ok
    print(f"  ({time.time()-t0:.1f}s)")

    print()
    print("=" * 72)
    if all_ok:
        print(f"  {Pass.OK} ALL CLAIMS HOLD. EVALSIG separates the cases the doc promises.")
    else:
        print(f"  {Pass.FAIL} at least one claim failed; see above.")
    print("=" * 72)

    Path("/tmp/evalsig_validate/_summary.json").write_text(
        json.dumps(summary, indent=2, default=str)
    )
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
