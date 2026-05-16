# Sequential testing

Fixed-sample tests assume you decide the sample size before peeking at
the data. If you peek halfway through and stop early, you inflate the
false-positive rate. Sequential tests are explicitly designed to allow
peeking: the guarantee holds at every sample size you check.

This matters most for expensive evals. Long-context agentic benchmarks
can take hours per run; you would like to stop as soon as the signal is
clear, not after a fixed budget.

## The idea

Build a confidence interval that is valid for **all sample sizes
simultaneously**, not just one. As soon as the interval excludes zero
(in the direction you care about), you stop and report "significant".
Alpha is spent globally, so the test is honest no matter how many times
you peek.

EVALSIG implements the Howard et al. (2021) "asymptotic confidence
sequence" for the running mean of bounded i.i.d. observations:

```
width(t) = sigma * sqrt( (2 * (t + rho^2) * log( sqrt(t + rho^2) / (alpha * rho) )) / t^2 )
```

`rho` is a tuning parameter that controls where the bound is sharpest.
The default `rho = 1.0` is a sensible choice when you don't know the
expected stopping time in advance.

## Python API

```python
from evalsig.inference import sequential_gate

diffs = stream_of_paired_diffs()   # any iterable of floats
out = sequential_gate(diffs, alternative="greater", alpha=0.05, min_n=30)

if out.stopped:
    print(f"Significant at n={out.n_pairs}, delta={out.delta:+.4f}")
else:
    print(f"Walked the whole stream, no rejection (n={out.n_pairs})")
```

`min_n` is a small warm-up: we never claim significance before this
sample size because the early bound is essentially infinite anyway.

## CLI

If you have the paired runs as files (RunFrame JSON, lm-eval JSONL, etc.)
you can also call:

```bash
evalsig watch \
  --baseline baseline.json \
  --candidate candidate.json \
  --metric accuracy \
  --alpha 0.05 \
  --alternative greater \
  --min-n 30
```

Exit code is 0 if the test fires (the candidate is significantly better),
2 otherwise.

## What you give up

A sequential test trades some efficiency for the peek-when-you-want
guarantee. In our experiments, the sequential test usually needs about
1.5x to 2x more items than a perfectly-sized fixed test to reach the
same conclusion at the same alpha. The exchange is almost always
worth it when:

* runs are expensive and you can stop them midway
* you do not know in advance how many items you will be able to afford
* you are running an A/B for a long time and want to keep peeking

## What stays the same

Sequential tests still need cluster awareness when items are grouped, and
they still need a paired pairing when items are paired. The `watch`
command in EVALSIG handles the paired case (it diffs items by id before
streaming).

## See also

* [MDE and power](mde-and-power.md): the fixed-sample alternative.
* [What evalsig solves](what-evalsig-solves.md): how sequential testing
  fits into the larger story.
* `evalsig.inference.sequential` module reference: function signatures
  and parameters.
