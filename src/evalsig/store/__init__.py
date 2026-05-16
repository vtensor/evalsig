"""Append-only run history store.

The store sits on top of Parquet + a small JSON manifest. It is
optional: the OSS CLI gates work fine without it. The SaaS dashboards
read from the same Parquet lake the OSS users write to, so customers
can move between them without re-instrumenting.
"""
from evalsig.store.schema import STORE_LAYOUT
from evalsig.store.writer import write_run, RunStoreWriter
from evalsig.store.reader import (
    list_runs,
    load_run,
    query_runs,
    RunHistoryRecord,
)
from evalsig.store.manifest import Manifest, load_manifest, save_manifest

__all__ = [
    "STORE_LAYOUT",
    "write_run",
    "RunStoreWriter",
    "list_runs",
    "load_run",
    "query_runs",
    "RunHistoryRecord",
    "Manifest",
    "load_manifest",
    "save_manifest",
]
