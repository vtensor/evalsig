# Scenario: compliance audit trail

You ship LLM-powered features into a regulated industry (finance,
healthcare, defence). Every release decision needs to be defensible to
an auditor a year later. This page is the recipe for capturing exactly
that, with EVALSIG as the source of truth.

## What auditors want to see

1. The data the decision was based on (the two RunFrame files).
2. The exact statistical inference that was run (method, alpha, power,
   min-delta).
3. The verdict and the underlying p-value, CI, and MDE.
4. A timestamp and an immutable identity for the decision.

EVALSIG's JSON report covers (2) and (3). The store and a hash chain
cover (1) and (4).

## The capture script

```python title="scripts/audit_capture.py"
import hashlib
import json
from pathlib import Path

from evalsig import gate
from evalsig.io import read_runframe_json
from evalsig.store import write_run


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def main(baseline_path: str, candidate_path: str, project_id: str,
         out_dir: str) -> int:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    a = read_runframe_json(baseline_path)
    b = read_runframe_json(candidate_path)
    report = gate(a, b, min_delta=0.005, alpha=0.05, power=0.80,
                  cluster="passage_id", one_sided=True)

    # Persist the inputs into the store with the verdict.
    write_run(out / "store", a, project_id=project_id, verdict=None,
              parent_run_id=None)
    write_run(out / "store", b, project_id=project_id,
              delta=report.comparison.delta,
              p_value=report.comparison.p_value,
              verdict=report.verdict.value,
              parent_run_id=a.run_id)

    # Build the audit envelope.
    envelope = {
        "verdict": report.verdict.value,
        "exit_code": report.exit_code,
        "report": report.to_dict(),
        "inputs": {
            "baseline": {"path": baseline_path,
                         "sha256": sha256_of(Path(baseline_path))},
            "candidate": {"path": candidate_path,
                          "sha256": sha256_of(Path(candidate_path))},
        },
    }
    (out / "audit.json").write_text(json.dumps(envelope, indent=2))
    return report.exit_code
```

The envelope is the artefact you keep. It is small (a few KB), readable
in plain text, and contains everything an auditor needs.

## Signing the envelope

If your stack uses Sigstore or a corporate CA, wrap the script's output
with the signer of your choice:

```bash
cosign sign-blob audit.json --output-signature audit.json.sig
```

EVALSIG does not ship a signer. Keeping it out of the package means
your security team chooses the trust root.

## Storing the trail

Two options:

* **In-repo:** commit `audit/<release-id>/audit.json` per release. Git
  is already an append-only Merkle log, which is most of what you need.
* **In a separate write-once bucket:** S3 with object-lock or GCS with
  retention policies. EVALSIG's store layout is partition-friendly,
  which makes this easy.

## Querying the trail

For any past release:

```bash
evalsig history \
  --root /var/audit/evalsig \
  --project mmlu-pro \
  --since 2026-01-01 --until 2026-06-30
```

You get a one-line summary per run plus a path to the underlying
Parquet. Load any run back into Python with `evalsig.store.load_run`.

## What you should not do

* **Do not regenerate the report from the candidate file alone.** The
  audit needs the *baseline* hash too, otherwise you can swap baselines
  silently.
* **Do not edit `audit.json` after the fact.** If a verdict changes,
  it gets a new envelope; the old one stays as-is. Append, never mutate.

## See also

* [Output formats: JSON](../usage/output-formats.md#json)
* [Modules: store](../modules/store.md)
