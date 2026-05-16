"""evalsig command-line tool.

Subcommands:
  compare   print delta, CI, p-value, MDE for two runs
  gate      same as compare, but with a min-delta policy and an exit code
  mde       compute MDE or required N, no run files needed
  watch     stream paired diffs through a sequential / always-valid test
  doctor    validate a RunFrame JSON file against the schema
  history   list / query the local run store
  version   print the package version

Exit codes (BSD sysexits style):
  0   ALLOW or successful command
  1   REJECT
  2   INCONCLUSIVE (run too small to detect the requested effect)
 64   bad command-line arguments
 65   bad input data
 70   internal error
"""
from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path
from typing import Optional

from evalsig._version import __version__
from evalsig.compare.compare import compare
from evalsig.compare.gate import gate
from evalsig.compare.report import to_json, to_markdown, to_tty
from evalsig.io.json_runframe import (
    read_runframe_json,
    write_runframe_json,
)
from evalsig.io.lm_eval import read_lm_eval_json
from evalsig.io.inspect_log import read_inspect_log
from evalsig.io.helm import read_helm_scenario
from evalsig.io.parquet import read_runframe_parquet
from evalsig.types import RunFrame
from evalsig.inference.mde import required_n
from evalsig.inference.sequential import sequential_gate


def _read(path: str, format: str, model_id: Optional[str] = None,
          task_id: Optional[str] = None, metric: str = "accuracy",
          cluster_key: Optional[str] = None) -> RunFrame:
    # Pick a reader from --format, or guess from the file extension.
    p = Path(path)
    if format == "auto":
        if p.suffix == ".jsonl":
            format = "lm_eval"
        elif p.suffix == ".eval" or "inspect" in p.name.lower():
            format = "inspect"
        elif p.suffix == ".parquet":
            format = "parquet"
        elif "helm" in p.name.lower() or p.name == "scenario_state.json":
            format = "helm"
        else:
            format = "runframe"
    if format == "runframe":
        return read_runframe_json(p)
    if format == "lm_eval":
        return read_lm_eval_json(
            p, model_id=model_id or p.stem, task_id=task_id or "task",
            metric_name=metric, cluster_key=cluster_key,
        )
    if format == "inspect":
        return read_inspect_log(p, metric_name=metric, cluster_key=cluster_key)
    if format == "helm":
        return read_helm_scenario(
            p, model_id=model_id, task_id=task_id,
            metric_name=metric, cluster_key=cluster_key,
        )
    if format == "parquet":
        return read_runframe_parquet(p)
    raise ValueError(f"unknown format: {format}")


def _emit(result, args, default_renderer):
    """Pick a renderer (json/markdown/tty) and print/write the result."""
    fmt = args.output if getattr(args, "output", None) else "tty"
    if fmt == "json":
        text = to_json(result)
    elif fmt == "markdown":
        text = to_markdown(result)
    else:
        text = default_renderer(result)
    print(text)
    if getattr(args, "json", None):
        Path(args.json).write_text(to_json(result))


def cmd_compare(args: argparse.Namespace) -> int:
    a = _read(args.baseline, args.format, args.baseline_model, args.task,
              args.metric, args.cluster)
    b = _read(args.candidate, args.format, args.candidate_model, args.task,
              args.metric, args.cluster)
    res = compare(
        a, b, method=args.method, cluster=args.cluster, alpha=args.alpha,
        one_sided=args.one_sided, target_power=args.power,
        n_resamples=args.resamples, rng=args.seed,
    )
    _emit(res, args, default_renderer=lambda r: to_tty(r, use_color=sys.stdout.isatty()))
    return 0


def cmd_gate(args: argparse.Namespace) -> int:
    a = _read(args.baseline, args.format, args.baseline_model, args.task,
              args.metric, args.cluster)
    b = _read(args.candidate, args.format, args.candidate_model, args.task,
              args.metric, args.cluster)
    report = gate(
        a, b, min_delta=args.min_delta, alpha=args.alpha, power=args.power,
        method=args.method, cluster=args.cluster,
        one_sided=not args.two_sided,
        n_resamples=args.resamples, rng=args.seed,
    )
    _emit(report, args, default_renderer=lambda r: to_tty(r, use_color=sys.stdout.isatty()))
    return report.exit_code


def cmd_mde(args: argparse.Namespace) -> int:
    from evalsig.inference.mde import mde
    if args.target_delta is not None:
        n = required_n(
            args.target_delta, args.sd_diff, alpha=args.alpha,
            power=args.power, one_sided=args.one_sided,
            icc=args.icc, mean_cluster_size=args.cluster_size,
        )
        print(f"required N = {n:,} paired items to detect delta={args.target_delta:.4f}")
        print(f"  at alpha={args.alpha}, power={args.power}, "
              f"sd_diff={args.sd_diff}, icc={args.icc}, "
              f"mean_cluster_size={args.cluster_size}")
        return 0

    res = mde(
        args.sd_diff, args.n_pairs, alpha=args.alpha, power=args.power,
        one_sided=args.one_sided,
        n_clusters=args.n_clusters, icc=args.icc,
    )
    print(f"MDE = {res.mde:.4f}")
    print(f"  alpha={res.alpha}, power={res.power}, "
          f"sd_diff={res.sd_diff}, n={res.n_pairs}")
    if res.deff is not None:
        print(f"  design effect = {res.deff:.3f} "
              f"(icc={res.icc}, clusters={res.n_clusters})")
    return 0


def cmd_watch(args: argparse.Namespace) -> int:
    """Run an always-valid sequential test on two runs streamed by item."""
    a = _read(args.baseline, args.format, args.baseline_model, args.task,
              args.metric, args.cluster)
    b = _read(args.candidate, args.format, args.candidate_model, args.task,
              args.metric, args.cluster)
    # Align item ids manually so order is reproducible.
    a_map = {it.item_id: float(it.score) for it in a.items if it.epoch == 0}
    b_map = {it.item_id: float(it.score) for it in b.items if it.epoch == 0}
    common = sorted(set(a_map) & set(b_map))
    diffs = [b_map[k] - a_map[k] for k in common]
    out = sequential_gate(
        diffs,
        alpha=args.alpha,
        alternative=args.alternative,
        rho=args.rho,
        min_n=args.min_n,
    )
    print("EVALSIG sequential watch")
    print("========================")
    print(f"n_pairs:     {out.n_pairs}")
    print(f"delta:       {out.delta:+.4f}")
    print(f"CI ({1-args.alpha:.0%}):    [{out.ci[0]:+.4f}, {out.ci[1]:+.4f}]")
    print(f"half-width:  {out.half_width:.4f}")
    print(f"stopped:     {out.stopped}")
    return 0 if out.stopped else 2


def cmd_doctor(args: argparse.Namespace) -> int:
    """Validate one or more RunFrame JSON files against the schema."""
    from evalsig.io.json_runframe import _validate, SchemaError
    failures = 0
    for path in args.files:
        p = Path(path)
        try:
            obj = json.loads(p.read_text())
            _validate(obj)
            run = read_runframe_json(p)
            print(f"  OK   {path}  (n={len(run.items)}, "
                  f"model={run.model_id}, task={run.task_id})")
        except (SchemaError, FileNotFoundError, json.JSONDecodeError) as e:
            failures += 1
            print(f"  FAIL {path}  -- {e}")
    if failures:
        print(f"\n{failures} file(s) failed validation.")
        return 65
    print(f"\nAll {len(args.files)} file(s) validate cleanly.")
    return 0


def cmd_history(args: argparse.Namespace) -> int:
    """List runs in the local store, with optional filters."""
    from evalsig.store.reader import query_runs

    runs = query_runs(
        args.root,
        project_id=args.project,
        model_id=args.model_id,
        task_id=args.task_id,
        metric_name=args.metric_name,
        since=args.since,
        until=args.until,
    )
    if not runs:
        print(f"No runs found in {args.root} (project={args.project}).")
        return 0
    # Header
    print(f"{'run_id':<24}{'model':<22}{'task':<22}{'metric':<12}"
          f"{'delta':>10}{'verdict':>14}  ts")
    print("-" * 110)
    for h in runs:
        r = h.record
        delta_s = f"{r.delta:+.4f}" if r.delta is not None else "-"
        verdict_s = r.verdict if r.verdict else "-"
        print(f"{r.run_id:<24}{r.model_id:<22}{r.task_id:<22}"
              f"{r.metric_name:<12}{delta_s:>10}{verdict_s:>14}  {r.ts}")
    return 0


def cmd_version(args: argparse.Namespace) -> int:
    print(f"evalsig {__version__}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="evalsig",
        description="Statistical release gating for LLM evaluations.",
    )
    p.add_argument("--version", action="version", version=f"evalsig {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_common_compare(sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--baseline", required=True, help="path to baseline run")
        sp.add_argument("--candidate", required=True, help="path to candidate run")
        sp.add_argument("--format", choices=["auto", "runframe", "lm_eval",
                                              "inspect", "helm", "parquet"],
                        default="auto")
        sp.add_argument("--metric", default="accuracy")
        sp.add_argument("--cluster", default=None,
                        help="cluster key (column/metadata field)")
        sp.add_argument("--task", default=None)
        sp.add_argument("--baseline-model", default=None)
        sp.add_argument("--candidate-model", default=None)
        sp.add_argument("--alpha", type=float, default=0.05)
        sp.add_argument("--power", type=float, default=0.80)
        sp.add_argument("--method", default="auto",
                        choices=["auto", "paired_t", "paired_permutation",
                                 "paired_bootstrap", "mcnemar",
                                 "cluster_bootstrap"])
        sp.add_argument("--resamples", type=int, default=10_000)
        sp.add_argument("--seed", type=int, default=0)
        sp.add_argument("--json", default=None,
                        help="also write a JSON report to this path")
        sp.add_argument("--output", choices=["tty", "json", "markdown"],
                        default="tty",
                        help="renderer for the stdout report (default: tty)")

    sp = sub.add_parser("compare", help="compare two runs and print statistics")
    add_common_compare(sp)
    sp.add_argument("--one-sided", action="store_true",
                    help="test only candidate > baseline")
    sp.set_defaults(func=cmd_compare)

    sp = sub.add_parser("gate",
                        help="release-gate two runs; non-zero exit blocks the release")
    add_common_compare(sp)
    sp.add_argument("--min-delta", type=float, required=True,
                    help="minimum effect size policy must clear to ship")
    sp.add_argument("--two-sided", action="store_true",
                    help="default is one-sided greater; pass this to flip")
    sp.set_defaults(func=cmd_gate)

    sp = sub.add_parser("mde",
                        help="compute minimum detectable effect or required N")
    sp.add_argument("--sd-diff", type=float, required=True,
                    help="sample SD of the per-item paired difference")
    sp.add_argument("--n-pairs", type=int, default=1000)
    sp.add_argument("--target-delta", type=float, default=None,
                    help="if given, compute required N instead of MDE")
    sp.add_argument("--alpha", type=float, default=0.05)
    sp.add_argument("--power", type=float, default=0.80)
    sp.add_argument("--one-sided", action="store_true")
    sp.add_argument("--n-clusters", type=int, default=None)
    sp.add_argument("--icc", type=float, default=0.0)
    sp.add_argument("--cluster-size", type=float, default=1.0)
    sp.set_defaults(func=cmd_mde)

    sp = sub.add_parser("watch",
                        help="always-valid sequential test on two runs")
    sp.add_argument("--baseline", required=True)
    sp.add_argument("--candidate", required=True)
    sp.add_argument("--format", choices=["auto", "runframe", "lm_eval",
                                          "inspect", "helm", "parquet"],
                    default="auto")
    sp.add_argument("--metric", default="accuracy")
    sp.add_argument("--cluster", default=None)
    sp.add_argument("--task", default=None)
    sp.add_argument("--baseline-model", default=None)
    sp.add_argument("--candidate-model", default=None)
    sp.add_argument("--alpha", type=float, default=0.05)
    sp.add_argument("--alternative", choices=["greater", "less", "two-sided"],
                    default="greater")
    sp.add_argument("--rho", type=float, default=1.0)
    sp.add_argument("--min-n", type=int, default=30)
    sp.set_defaults(func=cmd_watch)

    sp = sub.add_parser("doctor",
                        help="validate one or more RunFrame JSON files")
    sp.add_argument("files", nargs="+", help="JSON file(s) to check")
    sp.set_defaults(func=cmd_doctor)

    sp = sub.add_parser("history",
                        help="list runs in the local store")
    sp.add_argument("--root", required=True, help="store root directory")
    sp.add_argument("--project", default="default")
    sp.add_argument("--model-id", default=None)
    sp.add_argument("--task-id", default=None)
    sp.add_argument("--metric-name", default=None)
    sp.add_argument("--since", default=None,
                    help="ISO-8601 lower bound on run timestamp")
    sp.add_argument("--until", default=None,
                    help="ISO-8601 upper bound on run timestamp")
    sp.set_defaults(func=cmd_history)

    sp = sub.add_parser("version", help="print the package version")
    sp.set_defaults(func=cmd_version)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ValueError, FileNotFoundError) as e:
        print(f"evalsig: data error: {e}", file=sys.stderr)
        return 65
    except SystemExit:
        raise
    except Exception:
        print("evalsig: internal error", file=sys.stderr)
        traceback.print_exc()
        return 70


if __name__ == "__main__":
    sys.exit(main())
