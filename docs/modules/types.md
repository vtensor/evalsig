# `evalsig.types`

Canonical data types that travel between modules. All are frozen
dataclasses; mutation is by design impossible.

## `ItemResult`

One scored unit in an eval run.

```python
@dataclass(frozen=True)
class ItemResult:
    item_id: str
    score: float
    cluster_id: Optional[str] = None
    epoch: int = 0
    metadata: dict = field(default_factory=dict)
```

**Fields:**

* `item_id` -- the identifier that lines this item up with the same item
  in the other run.
* `score` -- the per-item metric. 0/1 binary is the most common; any
  float is accepted.
* `cluster_id` -- optional group label. Required for cluster-aware
  inference.
* `epoch` -- repeated runs of the same item carry distinct epoch
  numbers. v1 of EVALSIG only uses epoch 0 for inference; future
  versions will fold multi-epoch variance in.
* `metadata` -- free-form bag for whatever your harness emits.

## `RunFrame`

One model's run on one task.

```python
@dataclass(frozen=True)
class RunFrame:
    run_id: str
    model_id: str
    task_id: str
    metric_name: str
    items: Sequence[ItemResult]
    config_hash: str = ""
```

**Fields:**

* `run_id` -- unique identifier for the run (typically
  `f"{model_id}::{task_id}"` or a UUID).
* `model_id`, `task_id`, `metric_name` -- the descriptive triple.
* `items` -- the per-item scores.
* `config_hash` -- a stable hash of the model + harness configuration.
  Use it to detect "did we run this exact config before?" without
  diffing fields.

A `RunFrame` raises `ValueError` at construction if `items` is empty.

## `ComparisonResult`

The output of `compare()`. Everything downstream renders from this.

```python
@dataclass(frozen=True)
class ComparisonResult:
    delta: float
    ci: tuple[float, float]
    ci_level: float
    p_value: float
    significant: bool
    n_pairs: int
    n_clusters: Optional[int]
    method: str
    mde: float
    notes: tuple[str, ...] = ()
```

Methods:

* `to_dict()` -- JSON-friendly view. Used by `to_json` and the SaaS
  schema.

See [Understanding the output](../get-started/understanding-output.md)
for a field-by-field tour.

## `MDEResult`

The output of `mde()`, also the input for transparent reporting in the
gate.

```python
@dataclass(frozen=True)
class MDEResult:
    mde: float
    alpha: float
    power: float
    n_pairs: int
    sd_diff: float
    n_clusters: Optional[int] = None
    icc: Optional[float] = None
    deff: Optional[float] = None
```

`deff` is the design effect when items are clustered; `None` otherwise.

## Why these are frozen

A release verdict is the kind of value you want to surface in many
places (CI logs, dashboards, audit reports) without worrying about
mutation. Frozen dataclasses give you immutability and structural
equality for free, and they pickle cleanly for queue-based systems.

## See also

* [Python API](../usage/python-api.md): how these types appear in
  client code.
* [Output formats](../usage/output-formats.md): how `to_dict()` is
  serialised.
