"""Render a ComparisonResult or GateReport in three formats.

Each renderer is a pure function: input is the result object, output is
a string. The CLI picks the renderer based on a flag; the SaaS uses the
Markdown renderer for compliance exports and the JSON renderer for the
audit trail.
"""
from __future__ import annotations

import json
from typing import Any, Mapping

from evalsig.compare.gate import GateReport
from evalsig.types import ComparisonResult


def _fmt_ci(ci: tuple[float, float]) -> str:
    def f(x: float) -> str:
        if x == float("inf"):
            return "+inf"
        if x == float("-inf"):
            return "-inf"
        return f"{x:+.4f}"
    return f"[{f(ci[0])}, {f(ci[1])}]"


# JSON ------------------------------------------------------------------

def to_json(result: ComparisonResult | GateReport, *, indent: int = 2) -> str:
    """Serialise a result to a JSON string."""
    if isinstance(result, GateReport):
        payload: Mapping[str, Any] = result.to_dict()
    else:
        payload = result.to_dict()
    return json.dumps(payload, indent=indent, default=str)


# Markdown --------------------------------------------------------------

def to_markdown(result: ComparisonResult | GateReport) -> str:
    """Render as a small Markdown block suitable for a PR comment or a
    compliance export."""
    if isinstance(result, GateReport):
        return _gate_markdown(result)
    return _comparison_markdown(result)


def _comparison_markdown(c: ComparisonResult) -> str:
    lines = [
        "## EVALSIG comparison",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| delta | `{c.delta:+.4f}` |",
        f"| CI ({c.ci_level:.0%}) | `{_fmt_ci(c.ci)}` |",
        f"| p-value | `{c.p_value:.4f}` |",
        f"| method | `{c.method}` |",
        f"| n_pairs | {c.n_pairs} |",
    ]
    if c.n_clusters:
        lines.append(f"| n_clusters | {c.n_clusters} |")
    lines.append(f"| MDE | `{c.mde:.4f}` |")
    lines.append(f"| significant | **{c.significant}** |")
    if c.notes:
        lines.append("")
        lines.append("**Notes:**")
        for n in c.notes:
            lines.append(f"- {n}")
    return "\n".join(lines)


def _gate_markdown(g: GateReport) -> str:
    c = g.comparison
    emoji = {"ALLOW": ":white_check_mark:", "REJECT": ":no_entry:",
             "INCONCLUSIVE": ":warning:"}.get(g.verdict.value, "")
    lines = [
        f"## EVALSIG release gate {emoji} {g.verdict.value}",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| verdict | **{g.verdict.value}** |",
        f"| min_delta policy | `{g.min_delta:.4f}` |",
        f"| observed delta | `{c.delta:+.4f}` |",
        f"| CI ({c.ci_level:.0%}) | `{_fmt_ci(c.ci)}` |",
        f"| p-value | `{c.p_value:.4f}` |",
        f"| detectable @ {g.power:.0%} power | `{c.mde:.4f}` |",
        f"| method | `{c.method}` |",
        f"| n_pairs | {c.n_pairs} |",
    ]
    if g.suggestion:
        lines += ["", "**Suggestion:** " + g.suggestion]
    if c.notes:
        lines.append("")
        lines.append("**Notes:**")
        for n in c.notes:
            lines.append(f"- {n}")
    return "\n".join(lines)


# Terminal --------------------------------------------------------------

def to_tty(result: ComparisonResult | GateReport, *, use_color: bool = True
           ) -> str:
    """Render for the terminal. ANSI colors highlight the verdict."""
    def color(s: str, code: str) -> str:
        return f"\033[{code}m{s}\033[0m" if use_color else s

    if isinstance(result, GateReport):
        c = result.comparison
        verdict_codes = {"ALLOW": "92", "REJECT": "91", "INCONCLUSIVE": "93"}
        v_str = color(result.verdict.value, verdict_codes.get(result.verdict.value, "0"))
        lines = [
            "EVALSIG release gate",
            "====================",
            f"delta:         {c.delta:+.4f}  ({c.method})",
            f"CI ({c.ci_level:.0%}):      {_fmt_ci(c.ci)}",
            f"p-value:       {c.p_value:.4f}",
            f"required MDE:  {result.min_delta:.4f}",
            f"detectable:    {c.mde:.4f} at {result.power:.0%} power",
            "",
            f"VERDICT: {v_str}",
        ]
        if result.suggestion:
            lines.append(f"Suggestion: {result.suggestion}")
        return "\n".join(lines)

    # ComparisonResult only
    lines = [
        "EVALSIG comparison",
        "==================",
        f"delta:       {result.delta:+.4f}",
        f"CI ({result.ci_level:.0%}):    {_fmt_ci(result.ci)}",
        f"p-value:     {result.p_value:.4f}",
        f"method:      {result.method}",
        f"n_pairs:     {result.n_pairs}",
        f"MDE:         {result.mde:.4f}",
        f"significant: {result.significant}",
    ]
    return "\n".join(lines)
