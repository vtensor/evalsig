# Scenario: sequential watch in CI

Your eval suite takes hours per run. You want to stop as soon as the
verdict is clear, without inflating false positives by peeking at a
fixed-sample p-value. This is what `evalsig watch` is for.

## The pattern

1. Stream items from the eval harness as they finish.
2. Pair each item across baseline and candidate.
3. Feed the per-item differences into `sequential_gate`.
4. Stop the run (and exit the CI step) as soon as the CI excludes zero.

## A Python harness

```python
import itertools
from evalsig.inference import sequential_gate

def paired_diff_stream(baseline_iter, candidate_iter):
    base_map = {}
    for it in baseline_iter:
        base_map[it.item_id] = it.score
    # Walk candidate items; when we have a match, yield the diff.
    for it in candidate_iter:
        if it.item_id in base_map:
            yield it.score - base_map[it.item_id]

stream = paired_diff_stream(stream_baseline_items(), stream_candidate_items())
out = sequential_gate(stream, alpha=0.05, alternative="greater", min_n=30)

print(f"stopped after {out.n_pairs} items at delta={out.delta:+.4f}")
print("ship" if out.stopped else "do not ship")
```

`sequential_gate` walks the iterator one item at a time, updates the
running mean and the Howard 2021 confidence sequence, and returns as
soon as the CI excludes zero (or when the iterator is exhausted).

## Using the CLI

If your harness writes per-item results to a file as it goes (one JSON
record per line), you can call:

```bash
evalsig watch \
  --baseline baseline.json \
  --candidate candidate.json \
  --metric accuracy \
  --alternative greater \
  --alpha 0.05 \
  --min-n 30
```

Exit code is 0 if the test fires, 2 otherwise. Wire it into your CI
step the same way you would `evalsig gate`.

## Tuning `rho`

`rho` controls where the bound is sharpest. The default `rho = 1.0` is
sensible when you do not know the expected stopping time in advance.
If your runs typically take 200 to 500 items to reject, set
`rho = sqrt(500)` for a slightly tighter bound around that range.

## What you give up

Sequential tests are less efficient than perfectly-sized fixed tests:
expect roughly 1.5x to 2x more items to reach the same conclusion.
The exchange is worth it when:

* runs are expensive and you can stop mid-flight,
* you do not know how many items you can afford,
* you want to keep peeking honestly.

It is **not** worth it when you have a fixed eval budget anyway --
just run all the items and use the regular `gate`.

## Don't double-test

Picking the smaller of (sequential gate, fixed gate) re-introduces
multiple testing and breaks alpha. Pick one in advance and commit.

## See also

* [Concepts: sequential testing](../concepts/sequential-testing.md)
* [Modules: inference](../modules/inference.md): `confidence_sequence`
  and `sequential_gate` signatures.
