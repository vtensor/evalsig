"""On-disk layout for the run history.

The store is partitioned by project and date so queries on a single
project / month do not need to scan everything.

  {root}/{project}/year=YYYY/month=MM/run_id={run_id}.parquet
  {root}/{project}/manifest.json

The manifest summarises every run in the project (model, task, metric,
delta if known, exit code). It is the lookup index that `evalsig
history` queries. Listing runs without the manifest works too; it is
just slower.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StoreLayout:
    # Layout knobs in one place so we can evolve them later.
    manifest_filename: str = "manifest.json"
    file_extension: str = ".parquet"
    partition_year: bool = True
    partition_month: bool = True


STORE_LAYOUT = StoreLayout()
