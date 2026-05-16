# Scenario: A/B on RLHF checkpoints

You run an RLHF loop. Every few hours you have a fresh checkpoint and
need to decide whether to promote it. The eval suite is fixed; the
items overlap exactly between runs; the per-step deltas are typically
small.

This is the canonical paired-difference scenario, and EVALSIG's gate
is built for it.

## The setup

* Baseline: the current production checkpoint, scored on the eval
  suite.
* Candidate: the new RLHF checkpoint, scored on the same suite.
* Decision: promote iff the candidate is statistically better at a
  policy threshold of 1pp.

## The script

```python title="scripts/promote_or_reject.py"
import sys
from evalsig import gate
from evalsig.io import read_runframe_json

baseline = read_runframe_json("baseline.json")
candidate = read_runframe_json(sys.argv[1])

report = gate(
    baseline, candidate,
    min_delta=0.01,        # promotion policy: at least 1pp better
    alpha=0.05,
    power=0.80,
    one_sided=True,
    rng=0,
)

print(report.verdict.value)
sys.exit(report.exit_code)
```

Run it after every checkpoint:

```bash
python scripts/promote_or_reject.py checkpoint-step-12345.json
case $? in
    0) ./promote.sh ;;
    1) echo "checkpoint rejected" ;;
    2) echo "need more eval items" ;;
esac
```

## Recording history

If you also want the per-checkpoint trend, write each candidate plus its
verdict into the local store:

```python
from evalsig.store import write_run

write_run(
    "/var/lib/evalsig/store",
    candidate,
    project_id="rlhf-loop",
    delta=report.comparison.delta,
    p_value=report.comparison.p_value,
    verdict=report.verdict.value,
    parent_run_id=baseline.run_id,
)
```

And query later:

```bash
evalsig history --root /var/lib/evalsig/store --project rlhf-loop \
    --since 2026-05-01 --until 2026-06-01
```

## When the answer is "not yet"

Small deltas plus a small eval suite mean a lot of INCONCLUSIVE
verdicts. Two options:

* **Grow the suite.** `evalsig.required_n(target_delta=0.005, sd_diff=0.3)`
  gives you the number.
* **Switch to a sequential gate.** Stream item-level diffs as you
  collect them and stop as soon as the always-valid CI excludes zero.
  See [Sequential watch in CI](sequential-watch.md).

## What you should not do

* **Don't peek at fixed-sample p-values and stop early.** The alpha
  guarantee fails. If you want to peek, use `evalsig watch`.
* **Don't promote on a single 1pp delta without checking the MDE.**
  Without the MDE, you don't know whether you're seeing signal or
  noise.

## See also

* [Concepts: paired vs unpaired](../concepts/paired-vs-unpaired.md)
* [Concepts: MDE and power](../concepts/mde-and-power.md)
* [Scenarios: sequential watch in CI](sequential-watch.md)
