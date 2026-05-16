# Glossary

A short dictionary of the terms EVALSIG uses, in plain English. When
something here disagrees with a stats textbook, defer to the textbook;
this page is meant as a quick reference, not a rigorous definition.

**Alpha (alpha).** The chance the test fires when there really is no
effect. The standard value is 0.05 (5%).

**Beta (beta).** The chance the test misses a real effect. Power equals
`1 - beta`. The standard target is 0.80 (80% power, 20% beta).

**Benjamini-Hochberg (BH).** A multiple-comparison correction that
controls the *false discovery rate*. Use when you have many tests and a
small fraction of false positives is acceptable.

**Bonferroni.** The simplest multiple-comparison correction: multiply
every p-value by the number of tests. Conservative but always valid.

**Bootstrap.** Resample your data with replacement many times to
estimate the variance of an estimator. Use when you don't want to
assume a particular distribution.

**Candidate.** The new run you are evaluating against the baseline. In
EVALSIG this is the second argument to `compare()` and `gate()`.

**Cliff's delta.** A non-parametric effect size in `[-1, +1]`. The
probability that a random `b` beats a random `a`, minus the reverse.

**Cluster bootstrap.** A bootstrap that resamples whole groups of items
(passages, templates) instead of individual items. Required when items
inside a group move together.

**Cluster id.** A label on each item telling EVALSIG which group it
belongs to. Pass `cluster=<name>` to opt into cluster-aware inference.

**Cohen's d.** The mean difference divided by the standard deviation.
Comes in two flavours: two-sample (pooled SD) and paired (SD of the
per-item difference).

**Confidence interval (CI).** A range that the true value falls inside
some fraction of the time (typically 95%). Width is the practical
measure of "how much did we learn".

**Confidence sequence.** Like a confidence interval, but valid at every
sample size simultaneously. The basis of EVALSIG's sequential test.

**Delta.** The estimated effect: candidate mean minus baseline mean.

**Design effect (deff).** A factor that adjusts your effective sample
size when items are clustered: `deff = 1 + (m - 1) * icc` where `m` is
the mean cluster size.

**Discordant pair.** In McNemar's test, an item where the two runs
disagree (one got it right, the other got it wrong). Only these items
carry information.

**Effective N (n_eff).** Sample size after correcting for clustering:
`n_eff = n / deff`.

**E-value / always-valid test.** An anytime-valid statistical test
that lets you peek at the data without inflating the false-positive
rate. EVALSIG ships the Howard 2021 asymptotic version.

**False discovery rate (FDR).** The expected fraction of false
positives among the rejected hypotheses. The BH method controls this.

**Family-wise error rate (FWER).** The probability of any false
positive across a family of tests. Bonferroni and Holm both control
this.

**Gate.** The release decision: ALLOW, REJECT, or INCONCLUSIVE. The
top-level `gate()` function wraps `compare()` with a policy.

**Holm.** A step-down FWER correction that is uniformly more powerful
than Bonferroni.

**ICC (intraclass correlation).** The within-cluster correlation. High
ICC means items inside the same cluster move together a lot; low ICC
means they are nearly independent.

**INCONCLUSIVE.** Gate verdict for "not significant *and* the run was
too small to detect the requested minimum effect". The right answer is
to collect more data, not to ship and not to give up.

**Inspect AI.** An eval framework from UK AISI. EVALSIG reads its
`.eval` log format directly.

**Item.** One scored unit in the eval. A question, a problem, a
prompt-response pair.

**Item id (item_id).** The identifier that lines up the same item
across two runs. EVALSIG pairs runs by item id.

**lm-evaluation-harness.** EleutherAI's eval framework, the de facto
OSS standard. EVALSIG reads its `samples_*.jsonl` files.

**McNemar's test.** A paired test for binary outcomes. Counts the
discordant pairs and tests whether the two directions are equally
likely.

**MDE (minimum detectable effect).** The smallest true effect your run
could have detected at the requested power, given alpha and the
observed SD.

**Method.** Which statistical test produced the result. EVALSIG can
auto-pick or you can pass `--method` explicitly.

**Min-delta (min_delta).** The release policy: the smallest effect you
care about. Used by `gate()` to decide REJECT vs ALLOW even when the
result is significant.

**One-sided.** A test where you only count one direction (e.g. only B
better than A) as a rejection. Halves the alpha relative to a two-sided
test.

**Paired / paired difference.** Comparing two runs on the same items
and testing the mean of `b - a` rather than comparing means of `a` and
`b` separately.

**Permutation test.** A non-parametric test built by shuffling labels
(or signs, for paired) many times and counting how often a shuffled
statistic is as extreme as the observed one.

**Power.** Probability that the test fires when there is a real effect.
`Power = 1 - beta`.

**Required N.** The number of items you need to detect a given target
delta at the requested alpha and power.

**RunFrame.** EVALSIG's canonical in-memory and on-disk shape for one
model's run on one task.

**Run id (run_id).** The identifier for one full run (one model, one
task, one configuration). Distinct from item id, which is per-item.

**SD of the paired difference (sd_diff).** The standard deviation of
the per-item difference `b - a`. The main driver of MDE for paired
tests.

**Sequential gate.** Same as the regular gate but the alpha guarantee
holds at every sample size you check. Useful when you want to stop a
run early.

**Significant.** Conventional shorthand for "p-value < alpha". EVALSIG
also requires the delta to point in the requested direction when the
test is one-sided.

**Store.** EVALSIG's optional append-only Parquet history of runs and
verdicts. The CLI `history` subcommand queries it.

**Verdict.** The output of the gate: ALLOW, REJECT, or INCONCLUSIVE.
Mapped to exit codes 0, 1, 2.
