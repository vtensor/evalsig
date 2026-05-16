"""Reader for the append-only run history store."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from evalsig.io.parquet import read_runframe_parquet
from evalsig.store.manifest import RunRecord, load_manifest
from evalsig.store.schema import STORE_LAYOUT
from evalsig.types import RunFrame


@dataclass(frozen=True)
class RunHistoryRecord:
    """A manifest record plus the absolute path it lives at."""
    record: RunRecord
    abs_path: Path


def _project_root(root: str | Path, project_id: str) -> Path:
    return Path(root) / project_id


def list_runs(root: str | Path, project_id: str = "default"
              ) -> list[RunHistoryRecord]:
    """List every run a project has stored."""
    proj = _project_root(root, project_id)
    manifest = load_manifest(proj / STORE_LAYOUT.manifest_filename,
                             project_id=project_id)
    return [
        RunHistoryRecord(record=r, abs_path=proj / r.path)
        for r in manifest.runs
    ]


def query_runs(
    root: str | Path,
    *,
    project_id: str = "default",
    model_id: Optional[str] = None,
    task_id: Optional[str] = None,
    metric_name: Optional[str] = None,
    since: Optional[str] = None,        # ISO-8601 cutoff (inclusive)
    until: Optional[str] = None,        # ISO-8601 cutoff (inclusive)
) -> list[RunHistoryRecord]:
    """Filter runs by common metadata. All filters are AND-combined.

    Times are compared lexicographically on ISO strings, which works for
    correctly-formatted UTC timestamps.
    """
    out: list[RunHistoryRecord] = []
    for h in list_runs(root, project_id=project_id):
        r = h.record
        if model_id is not None and r.model_id != model_id:
            continue
        if task_id is not None and r.task_id != task_id:
            continue
        if metric_name is not None and r.metric_name != metric_name:
            continue
        if since is not None and r.ts < since:
            continue
        if until is not None and r.ts > until:
            continue
        out.append(h)
    return out


def load_run(root: str | Path, run_id: str, *,
             project_id: str = "default") -> RunFrame:
    """Load one run's RunFrame from the store by run_id."""
    proj = _project_root(root, project_id)
    manifest = load_manifest(proj / STORE_LAYOUT.manifest_filename,
                             project_id=project_id)
    for r in manifest.runs:
        if r.run_id == run_id:
            return read_runframe_parquet(proj / r.path)
    raise KeyError(f"run_id '{run_id}' not found in project '{project_id}'")
