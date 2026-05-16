# Scenario: multi-task gates

You have an eval suite (MMLU-Pro, GPQA, AIME, SWE-bench, Terminal-Bench)
and your release policy is "the candidate must not regress on any task,
and must improve on at least one". How do you express that as a gate
without inflating false positives?

## The naive mistake

Running five independent gates at alpha = 0.05 means the chance that
at least one fires a false positive is about 23%. If your policy is
"must improve on at least one", you will ship roughly one in four
no-effect candidates by accident.

## The correction

Use a multiple-comparison correction over the per-task p-values.

```python
from evalsig import compare
from evalsig.inference import holm

tasks = ["mmlu", "gpqa", "aime", "swe-bench", "terminal-bench"]
results = {
    t: compare(load_baseline(t), load_candidate(t), one_sided=True)
    for t in tasks
}

# Improvement check: Holm step-down on the one-sided p-values.
p_values = [results[t].p_value for t in tasks]
adj = holm(p_values, alpha=0.05)

improved = [t for t, rej in zip(tasks, adj.reject) if rej]
print("improved (FWER-controlled):", improved)
```

If your policy is "no regressions on any task", run the comparison
in the other direction (or two-sided) and check that no task's
**lower** CI bound falls below the negative of `min_delta`:

```python
regressed = []
for t, r in results.items():
    lo, _ = r.ci
    if lo < -0.005:
        regressed.append(t)
print("regressed:", regressed)
```

## A combined gate

```python
def multi_task_gate(tasks, load_baseline, load_candidate,
                    min_delta=0.005, alpha=0.05, power=0.80):
    results = {
        t: compare(load_baseline(t), load_candidate(t), one_sided=True,
                   alpha=alpha, target_power=power)
        for t in tasks
    }
    p_values = [results[t].p_value for t in tasks]
    adj = holm(p_values, alpha=alpha)
    improved = {t for t, rej in zip(tasks, adj.reject) if rej}

    # Regression check at min_delta on each task.
    regressed = {
        t for t, r in results.items()
        if r.ci[0] is not None and r.ci[0] < -min_delta
    }

    if regressed:
        return "REJECT", {"regressed": list(regressed)}
    if improved:
        return "ALLOW", {"improved": list(improved)}
    return "INCONCLUSIVE", {"reason": "no significant improvement on any task"}
```

## FDR if you have many tasks

When you compare on twenty or more tasks, Bonferroni and Holm become
restrictive. Switch to BH (Benjamini-Hochberg) for FDR control:

```python
from evalsig.inference import benjamini_hochberg
adj = benjamini_hochberg(p_values, alpha=0.10)  # 10% FDR
```

This is the right regime for exploration ("show me which tasks moved");
it is not appropriate for a strict release gate. Keep BH for analysis,
FWER for shipping.

## See also

* [Concepts: multiple comparisons](../concepts/multiplicity.md)
* [Modules: inference](../modules/inference.md): multiplicity functions.
* [Compliance audit trail](compliance-audit-trail.md): persisting the
  combined report.
