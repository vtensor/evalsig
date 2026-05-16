"""Writer for the append-only run history store."""
from __future__ import annotations

import datetime as _dt
from pathlib import Path
from typing import Optional

from evalsig.io.parquet import write_runframe_parquet
from evalsig.store.manifest import (
    Manifest,
    RunRecord,
    load_manifest,
    save_manifest,
)
from evalsig.store.schema import STORE_LAYOUT
from evalsig.types import RunFrame


def _partition_path(project_root: Path, run: RunFrame,
                    ts: _dt.datetime) -> Path:
    """Decide where a run's Parquet file lives inside the project root."""
    parts: list[str] = []
    if STORE_LAYOUT.partition_year:
        parts.append(f"year={ts.year:04d}")
    if STORE_LAYOUT.partition_month:
        parts.append(f"month={ts.month:02d}")
    parts.append(f"run_id={run.run_id}{STORE_LAYOUT.file_extension}")
    return project_root.joinpath(*parts)


class RunStoreWriter:
    """Light handle for writing many runs to one project.

    Loads the manifest once on construction; `commit()` flushes it to
    disk. Use as a context manager to commit automatically.
    """
    def __init__(self, root: str | Path, project_id: str = "default"):
        self.root = Path(root)
        self.project_id = project_id
        self.project_root = self.root / project_id
        self.project_root.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.project_root / STORE_LAYOUT.manifest_filename
        self.manifest: Manifest = load_manifest(
            self.manifest_path, project_id=project_id,
        )

    def __enter__(self) -> "RunStoreWriter":
        return self

    def __exit__(self, *_exc) -> None:
        self.commit()

    def write(self, run: RunFrame, *,
              ts: Optional[_dt.datetime] = None,
              delta: Optional[float] = None,
              p_value: Optional[float] = None,
              verdict: Optional[str] = None,
              parent_run_id: Optional[str] = None) -> RunRecord:
        if ts is None:
            ts = _dt.datetime.now(_dt.timezone.utc)
        out_path = _partition_path(self.project_root, run, ts)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        write_runframe_parquet(run, out_path, project_id=self.project_id)

        rel = out_path.relative_to(self.project_root).as_posix()
        record = RunRecord(
            run_id=run.run_id,
            model_id=run.model_id,
            task_id=run.task_id,
            metric_name=run.metric_name,
            ts=ts.isoformat(),
            path=rel,
            n_items=len(run.items),
            config_hash=run.config_hash,
            delta=delta,
            p_value=p_value,
            verdict=verdict,
            parent_run_id=parent_run_id,
        )
        self.manifest.add(record)
        return record

    def commit(self) -> None:
        save_manifest(self.manifest, self.manifest_path)


def write_run(root: str | Path, run: RunFrame, *,
              project_id: str = "default",
              **kwargs) -> RunRecord:
    """Convenience wrapper: write a single run and commit immediately."""
    with RunStoreWriter(root, project_id=project_id) as w:
        return w.write(run, **kwargs)
