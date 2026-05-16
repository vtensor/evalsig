"""Reader protocol and a small format registry.

Every reader returns a RunFrame. The Protocol below pins the contract so
third-party harnesses can ship their own readers without depending on
evalsig internals.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Protocol, runtime_checkable

from evalsig.types import RunFrame


@runtime_checkable
class Reader(Protocol):
    """A reader is any callable that turns a path into a RunFrame."""
    def __call__(self, path: str | Path, **kwargs) -> RunFrame: ...


# Format name -> reader function. Filled in by `register_reader` so the
# CLI can offer --format with the right choices.
_REGISTRY: dict[str, Reader] = {}


def register_reader(name: str, reader: Reader) -> None:
    """Register a reader under a short format name."""
    if name in _REGISTRY:
        raise ValueError(f"reader '{name}' is already registered")
    _REGISTRY[name] = reader


def get_reader(name: str) -> Reader:
    """Look up a reader by format name. Raises KeyError if unknown."""
    if name not in _REGISTRY:
        raise KeyError(
            f"unknown format '{name}'; registered: {sorted(_REGISTRY)}"
        )
    return _REGISTRY[name]


def available_formats() -> list[str]:
    """Names of all registered readers."""
    return sorted(_REGISTRY)
