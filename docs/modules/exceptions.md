# `evalsig.exceptions`

A typed exception hierarchy. Catch the root once and you catch every
EVALSIG-originating error.

## Hierarchy

```
EvalsigError                       (root)
+-- SchemaError                    (JSON did not match the RunFrame schema)
+-- AlignmentError                 (two runs cannot be aligned)
+-- InferenceError                 (statistical primitive misused)
+-- GatePolicyError                (gate called with an invalid policy)
+-- StoreError                     (store write or read failed)
+-- IntegrationError               (optional dependency missing or upstream failed)
```

## Why typed exceptions

Without a hierarchy, callers either catch `Exception` (which swallows
keyboard interrupts and bugs) or catch nothing (which means the program
exits on user input errors). With one, you can:

```python
from evalsig.exceptions import EvalsigError, SchemaError, AlignmentError

try:
    result = compare(load_a(), load_b())
except SchemaError as e:
    user_facing_error(f"Bad input file: {e}")
except AlignmentError as e:
    user_facing_error(f"Runs do not line up: {e}")
except EvalsigError as e:
    user_facing_error(f"Eval gate failed: {e}")
```

## When each one fires

* **`SchemaError`** -- JSON missing a required field, wrong type, or
  the file is not valid JSON.
* **`AlignmentError`** -- two runs have no overlapping `item_id`,
  coverage is below the safety threshold, or cluster ids disagree in
  ways that cannot be reconciled.
* **`InferenceError`** -- shape mismatch, too few items, or a method
  was called with arguments it does not support.
* **`GatePolicyError`** -- `min_delta`, `alpha`, or `power` outside
  their valid range, contradictory `one_sided`/direction settings.
* **`StoreError`** -- corrupt manifest, Parquet write failure, missing
  run id in a query.
* **`IntegrationError`** -- the user asked for the Braintrust
  integration without installing `braintrust`, or a pytest fixture
  was misused.

## CLI translation

The CLI translates these into exit codes:

* `SchemaError`, `AlignmentError` -> exit 65 (BSD `EX_DATAERR`)
* `GatePolicyError` -> exit 64 (BSD `EX_USAGE`)
* `InferenceError`, `StoreError`, `IntegrationError` -> exit 70 (BSD
  `EX_SOFTWARE`)

## See also

* [Modules: types](types.md): the data shapes these errors guard.
* [Modules: compare](compare.md): the gate's policy validation.
