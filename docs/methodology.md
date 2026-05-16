# Methodology

This page is the long-form story behind EVALSIG: why the package
exists, which papers it borrows from, and how we validated the claims
in code.

## The pain in numbers

* **Item-level noise.** Apple's GSM-Symbolic showed up to 65pp accuracy
  drops from adding an irrelevant clause to a math problem with the
  same answer (Mirzadeh et al., 2024). Zhao et al. (2021) showed
  swapping two few-shot examples drops accuracy from 88.5% to 51.3%.
* **Infrastructure noise.** Anthropic Engineering (March 2025)
  quantified a 6pp p<0.01 swing on Terminal-Bench 2.0 from resource
  config alone, and 1.54pp on SWE-bench from 5x RAM. Even at
  temperature 0, batch size and kernel fusion produce stochastic
  outputs (arXiv:2408.04667; Thinking Machines, 2025).
* **No paired inference.** Miller (2024, "Adding Error Bars to Evals")
  shows frontier models correlate 0.3 to 0.7 question-to-question.
  Paired analysis gives 2 to 4 times lower variance for free.

Despite all this, every commercial eval tool we surveyed in May 2026
stopped at "bootstrap CI on a single run". Inspect AI is the only
one that ships clustered SE.

## What EVALSIG implements

| Feature | EVALSIG | lm-eval | Inspect AI | HELM | OpenAI Evals | Promptfoo | Braintrust | LangSmith | Galileo | Patronus | W&B Weave | Vellum | HoneyHive |
|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| Bootstrap CI | yes | partial | yes | per-scenario | no | no | side-by-side | no | no | no | no | no | no |
| Clustered SE | yes | no | yes | no | no | no | no | no | no | no | no | no | no |
| Paired test | yes | no | no | no | no | no | no | no | no | no | no | no | no |
| Permutation | yes | no | no | no | no | no | no | no | no | no | no | no | no |
| MDE / power | yes | no | no | no | no | no | no | no | no | no | no | no | no |
| Sequential | yes | no | no | no | no | no | no | no | no | no | no | no | no |
| Multiplicity | yes | no | no | no | no | no | no | no | no | no | no | no | no |

## Validation

The `research/validate.py` script runs four Monte Carlo experiments
that, together, confirm EVALSIG does what the design doc promises.
Total runtime under 30 seconds on a laptop.

### E1: paired inference beats unpaired Welch

* **Setup**: 400 simulations, 500 items each, true lift 1.5pp, shared
  per-item luck (the regime Miller cites).
* **Result**: paired permutation power 85.8%, unpaired Welch power
  0.0%. Same data, same effect.

### E2: cluster bootstrap controls Type-I under clustering

* **Setup**: 600 simulations under the null, 50 clusters of 10 items,
  mean within-cluster correlation 0.71.
* **Result**: naive item-level bootstrap rejects 43.2% of the time
  (target 5%). Cluster bootstrap rejects 5.5%.

### E3: MDE matches the empirical detection rate

* **Setup**: `sd_diff = 0.4`, `n = 1000`, alpha = 0.05, target power
  80%. Computed MDE = 0.0315. Then 500 simulations with the true
  effect equal to that MDE.
* **Result**: empirical detection rate 81%, within 1pp of the target.

### E4: CLI release gate end-to-end

* **infra-noise** (6,000 items, two configs of the same model):
  REJECT (delta -0.30pp, p = 0.78, MDE 1.00pp).
* **real-improvement** (2,000 items, 2.5pp true lift): ALLOW (delta
  +2.95pp, p = 0.0002, MDE 0.94pp).
* **underpowered** (80 items, 2.5pp true lift): INCONCLUSIVE (delta
  +6.25pp, p = 0.23, MDE 16.75pp). The gate suggests collecting ~9,899
  more items.

Reproduce with:

```bash
python research/validate.py
```

## Why this is hard to copy

The statistics is well known. The literature is mature. So why
doesn't every eval vendor ship this already? Three reasons:

1. **It is dull.** Implementing bootstrap CIs, McNemar, cluster
   bootstraps, and an MDE planner is not a sexy roadmap item. The
   teams that would do it are usually doing something else.
2. **It requires giving up the easy headline.** A statistically
   defensible release gate refuses some releases that would have
   shipped under a naive comparison. Vendors do not love saying
   "actually, your improvement is not significant".
3. **It crosses team lines.** The eval runner, the dashboard, the CI
   gate, the audit trail, and the SaaS billing are usually separate
   products with separate roadmaps. EVALSIG is the thin layer that
   joins them.

## References

1. Anthropic Engineering, "Quantifying infrastructure noise in agentic
   coding evals," March 2025.
2. Mirzadeh et al., "GSM-Symbolic: Understanding the Limitations of
   Mathematical Reasoning in LLMs," Apple ML Research, Oct 2024.
3. Zhao et al., "Calibrate Before Use: Improving Few-Shot Performance
   of Language Models," ICML 2021.
4. "Non-Determinism of Deterministic LLM Settings," arXiv:2408.04667.
5. Thinking Machines, "Defeating Nondeterminism in LLM Inference,"
   2025.
6. Miller, "Adding Error Bars to Evals: A Statistical Approach to
   Language Model Evaluations," arXiv:2411.00640.
7. Howard, Ramdas, McAuliffe, Sekhon, "Time-uniform, nonparametric,
   nonasymptotic confidence sequences," Annals of Statistics, 2021.
8. Liang et al., "Holistic Evaluation of Language Models" (HELM),
   arXiv:2211.09110.
9. Benjamini, Hochberg, "Controlling the False Discovery Rate: A
   Practical and Powerful Approach to Multiple Testing," JRSS-B,
   1995.
