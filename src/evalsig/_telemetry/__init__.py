"""Opt-in usage telemetry.

Defaults to OFF. The user must set EVALSIG_TELEMETRY=1 to enable. Even
when enabled, only event names and aggregate counts are sent; no run
content, no item-level data.
"""
from evalsig._telemetry.client import emit, enabled

__all__ = ["emit", "enabled"]
