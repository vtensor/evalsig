# Scenario: auditing third-party evals

A vendor says "model B is 3pp better than model A on MMLU-Pro". You
have the underlying samples files. The question: is the claim
defensible?

This is the audit case, and the right tool is `evalsig compare` with
the most conservative settings.

## What "defensible" means

A vendor claim is defensible when:

1. The eval set is large enough to detect the claimed delta at the
   conventional power (80%).
2. The paired test on item-level scores gives a CI that excludes the
   null in the claimed direction.
3. The per-item variance accounts for item grouping (cluster bootstrap
   if items have natural groups).
4. The number of comparisons reported did not inflate alpha (one
   benchmark in isolation, fine; "best of ten" tasks, suspicious).

## The audit workflow

```bash
# 1. Validate inputs.
evalsig doctor vendor-baseline.json vendor-candidate.json

# 2. Use a two-sided test for an audit (you have no reason to assume
# the direction in advance).
evalsig compare \
  --baseline vendor-baseline.json \
  --candidate vendor-candidate.json \
  --cluster passage_id \
  --alpha 0.05 \
  --power 0.80 \
  --output markdown > audit-report.md
```

The Markdown output is the audit artefact: archive it together with
the input files and a hash of each.

## When the claim is real

You get something like:

```
delta:       +0.0312
CI (95%):    [+0.0188, +0.0436]
p-value:     1.4e-06
method:      cluster_bootstrap
n_pairs:     14080  (704 clusters)
MDE@80%:     0.0094
significant: True
```

The 95% CI excludes 0 and the MDE is well below the claimed delta.
Defensible.

## When the claim does not hold up

```
delta:       +0.0312
CI (95%):    [-0.0011, +0.0635]
p-value:     0.058
method:      cluster_bootstrap
n_pairs:     408  (44 clusters)
MDE@80%:     0.0312
significant: False

note: item-set coverage is 78% (below 95%); 56 items only in candidate,
      32 only in baseline
```

Three red flags:

1. The CI dips below zero. The 3pp claim is consistent with no effect.
2. The MDE equals the claimed delta. The eval was just barely powered
   for what they claimed, and it didn't quite clear the bar.
3. Item-set coverage is 78%. Some items appear in only one run; that
   alignment problem alone can bias the aggregate.

## The "subgroup snipe" anti-pattern

A common slide-deck trick: "model B is +5pp better on the math subset".
That is a subgroup analysis. If they ran the same comparison on ten
subgroups and reported only the best one, alpha is inflated.

The honest version is to run all ten and apply a multiple-comparison
correction:

```python
from evalsig.inference import holm
from evalsig import compare

results = {sg: compare(load(sg, "a"), load(sg, "b"))
           for sg in ("math", "code", "...", "trivia")}
p_values = [r.p_value for r in results.values()]
adj = holm(p_values, alpha=0.05)

for (sg, r), reject in zip(results.items(), adj.reject):
    print(f"{sg:18}  delta={r.delta:+.4f}  adj_p={adj.p_adjusted[i]:.4f}  ship={reject}")
```

See [Multiple comparisons](../concepts/multiplicity.md).

## What you should not do

* **Don't accept aggregate deltas with no item-level data.** Without
  the per-item file you cannot pair, cluster, or compute MDE.
* **Don't anchor on the headline number.** A 3pp claim with a 4pp MDE
  is no claim at all.

## See also

* [Concepts: clustered standard errors](../concepts/clustering.md)
* [Concepts: multiplicity](../concepts/multiplicity.md)
* [Compliance audit trail](compliance-audit-trail.md)
