"""Publish a ComparisonResult or GateReport to Braintrust.

Braintrust ships its own SDK; we import it lazily and fall back to a
clear error if the user hasn't installed it. The function turns a
RunFrame pair into a Braintrust experiment record so customers can see
EVALSIG's verdict next to their existing dashboards.
"""
from __future__ import annotations

from typing import Any, Optional

from evalsig.compare.compare import compare
from evalsig.compare.gate import gate
from evalsig.exceptions import IntegrationError
from evalsig.types import RunFrame


def publish_comparison(
    a: RunFrame,
    b: RunFrame,
    *,
    project: str,
    experiment: str,
    api_key: Optional[str] = None,
    min_delta: Optional[float] = None,
    **gate_kwargs: Any,
) -> dict:
    """Compare two runs and publish the result as a Braintrust experiment.

    Returns the dict payload that was sent. Raises IntegrationError if
    the braintrust package is not installed or the upload fails.
    """
    try:
        import braintrust  # type: ignore
    except ImportError as e:
        raise IntegrationError(
            "the braintrust package is not installed; "
            "install with `pip install braintrust`"
        ) from e

    if min_delta is None:
        result: Any = compare(a, b)
        payload = result.to_dict()
        verdict = "ALLOW" if result.significant else "REJECT"
    else:
        report = gate(a, b, min_delta=min_delta, **gate_kwargs)
        payload = report.to_dict()
        verdict = report.verdict.value

    init = getattr(braintrust, "init", None)
    if init is None:
        raise IntegrationError(
            "the installed braintrust package is missing `init`; "
            "please upgrade"
        )

    with init(project=project, experiment=experiment, api_key=api_key) as exp:
        exp.log(
            input={"baseline": a.model_id, "candidate": b.model_id},
            output=verdict,
            metadata=payload,
        )
    return payload
