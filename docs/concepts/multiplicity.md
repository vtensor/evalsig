# Multiple comparisons

If you test one task at alpha = 0.05 you have a 5% chance of a false
positive. If you test ten tasks independently at the same alpha, the
chance of at least one false positive is about 40%. Multiple-comparison
correction is how you keep that under control.

## When this comes up

* You run a release gate over a suite of tasks (MMLU, GPQA, AIME, SWE-bench,
  Terminal-Bench).
* You audit a model across subgroups (math, code, dialogue, creative
  writing).
* You compare many candidates against one baseline (a sweep of
  fine-tunes).

In each case you have multiple p-values and you need a coherent decision
rule.

## Two flavours of guarantee

| Guarantee | What it controls | When to use |
|---|---|---|
| Family-wise error rate (FWER) | Probability of any false positive | High-stakes shipments where one mistake is bad |
| False discovery rate (FDR) | Expected fraction of false positives among rejections | Exploration / ranking many candidates |

FWER is the conservative one and is the right default for a release gate.
FDR is more powerful when you have many tests and you're okay with a
small fraction being noise.

## Methods EVALSIG ships

### Bonferroni

Multiply every p-value by the number of tests, clip to 1. Conservative
but simple, and uniformly valid:

```python
from evalsig.inference import bonferroni
out = bonferroni([0.01, 0.04, 0.06, 0.20])
print(out.p_adjusted)   # [0.04, 0.16, 0.24, 0.80]
print(out.reject)       # [True, False, False, False]
```

### Holm

Sort the p-values, multiply the i-th smallest by (m - i + 1), enforce
monotone non-decreasing. Uniformly more powerful than Bonferroni at the
same FWER:

```python
from evalsig.inference import holm
out = holm([0.01, 0.04, 0.06, 0.20])
print(out.p_adjusted)   # [0.04, 0.12, 0.12, 0.20]
```

### Benjamini-Hochberg

FDR control. Sort, scale by m/rank, take the running minimum from the
largest p-value backwards:

```python
from evalsig.inference import benjamini_hochberg
out = benjamini_hochberg([0.01, 0.04, 0.06, 0.20])
print(out.p_adjusted)   # [0.04, 0.08, 0.08, 0.20]
```

## Worked example: multi-task release gate

```python
from evalsig import compare, ComparisonResult
from evalsig.inference import holm

tasks = ["mmlu", "gpqa", "aime", "swe-bench", "terminal-bench"]
results: dict[str, ComparisonResult] = {
    t: compare(load_baseline(t), load_candidate(t), one_sided=True)
    for t in tasks
}

p_values = [results[t].p_value for t in tasks]
adj = holm(p_values, alpha=0.05)

for t, p, rej in zip(tasks, adj.p_adjusted, adj.reject):
    print(f"{t:18}  raw p = {p:.4f}   reject = {rej}")
```

Ship only if every task you cared about is in the `reject` set, or fall
back to FDR control if your policy is "ship when most tasks improve".

## What you should not do

* Do not run five tests and report the smallest p-value. That is the
  multiple-comparison problem in its rawest form.
* Do not run five tests, see one significant result, and ignore the
  other four. You implicitly tested all five; correct for it.
* Do not use FDR on a release decision unless the policy is explicitly
  "okay with some false ships".

## See also

* [What evalsig solves](what-evalsig-solves.md) for where multiplicity
  fits in the bigger picture.
* `evalsig.inference.multiplicity` module reference for the function
  signatures.
