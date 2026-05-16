"""EVALSIG: statistical release gating for LLM evals.

Top-level imports give you the 80%-case API. Power users reach into the
submodules (``evalsig.inference``, ``evalsig.io``, ``evalsig.store``) for
the rest.
"""
from evalsig._version import __version__
from evalsig.types import (
    ItemResult,
    RunFrame,
    ComparisonResult,
    MDEResult,
)
from evalsig.exceptions import (
    EvalsigError,
    SchemaError,
    AlignmentError,
    InferenceError,
    GatePolicyError,
    StoreError,
    IntegrationError,
)
from evalsig.compare.compare import compare
from evalsig.compare.gate import gate, GateVerdict, GateReport
from evalsig.compare.report import to_json, to_markdown, to_tty
from evalsig.inference.mde import mde, required_n
from evalsig.inference.power import power_for_delta
from evalsig.inference.effect_size import (
    cohens_d,
    cohens_d_paired,
    cliffs_delta,
)
from evalsig.inference.sequential import (
    confidence_sequence,
    sequential_gate,
)
from evalsig.inference.multiplicity import (
    bonferroni,
    holm,
    benjamini_hochberg,
)

__all__ = [
    # version
    "__version__",
    # types
    "ItemResult",
    "RunFrame",
    "ComparisonResult",
    "MDEResult",
    # exceptions
    "EvalsigError",
    "SchemaError",
    "AlignmentError",
    "InferenceError",
    "GatePolicyError",
    "StoreError",
    "IntegrationError",
    # compare / gate
    "compare",
    "gate",
    "GateVerdict",
    "GateReport",
    "to_json",
    "to_markdown",
    "to_tty",
    # inference
    "mde",
    "required_n",
    "power_for_delta",
    "cohens_d",
    "cohens_d_paired",
    "cliffs_delta",
    "confidence_sequence",
    "sequential_gate",
    "bonferroni",
    "holm",
    "benjamini_hochberg",
]
