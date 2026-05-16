# What EVALSIG solves

This page is the conceptual map. Read it once and the rest of the docs
will make sense; skip it and every term will feel arbitrary.

## The pain in one paragraph

LLM evals are noisy, and the field reports point deltas as if they were
signals. Apple's GSM-Symbolic showed up to 65pp accuracy drops from adding
an irrelevant clause to a math problem with the same answer. Zhao et al.
showed swapping two few-shot examples drops accuracy from 88.5% to 51.3%.
Anthropic published a 6pp swing on Terminal-Bench 2.0 from infrastructure
config alone. And frontier labs ship model updates on 1 to 3 percentage
point deltas. Without the right statistical lens, you cannot tell which
is which.

## What real eval pipelines need

To responsibly say "model B is better than model A" on an eval, you need
to answer four questions:

1. **Is the delta real?** That is a p-value or a confidence interval.
2. **Is it big enough to care about?** That is your minimum-delta policy.
3. **Could we even have seen it if it were real?** That is power /
   minimum-detectable-effect.
4. **Did we account for the structure of the data?** That is clustered
   standard errors, paired vs unpaired, and multiple-comparison correction.

Every commercial eval tool today answers at most one of these. EVALSIG
answers all four.

## How EVALSIG fits into your pipeline

```
your eval harness          EVALSIG                       your CI / dashboards
-----------------          ----------------------        ----------------------
[ Inspect AI       ]
[ lm-eval-harness  ]  ->   [ evalsig.io       ]   ->     gate exit code 0/1/2
[ HELM             ]       [ evalsig.inference]          JSON report
[ simple-evals     ]       [ evalsig.compare  ]          Markdown PR comment
[ your own runner  ]       [ evalsig.store    ]          Parquet history
```

EVALSIG does *not* run your eval and does *not* grade your model. It sits
between the scoring step and the release decision.

## Why paired inference is the unlock

Frontier models correlate 0.3 to 0.7 question-to-question: easy items are
easy for both, hard items are hard for both. If you take that pairing into
account, the variance of the difference is far smaller than the variance
of either run alone. The Miller (2024) paper calls this "free variance
reduction".

Concretely: at a 1.5pp lift on 500 items, our research validation script
finds the paired permutation test fires 85.8% of the time, while an
unpaired Welch t-test on the same data fires 0.0% of the time. Same data,
same effect, different inference. The unpaired test is throwing away most
of what you collected.

See [Paired vs unpaired](paired-vs-unpaired.md) for the mechanics.

## Why clustered standard errors matter

Most public benchmarks have items that move together: several questions
from one passage, several problems from one template, several plans from
one task. Naive item-level inference treats them as independent, undercounts
the variance, and reports tighter confidence intervals than the data
actually supports.

In our validation, an H0 scenario with cluster-level shared shifts produced
a false-positive rate of 43.2% under the naive bootstrap, vs 5.5% under the
cluster bootstrap. That is a factor of nine difference in the chance you
ship a non-existent improvement.

See [Clustered standard errors](clustering.md) for the model.

## Why minimum detectable effect matters

The first thing customers ask is "I see a 1.2pp delta, is it real?". The
second thing they ask, once they understand the first, is "How small could
the true effect be and still escape my test?".

That is the minimum detectable effect. If your run can only detect effects
larger than 3pp, and you observed a 1.2pp delta that came back not
significant, you cannot say "no effect" -- you can only say "we wouldn't
have seen it either way". That is a different conclusion from a properly
powered null result, and EVALSIG's gate flags it as INCONCLUSIVE rather
than REJECT.

See [MDE and power](mde-and-power.md) for the formula and the calibration
study.

## Why sequential testing matters

Expensive evals (long-context agentic benchmarks, large reasoning suites)
take hours per run. You'd like to stop as soon as the answer is clear,
without inflating false positives. Standard tests forbid peeking; sequential
tests are explicitly designed to allow it.

EVALSIG ships an always-valid confidence sequence (Howard et al. 2021) so
you can call `evalsig watch` on an in-progress run and stop as soon as the
interval excludes zero. The alpha is spent globally, so the guarantee holds
at every sample size you check.

See [Sequential testing](sequential-testing.md).

## Why multiple-comparison correction matters

If you gate on 10 tasks at once with alpha = 0.05 each, the chance that at
least one task fires a false positive is about 40%. Either tighten the
per-task alpha (Bonferroni / Holm), or shift to false-discovery-rate
control (Benjamini-Hochberg) where the expected fraction of false
rejections among all rejections stays below alpha.

EVALSIG ships all three so you can pick the regime that fits your release
policy.

See [Multiple comparisons](multiplicity.md).

## The bottom line

EVALSIG is a release gate. Its single job is to convert a pair of eval
runs plus a policy (alpha, power, min-delta) into one of three answers:
ALLOW, REJECT, INCONCLUSIVE. Everything else in the package (the IO
layer, the store, the dashboards, the integrations) exists to make that
gate easier to plug in.
