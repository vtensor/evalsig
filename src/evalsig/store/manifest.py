"""Per-project manifest (JSON) listing every stored run.

We keep it as a single JSON file because manifests stay small (one
record per run, not per item) and JSON is the friendliest format for
git-tracked stores. For projects with millions of runs we'd switch to a
SQLite index, but that's a v2 problem.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class RunRecord:
    run_id: str
    model_id: str
    task_id: str
    metric_name: str
    ts: str            # ISO-8601 in UTC
    path: str          # path relative to the project root
    n_items: int
    config_hash: str = ""
    delta: Optional[float] = None
    p_value: Optional[float] = None
    verdict: Optional[str] = None
    parent_run_id: Optional[str] = None

    def to_dict(self) -> dict:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, obj: dict) -> "RunRecord":
        return cls(**obj)


@dataclass
class Manifest:
    project_id: str
    version: int = 1
    runs: list[RunRecord] = field(default_factory=list)

    def add(self, record: RunRecord) -> None:
        # Replace if the same run_id is being re-written.
        self.runs = [r for r in self.runs if r.run_id != record.run_id]
        self.runs.append(record)

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "version": self.version,
            "runs": [r.to_dict() for r in self.runs],
        }

    @classmethod
    def from_dict(cls, obj: dict) -> "Manifest":
        return cls(
            project_id=obj["project_id"],
            version=int(obj.get("version", 1)),
            runs=[RunRecord.from_dict(r) for r in obj.get("runs", [])],
        )


def load_manifest(path: str | Path, *, project_id: str | None = None
                  ) -> Manifest:
    """Load the project manifest. Returns an empty one if the file is
    missing."""
    p = Path(path)
    if not p.exists():
        return Manifest(project_id=project_id or "default")
    return Manifest.from_dict(json.loads(p.read_text()))


def save_manifest(manifest: Manifest, path: str | Path) -> None:
    """Write the manifest to disk (atomic via tempfile rename)."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(manifest.to_dict(), indent=2))
    tmp.replace(p)
