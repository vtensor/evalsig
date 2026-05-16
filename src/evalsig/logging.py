"""Lightweight logging helpers.

We avoid pulling in structlog as a hard dependency. Instead we configure
the stdlib logger with a small format and let users override it.
"""
from __future__ import annotations

import logging
import os
import sys
from typing import Optional


_DEFAULT_FORMAT = "%(asctime)s %(name)s %(levelname)s %(message)s"


def get_logger(name: str = "evalsig") -> logging.Logger:
    """Return a logger pre-configured with a sensible default handler.

    Honours the EVALSIG_LOG_LEVEL environment variable. Calling this many
    times is safe: handlers are only added once.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter(_DEFAULT_FORMAT))
        logger.addHandler(handler)
        level_name = os.environ.get("EVALSIG_LOG_LEVEL", "WARNING").upper()
        logger.setLevel(getattr(logging, level_name, logging.WARNING))
        logger.propagate = False
    return logger


def set_level(level: str | int, name: Optional[str] = "evalsig") -> None:
    """Override the level on the evalsig logger."""
    logger = logging.getLogger(name)
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(level)
