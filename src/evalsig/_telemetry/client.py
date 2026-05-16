"""Tiny opt-in telemetry client.

When EVALSIG_TELEMETRY=1, we append a single JSON line per event to
~/.evalsig/usage.jsonl (or $EVALSIG_TELEMETRY_PATH if set). No network
traffic happens here; the file is a local audit log. A future SaaS
shipper can rotate and upload it on its own schedule.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
from pathlib import Path
from typing import Any


def enabled() -> bool:
    """True only if the user has explicitly opted in."""
    return os.environ.get("EVALSIG_TELEMETRY", "").lower() in ("1", "true", "yes")


def _default_path() -> Path:
    custom = os.environ.get("EVALSIG_TELEMETRY_PATH")
    if custom:
        return Path(custom)
    return Path.home() / ".evalsig" / "usage.jsonl"


def emit(event: str, **fields: Any) -> None:
    """Record a single usage event. Silent no-op when disabled."""
    if not enabled():
        return
    path = _default_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "ts": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "event": event,
        **fields,
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")
