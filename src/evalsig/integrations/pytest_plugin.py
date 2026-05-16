"""Pytest plugin that exposes an `evalsig_gate` fixture.

Usage:

    # conftest.py
    pytest_plugins = ["evalsig.integrations.pytest_plugin"]

    # test_release.py
    def test_no_regression(evalsig_gate):
        a = evalsig_gate.load("baseline.eval", format="inspect")
        b = evalsig_gate.load("candidate.eval", format="inspect")
        evalsig_gate.assert_no_regression(a, b, metric="accuracy",
                                          min_delta=0.005)

The fixture is a thin adapter over the public `gate()` function so that
test failures show a useful message rather than a raw assertion.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from evalsig.compare.gate import gate
from evalsig.compare.report import to_markdown
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


class EvalsigGateFixture:
    """Methods callers reach for inside a pytest test body."""

    def load(self, path: str | Path, *, format: str = "runframe",
             **kwargs: Any):
        if format not in _READERS:
            raise ValueError(
                f"unknown format '{format}'; choose from {sorted(_READERS)}"
            )
        reader = _READERS[format]
        return reader(path, **kwargs)

    def assert_no_regression(self, baseline, candidate, *,
                              metric: str = "accuracy",
                              min_delta: float = 0.005,
                              alpha: float = 0.05,
                              power: float = 0.80,
                              cluster: str | None = None,
                              method: str = "auto") -> None:
        report = gate(
            baseline, candidate, min_delta=min_delta, alpha=alpha,
            power=power, method=method, cluster=cluster,
        )
        if report.verdict.value != "ALLOW":
            # Surface the full report when the assertion fails. Pytest
            # captures the message, so the developer sees the whole
            # picture without re-running.
            msg = to_markdown(report)
            raise AssertionError(
                f"EVALSIG release gate did not allow this candidate.\n\n{msg}"
            )


def pytest_configure(config) -> None:  # noqa: D401 - pytest hook signature
    """Register markers so users can decorate tests cleanly."""
    config.addinivalue_line(
        "markers",
        "evalsig: mark a test as a statistical release gate (uses evalsig_gate fixture).",
    )


# The fixture itself. Pytest discovers it by name.
try:
    import pytest  # noqa: F401  imported for fixture decorator
except ImportError:  # pragma: no cover - pytest is an optional dep
    pytest = None  # type: ignore

if pytest is not None:

    @pytest.fixture()
    def evalsig_gate() -> EvalsigGateFixture:
        """Fixture exposing the evalsig release-gate API to tests."""
        return EvalsigGateFixture()
