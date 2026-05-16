"""Typed errors raised by evalsig.

Every error users hit should be a subclass of EvalsigError so they can be
caught in one place and translated into a sensible CLI exit code or
HTTP response.
"""
from __future__ import annotations


class EvalsigError(Exception):
    """Root of the evalsig error hierarchy."""


class SchemaError(EvalsigError):
    """A RunFrame JSON failed validation against the published schema."""


class AlignmentError(EvalsigError):
    """Two runs cannot be aligned: too few overlapping items, mismatched
    cluster ids, or other structural problems."""


class InferenceError(EvalsigError):
    """A statistical primitive was called with arguments it cannot honor.
    Usually a shape mismatch or a sample size that is too small."""


class GatePolicyError(EvalsigError):
    """The gate was called with an inconsistent policy (for example a
    negative min_delta or alpha outside (0, 1))."""


class StoreError(EvalsigError):
    """The append-only store rejected a write or could not satisfy a
    read query."""


class IntegrationError(EvalsigError):
    """An optional integration (Braintrust, pytest, GitHub Action) failed
    or required dependencies are missing."""
