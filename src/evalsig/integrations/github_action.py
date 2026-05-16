"""Entry point used by the published GitHub Action.

The action passes the inputs as environment variables prefixed with
INPUT_*, the same convention `actions/core` uses. This script reads
them, runs the gate, writes a Markdown summary to $GITHUB_STEP_SUMMARY
when present, and exits with the gate's exit code so the workflow job
fails or passes accordingly.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from evalsig.compare.gate import gate
from evalsig.compare.report import to_json, to_markdown
from evalsig.io.json_runframe import read_runframe_json
from evalsig.io.lm_eval import read_lm_eval_json
from evalsig.io.inspect_log import read_inspect_log
from evalsig.io.helm import read_helm_scenario
from evalsig.io.parquet import read_runframe_parquet


_READERS = {
    "runframe": read_runframe_json,
    "lm_eval": read_lm_eval_json,
    "inspect": read_inspect_log,
    "helm": read_helm_scenario,
    "parquet": read_runframe_parquet,
}


def _env(name: str, default: str | None = None, *,
         required: bool = False) -> str | None:
    """Read an INPUT_ env var, with optional default and 'required' flag."""
    key = f"INPUT_{name.upper()}"
    v = os.environ.get(key, default)
    if required and not v:
        raise SystemExit(f"missing required input '{name}' (env {key})")
    return v


def _read(path: str, fmt: str):
    if fmt not in _READERS:
        raise SystemExit(f"unknown format '{fmt}'")
    return _READERS[fmt](path)


def main() -> int:
    baseline_path = _env("baseline", required=True)
    candidate_path = _env("candidate", required=True)
    fmt = _env("format", "runframe") or "runframe"
    metric = _env("metric", "accuracy") or "accuracy"
    cluster = _env("cluster", "") or None
    min_delta = float(_env("min_delta", "0.005") or "0.005")
    alpha = float(_env("alpha", "0.05") or "0.05")
    power = float(_env("power", "0.80") or "0.80")
    method = _env("method", "auto") or "auto"
    one_sided = (_env("one_sided", "true") or "true").lower() in ("1", "true", "yes")

    a = _read(baseline_path, fmt)
    b = _read(candidate_path, fmt)
    report = gate(
        a, b, min_delta=min_delta, alpha=alpha, power=power,
        method=method, cluster=cluster, one_sided=one_sided,
    )

    # Write a Markdown summary block so the verdict shows up in the
    # GitHub Actions UI.
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        Path(summary_path).write_text(to_markdown(report), encoding="utf-8")

    # Emit outputs so downstream steps can read them via ${{ steps.evalsig.outputs.* }}
    output_path = os.environ.get("GITHUB_OUTPUT")
    if output_path:
        with open(output_path, "a", encoding="utf-8") as fh:
            fh.write(f"verdict={report.verdict.value}\n")
            fh.write(f"delta={report.comparison.delta}\n")
            fh.write(f"p_value={report.comparison.p_value}\n")
            fh.write(f"mde={report.comparison.mde}\n")

    # Always echo a JSON blob to stdout so the action's logs preserve it.
    print(to_json(report))
    return report.exit_code


if __name__ == "__main__":
    sys.exit(main())
