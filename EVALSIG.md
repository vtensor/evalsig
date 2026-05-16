# EVALSIG — Design Doc

| | |
|---|---|
| **Status** | Draft v1 |
| **Author** | Vikram Dev |
| **Date** | 2026-05-16 |
| **Reviewers** | TBD |
| **Repository** | `github.com/vtensor/evalsig` (planned) |
| **Implementation target** | Q3 2026 |

---

## 1. TL;DR

EVALSIG is a Python library + CLI + SaaS that sits between any LLM eval harness (Inspect AI, lm-evaluation-harness, HELM, simple-evals, internal pipelines) and the release decision. It applies the statistical methods the academic literature already recommends but no commercial tool ships end-to-end: **paired-difference testing, clustered standard errors, permutation tests, minimum-detectable-effect (MDE) / power analysis, and always-valid sequential monitoring**.

The pitch in one sentence: **frontier labs ship model updates on 1–3 percentage-point eval deltas, and Anthropic themselves measured 6pp swings on Terminal-Bench from infrastructure config alone [1]. EVALSIG is the release gate that distinguishes those two.**

OSS-free Python package gates CI builds. Paid SaaS owns the longitudinal dataset of `(run_conditions × scores × deltas)` and the dashboards. Reference customers: foundation model labs (credibility), AI safety institutes (procurement-driven), enterprise AI product teams (the SaaS buyer).

---

## 2. Problem

### 2.1 The pain

LLM evals are noisy, and the field reports point deltas as if they were signals.

1. **Item-level noise.** Apple's GSM-Symbolic showed up to **65pp accuracy drops** from adding an irrelevant clause to a math problem with the same answer [2]. Zhao et al. (ICML 2021) showed swapping two few-shot examples drops accuracy from 88.5% to 51.3% [3].
2. **Infrastructure noise.** Anthropic published a 6pp (p<0.01) swing on Terminal-Bench 2.0 from resource config alone, and 1.54pp on SWE-bench from 5× RAM [1]. Even at temperature=0, batch size and kernel fusion produce stochastic outputs [4][5].
3. **No paired inference.** Frontier models correlate 0.3–0.7 question-to-question. Comparing two models on the same items has 2–4× lower variance than independent samples. The literature calls this "free variance reduction" [6]. Zero commercial eval tools ship it.
4. **No clustered SE.** Most public benchmarks have items grouped by passage, problem stem, or template. Naive SE under-counts variance by **>3×** in those cases [6]. Inspect AI ships `cluster=` as the only exception in the entire field.
5. **No MDE.** Practitioners ask "I see a 1.2pp delta — is it real?" The honest answer requires power analysis given α, β, observed SD, and cluster structure. No commercial tool tells them how many items they would have needed to detect 1.2pp at 80% power.

### 2.2 Evidence the gap is open

Surveyed every credible eval tool in May 2026. The matrix:

| Tool | Bootstrap CI | Clustered SE | Paired test | Permutation | MDE/Power | Sequential |
|------|:---:|:---:|:---:|:---:|:---:|:---:|
| lm-evaluation-harness (EleutherAI) | acc_stderr only | ❌ | ❌ | ❌ | ❌ | ❌ |
| Inspect AI (UK AISI) | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| HELM (Stanford CRFM) | ✅ (per-scenario) | ❌ | ❌ | ❌ | ❌ | ❌ |
| OpenAI Evals / simple-evals | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Promptfoo | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Braintrust | side-by-side only | ❌ | ❌ | ❌ | ❌ | ❌ |
| LangSmith / Galileo / Patronus / W&B Weave / Vellum / HoneyHive | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| DeepEval / RAGAS | per-test scores | ❌ | ❌ | ❌ | ❌ | ❌ |

**The whole field maxes out at "bootstrap CI on a single run."** Inspect AI alone ships clustered SE. Nobody ships paired-difference inference, permutation tests, MDE/power, or sequential testing. The academic recipes have been public for 18+ months and remain unimplemented commercially.

### 2.3 Why now

- **Anthropic Nov 2024** publishes Miller's "Adding Error Bars to Evals" with five specific recommendations [6]; **Anthropic Engineering Mar 2025** quantifies infra noise on agentic evals [1].
- **Apple GSM-Symbolic Oct 2024** [2] makes benchmark-noise discussion mainstream.
- **Braintrust $80M Series B Feb 2026 at $800M valuation** [7] proves the eval-tooling market is real money.
- **Continued benchmark contamination scandals** in 2025–2026 push enterprise AI buyers to demand statistically defensible release gates.

The wedge is statistics, the literature is mature, and the budget exists.

---

## 3. Goals and Non-Goals

### 3.1 Goals (v1)

1. **Paired-difference inference** for two-model comparisons on the same item set (paired t, paired permutation, paired bootstrap, McNemar for binary).
2. **Clustered standard errors** with configurable cluster key (passage_id, template_id, stem_id, etc.).
3. **Minimum-detectable-effect** calculator: given α, β, observed pooled SD, cluster structure, return the smallest delta a run can detect, *and* the inverse: given desired MDE, return the required N.
4. **Bootstrap CI** with cluster-bootstrap mode.
5. **Permutation tests** (single-run and paired) as exact-inference fallback when distributional assumptions are shaky.
6. **Sequential / always-valid monitoring** via e-values, so labs can stop early without α inflation when running expensive evals.
7. **One CLI invocation gates CI.** Exit non-zero when `model_b - model_a` is not statistically significantly positive at requested MDE, α, power.
8. **Read native Inspect AI `.eval` logs.** Read lm-eval-harness JSON. Read a documented EVALSIG JSON Schema for everything else.
9. **Append-only run history** (Parquet) with a stable schema.
10. **SaaS dashboard** (private repo) for run history, regression patterns, flakiness trends.

### 3.2 Non-goals (v1)

- We don't run the eval. We don't host the model. We don't grade outputs.
- We don't build new task suites. We don't reproduce MMLU/GPQA.
- We don't ship LLM-as-judge models. (That's Patronus's lane.)
- We don't ship a tracing system. (That's Phoenix's lane.)
- We don't try to "explain" why the regression happened. We tell you *whether it exists*.

### 3.3 Explicit anti-features

- **No "score everything for you" feature.** Vendor-graded eval is a different market. Conflating them would split focus.
- **No GPU dependency in the core library.** Pure NumPy/SciPy. Statistics has been GPU-free for 50 years.
- **No mandatory cloud.** OSS works fully offline. SaaS is the optional dashboard, not the engine.

---

## 4. Personas and ICP

| Persona | Pain | Lever EVALSIG pulls | Buys? |
|---|---|---|---|
| **Frontier-lab researcher** (Anthropic, OpenAI, AISI, METR) | Reviewers ask "is this delta real?" | Library API. CI gate. | OSS user. Credibility flywheel. |
| **AI safety institute** (UK AISI, US AISI, METR) | Defensible third-party-grade inference | Library + dedicated cluster-aware tests | Procurement-grade SaaS or self-host license |
| **Enterprise AI product team** (fintech, med, legal, defence) | Vendor ships a model update; do we promote? | CLI gate in CI. SaaS dashboards for compliance audit trail. | **Primary SaaS buyer.** $5–50K/yr |
| **AI-first scaleup doing RLHF/finetune loops** (Replit, Cursor, Perplexity-class) | Telling fine-tune wins from noise | Plugin into Braintrust / LangSmith | Add-on SaaS, $249/mo tier |

**Where the money is**: enterprise AI product teams. They already accept eval deltas from vendors without statistical backing. They have compliance and audit requirements. They can articulate a release-gate budget the way they articulate a unit-test budget.

---

## 5. Competitive Landscape

### 5.1 Harnesses (eval runners, not stats engines)

- **lm-evaluation-harness (EleutherAI)** — the de facto OSS harness, 200+ tasks, plugin via `@register_model`/`@register_filter`, YAML task configs, results JSON with `acc_stderr` [GitHub](https://github.com/EleutherAI/lm-evaluation-harness). Stats stop at bootstrap stderr. **EVALSIG reads its JSON output.**
- **Inspect AI (UK AISI)** — best-engineered framework in the field. `dataset → Task → Solver → Scorer` primitives, `.eval` log format with published schema, native `bootstrap_stderr()` and `cluster=` kwarg [Inspect docs](https://inspect.aisi.org.uk/). **EVALSIG ingests its `.eval` files as a first-class input.**
- **HELM (Stanford CRFM)** — research-grade, bootstrap CIs per scenario, no paired or power machinery [arXiv:2211.09110](https://arxiv.org/abs/2211.09110).
- **OpenAI Evals / simple-evals** — minimal repros, zero stats.
- **Promptfoo** — pass/fail in CI, no stats.
- **Lighteval (HF)** — backs Open LLM Leaderboard, no stats layer.

### 5.2 Platforms (SaaS observability + eval)

- **Braintrust** — $124M raised, $800M valuation [7]. Strong dataset versioning + side-by-side. **No paired tests, no MDE.** They will likely build this eventually; EVALSIG ships now.
- **LangSmith** — strong on tracing, weak on inference.
- **Patronus** — sells evaluator-models-as-a-service. Different layer.
- **Galileo** — Series B $45M, proprietary "Luna" small-LM evaluators. Different layer.
- **Arize Phoenix / W&B Weave / Vellum / HoneyHive** — tracing-first.

### 5.3 Eval libraries (metric computation)

- **DeepEval / Confident AI** — "pytest for LLMs", flagship `G-Eval` LLM-as-judge. No aggregate inference.
- **RAGAS** — reference-free RAG metrics. Same.

### 5.4 The gap, in one sentence

**Every player today computes scores; nobody computes whether two scores differ, with proper inference, at scale, in CI.**

EVALSIG owns that wedge because (a) the statistics is hard enough that nobody has bothered, (b) the academic literature has crystallised into a checklist, (c) the buyers exist and are paying $50K+/yr to incumbents that don't solve this.

---

## 6. Product Surface

### 6.1 Library API

```python
from evalsig import EvalRun, compare, mde, paired_permutation_test
from evalsig.io import read_inspect_log, read_lm_eval_json

# Load runs from any source
run_a = read_inspect_log("baseline.eval")
run_b = read_inspect_log("candidate.eval")

# Paired difference with clustered SE
result = compare(
    run_a, run_b,
    method="paired_permutation",  # or "paired_t" | "paired_bootstrap" | "mcnemar"
    cluster="passage_id",
    alpha=0.05,
    one_sided=True,                # candidate > baseline
    n_resamples=10_000,
    rng=42,
)

print(result.delta)         # 0.0124  (1.24 pp)
print(result.ci)            # (-0.003, 0.027) at 95%
print(result.p_value)       # 0.082
print(result.significant)   # False
print(result.mde)           # 0.018  (we could only detect ≥1.8pp at 80% power)
```

### 6.2 CLI / CI gate

```bash
# Lint-style exit codes; non-zero = release blocked.
evalsig gate \
  --baseline baseline.eval \
  --candidate candidate.eval \
  --metric accuracy \
  --cluster passage_id \
  --min-delta 0.005 \
  --alpha 0.05 \
  --power 0.80 \
  --method paired_permutation \
  --json report.json
```

Output:

```
EVALSIG release gate
====================
metric:        accuracy
baseline:      0.6841  (n=4,032, c=1,008 clusters)
candidate:     0.6965
delta:         +0.0124 (paired)
p-value:       0.082 (paired permutation, 10,000 resamples)
required MDE:  0.005
detectable:    0.018 at 80% power

VERDICT: REJECT  candidate is not significantly better than baseline at requested MDE.
Suggestion: collect 12,400 more items (estimated) to reach 0.005 MDE at 80% power.
```

### 6.3 SaaS dashboard (paid)

- Run history per project (timeline of model_id × eval_id × delta with CIs).
- Flakiness panel (variance per task across "no-op" reruns).
- Power-decay panel (MDE drifting up as you reuse the same items — contamination signal).
- Regression patterns ("model_B drops on cluster=passage_45 in 7/10 reruns").
- Compliance export: signed JSON snapshot per release decision.

---

## 7. Architecture

```
  [ Harnesses (third-party) ]
    Inspect AI    lm-eval-harness    HELM    simple-evals    YAML
                       |
                       |  .eval / json / parquet
                       v
  [ evalsig.io ]
    Readers normalise everything into a single shape (RunFrame).
                       |
                       v
  [ evalsig.inference ]
    paired_t, paired_perm, paired_bootstrap, cluster_bootstrap,
    mcnemar, mde, power, sequential, effect_size.
                       |
                       v
  [ evalsig.cli ]  ->  exit code + JSON report
                       |
                       v
  [ evalsig.store ]  (optional)  ->  Parquet / S3 / DuckDB
                       |
                       v
  [ SaaS layer ]   ->  Postgres + S3 + dashboards (closed source)
```

The diagram is the whole product. Each box is one Python module with one responsibility (single-responsibility principle, applied at the module boundary).

---

## 8. Code Structure

Single PyPI package `evalsig`. Google-style layout: shallow, intentional, modules are nouns, files inside are verbs or types. No `utils.py` (always wrong).

```
evalsig/
  pyproject.toml
  README.md
  LICENSE                              # Apache-2.0 for the open-source core
  docs/                                # Sphinx + Diataxis layout
    concepts.md
    tutorials/
    reference/                         # auto-generated from docstrings
    methodology.md                     # the academic case
  examples/
    compare_two_inspect_runs.py
    ci_release_gate.py
    mde_for_target_delta.py
  tests/
    unit/
      test_paired_t.py
      test_paired_permutation.py
      test_cluster_bootstrap.py
      test_mde.py
      test_mcnemar.py
      test_io_inspect.py
    property/                          # Hypothesis-based property tests
      test_paired_invariants.py
      test_bootstrap_coverage.py       # Monte Carlo checks 95% CI covers 95%
    golden/                            # frozen outputs vs. R and statsmodels
      paired_t_against_R.json
      mcnemar_against_statsmodels.json
      permutation_against_coin.json
    e2e/
      test_cli_gate.py
  benches/                             # pytest-benchmark for perf budget
    bench_paired_permutation.py
  src/evalsig/
    __init__.py                        # re-exports the public API
    _version.py
    types.py                           # RunFrame, ItemResult, ComparisonResult, MDEResult
    exceptions.py                      # EvalsigError hierarchy
    logging.py                         # structlog config

    io/                                # ingestion
      __init__.py
      base.py                          # Reader protocol; entry-point registry
      inspect_log.py                   # reads .eval (Inspect AI)
      lm_eval.py                       # reads lm-evaluation-harness JSON
      helm.py                          # reads HELM scenario state
      parquet.py                       # reads/writes the canonical Parquet
      json_schema.py                   # public EVALSIG JSON Schema definition
      normalize.py                     # turns mixed inputs into a RunFrame

    inference/                         # statistics core (pure NumPy/SciPy)
      __init__.py
      _checks.py                       # input validation (paired alignment, dtypes)
      _rng.py                          # numpy.random.Generator factory + seeds
      paired.py                        # paired_t, paired_permutation, paired_bootstrap
      unpaired.py                      # two_sample_t, perm, bootstrap (fallback only)
      mcnemar.py                       # binary outcomes
      cluster_bootstrap.py             # block bootstrap on cluster id
      effect_size.py                   # Cohen's d, Cliff's delta, paired-d
      mde.py                           # given (alpha, beta, sd, rho), return MDE
      power.py                         # given (delta, alpha, beta, sd, rho), return N
      sequential.py                    # e-values / always-valid bounds
      multiplicity.py                  # Holm, BH-FDR, Bonferroni for multi-task gates

    compare/                           # orchestration over inference primitives
      __init__.py
      compare.py                       # the top-level `compare()` function
      gate.py                          # release-gate state machine
      report.py                        # ComparisonResult to JSON / Markdown / TTY

    store/                             # run history (Parquet, optional)
      __init__.py
      schema.py                        # the public Parquet schema
      writer.py                        # append-only writer with manifest
      reader.py                        # PyArrow-based, with predicate pushdown
      manifest.py                      # version and run lineage

    cli/                               # Click app
      __init__.py
      main.py                          # entry point
      compare.py                       # `evalsig compare`
      gate.py                          # `evalsig gate`
      mde.py                           # `evalsig mde`
      history.py                       # `evalsig history`
      doctor.py                        # `evalsig doctor` (schema validation)

    integrations/                      # optional helpers
      __init__.py
      pytest_plugin.py                 # @pytest.mark.evalsig fixture
      github_action.py                 # entry point for the published Action
      braintrust.py                    # publish ComparisonResult to Braintrust runs

    _telemetry/                        # opt-in usage counters, off by default
      __init__.py
      client.py
```

### 8.1 Why this layout

- **Modules are nouns.** `inference`, `io`, `compare`, `store`, `cli`. Each is exactly one responsibility.
- **Files inside modules are concrete tests or types.** No `helpers.py`, no `misc.py`. If a thing doesn't fit a noun, it doesn't exist yet.
- **`inference` is a leaf module.** It depends on nothing but NumPy/SciPy. This is the testability promise — the math is decoupled from the world. Property tests verify each estimator's coverage with Monte Carlo; golden tests pin numeric outputs against R (`coin`, `boot`) and statsmodels.
- **`compare` orchestrates inference.** Never the reverse. Dependency direction: `cli → compare → inference`. Never `inference → compare`. (Dependency-inversion principle.)
- **`store` is optional.** OSS works without it. SaaS reads/writes it.
- **`io` ingests, `compare` reasons, `store` persists, `cli` presents.** Onion architecture.

### 8.2 Public API surface

Exactly three top-level names you import 80% of the time:

```python
from evalsig import compare, gate, mde
```

Power users reach into `evalsig.inference.*` for individual estimators. Everything else is implementation detail.

---

## 9. Module Designs

### 9.1 `evalsig.types`

```python
from pydantic import BaseModel
from typing import Optional, Sequence

class ItemResult(BaseModel):
    item_id: str
    cluster_id: Optional[str] = None
    epoch: int = 0
    score: float                  # 0/1 for binary, otherwise scalar
    metadata: dict = {}

class RunFrame(BaseModel):
    """Canonical IR for one model's run on one task."""
    run_id: str
    model_id: str
    task_id: str
    metric_name: str
    items: Sequence[ItemResult]   # not Pandas — pure typed records
    config_hash: str              # stable hash of (model, params, harness version)

class ComparisonResult(BaseModel):
    delta: float
    ci: tuple[float, float]
    ci_level: float
    p_value: float
    significant: bool
    n_pairs: int
    n_clusters: Optional[int]
    method: str                    # "paired_permutation", etc.
    mde: float                     # minimum detectable effect at requested power
    notes: list[str] = []          # warnings / caveats
```

These are the only data classes that cross module boundaries. They are **immutable**, **versioned**, **JSON-Schema-emitting**.

### 9.2 `evalsig.inference`

The hot path. Pure functions. NumPy arrays in, dataclass out. No I/O.

Contract example:

```python
def paired_permutation_test(
    scores_a: np.ndarray,            # shape (n,)
    scores_b: np.ndarray,            # shape (n,)
    *,
    cluster_id: np.ndarray | None,   # shape (n,)
    alternative: str = "greater",
    n_resamples: int = 10_000,
    rng: np.random.Generator,
) -> PairedPermutationOutcome: ...
```

Why this signature:

- **Keyword-only past 2 positionals.** Reading at a callsite is easy.
- **`rng` is required.** No global state, no implicit seeding, fully reproducible across machines.
- **`cluster_id` is `np.ndarray | None`, not a sentinel string.** Static typing catches misuse.
- **Returns a dataclass, not a tuple.** Adding new outputs is non-breaking.
- **No DataFrame in the math layer.** DataFrames are I/O.

### 9.3 `evalsig.compare`

Orchestration. Picks the right inference primitive given input types:

```python
def compare(
    a: RunFrame,
    b: RunFrame,
    *,
    method: Literal["auto", "paired_t", "paired_permutation",
                    "paired_bootstrap", "mcnemar"] = "auto",
    cluster: str | None = None,
    alpha: float = 0.05,
    one_sided: bool = False,
    n_resamples: int = 10_000,
    rng: int | np.random.Generator = 0,
) -> ComparisonResult: ...
```

`method="auto"` picks: binary scores → McNemar; ≤30 paired observations or non-Gaussian → paired permutation; else paired bootstrap (more robust than paired t for heavy tails).

### 9.4 `evalsig.cli`

Click + Rich. One command per verb (`compare`, `gate`, `mde`, `history`, `doctor`). Every command emits machine-readable JSON via `--json` and human-readable TTY otherwise. CI integration is `evalsig gate ... --json report.json` and parsing the exit code.

Exit codes:
- `0` — release allowed (significant improvement at requested MDE)
- `1` — release rejected (not significant)
- `2` — inconclusive (underpowered run; suggest more items)
- `64` — usage error (bad CLI args)
- `65` — data error (schema validation failure, misaligned pairs)
- `70` — internal error (please file a bug)

These map to BSD sysexits.h conventions, which CI systems already understand.

### 9.5 `evalsig.store`

Append-only Parquet, partitioned by `project_id / year=YYYY / month=MM`. PyArrow native. The schema is published as a stable JSON Schema so third parties can write directly.

Storage layout per file:

```
{project}/{year}/{month}/{run_id}.parquet
{project}/manifest.json   # the run lineage: which run_id descended from which
```

A `manifest.json` per project lets `evalsig history` ask "show me every run on task=mmlu, model=claude-4.x, between 2026-01 and 2026-05" with zero scanning of irrelevant Parquet files.

### 9.6 `evalsig.integrations.pytest_plugin`

```python
def test_no_regression(evalsig_gate):
    a = evalsig_gate.load("baseline.eval")
    b = evalsig_gate.load("candidate.eval")
    evalsig_gate.assert_no_regression(a, b, metric="accuracy", min_delta=0.005)
```

Familiar API. Bridges to existing CI without touching the harness.

---

## 10. Data Model

### 10.1 Canonical RunFrame schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "EVALSIG RunFrame v1",
  "type": "object",
  "required": ["run_id", "model_id", "task_id", "metric_name", "items", "config_hash"],
  "properties": {
    "run_id":      {"type": "string"},
    "model_id":    {"type": "string"},
    "task_id":     {"type": "string"},
    "metric_name": {"type": "string"},
    "items": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["item_id", "score"],
        "properties": {
          "item_id":    {"type": "string"},
          "cluster_id": {"type": ["string", "null"]},
          "epoch":      {"type": "integer", "minimum": 0},
          "score":      {"type": "number"},
          "metadata":   {"type": "object"}
        }
      }
    },
    "config_hash": {"type": "string", "pattern": "^[a-f0-9]{16,64}$"}
  }
}
```

Published at `https://evalsig.dev/schemas/run.v1.json`. Versioned. Backward-compatible additions only past v1.

### 10.2 On-disk Parquet schema

| column | type | nullable | notes |
|---|---|:---:|---|
| project_id | string | no | dictionary-encoded |
| run_id | string | no | uuid7 |
| model_id | string | no | |
| task_id | string | no | |
| metric_name | string | no | |
| item_id | string | no | |
| cluster_id | string | yes | |
| epoch | int32 | no | 0 if single-shot |
| score | float64 | no | |
| config_hash | string | no | |
| ts | timestamp[us, UTC] | no | when item was scored |
| metadata | string (JSON) | yes | overflow bucket |

Long format, one row per `(run, item, epoch)`. Predicate pushdown on `(project_id, task_id, model_id)` is cheap. Storage cost @ 100M items: ~3GB compressed.

---

## 11. Performance Budget

| Operation | Budget |
|---|---|
| Read `.eval` (10K items) | < 200ms |
| Paired permutation, 10K items, 10K resamples | < 5s on a laptop |
| Cluster bootstrap, 10K items × 1K clusters × 5K resamples | < 8s |
| MDE calculation, closed form | < 10ms |
| `evalsig gate` end-to-end | < 10s for 10K items |

Vectorise resampling with NumPy advanced indexing. Avoid Python loops on the inner loop. JIT only if profiling demands; `numba` is allowed but not required (it complicates wheels and we want zero-friction install).

For runs >1M items, switch to chunked Parquet read + per-chunk resample with stratified aggregation. Sequential / e-value tests are O(1) per arriving item, by design.

---

## 12. Scalability

### 12.1 OSS path (single-process)

Up to 1M items comfortably. Above that, users batch by `cluster_id` and the cluster bootstrap parallelises naturally over CPU cores via `concurrent.futures.ProcessPoolExecutor`.

### 12.2 SaaS path

- **Ingest**: HTTPS POST a `RunFrame` JSON, or background-poll an S3 bucket. Validate against `run.v1.json`. Reject on schema violation with 422 + line-level errors.
- **Storage**: S3 for raw Parquet; DuckDB for ad-hoc analytic queries against the lake; Postgres for run metadata, projects, users, tokens.
- **Compute**: Stateless workers. Each `compare` is independent; horizontal scaling is "more workers." Long-running cluster bootstraps go to a job queue (RQ on Redis, no Celery).
- **Dashboards**: Read-only views on the Parquet lake via DuckDB-WASM in the browser for the lighter queries; server-side DuckDB for joins across projects.

### 12.3 Capacity targets, year 1

- 200 paying customers
- 50K runs/month
- 1B items/month under management
- Comfortably one `t3.large` worker pool + one Aurora Serverless v2 + 1TB S3

### 12.4 Multitenancy

Postgres row-level security keyed by `project_id`. S3 paths prefixed by `org_id/`. Workers carry an org token in context; readers validate before any compute.

---

## 13. Reliability and Failure Modes

| Failure | Detection | Mitigation |
|---|---|---|
| Misaligned paired runs (different `item_id` sets) | `_checks.py` validates intersection ≥ 95% of either run before computing | Reject with explicit error listing missing items |
| Cluster ID present on one side, absent on other | Schema validator | Reject; suggest unclustered fallback |
| All scores identical (no variance) | Inference layer | Return `delta=0, p=1.0, ci=(0,0), significant=False` with a note |
| Heavy-tailed scores breaking paired-t | Auto-method detection routes to permutation | Document why method changed |
| Bootstrap resampling explodes memory | Streamed resampler, configurable `chunk_size` | Default chunk_size=2,048 |
| RNG state inconsistent across machines | Always require `rng` param; never default to module-level RNG | Reproducibility is a feature, not a wish |

Every error is a typed subclass of `EvalsigError`. Never raise generic `ValueError`s past the input-validation boundary.

---

## 14. Security and Privacy

- **OSS core has zero network egress.** No telemetry, no phone-home. `_telemetry/` is opt-in via env var.
- **SaaS data plane**: TLS 1.3, AES-256 at rest, customer-managed KMS keys at Team tier and above.
- **No item content stored by default.** SaaS persists scores + cluster IDs + metadata, not prompts/responses unless customer opts in. This is the privacy-preserving default; eval prompts often contain PII or proprietary domain data.
- **SOC2 Type II** by month 9 of SaaS launch (use Vanta).
- **Schema validation at the edge.** Every input is JSON-Schema-validated before it touches inference. No `eval(...)`-style dynamic dispatch anywhere.

---

## 15. Commercial Packaging

### 15.1 Tier matrix

| Tier | Price | Includes | ICP |
|---|---|---|---|
| **OSS** | Free, Apache-2.0 | Library, CLI, GitHub Action, pytest plugin, Parquet store | Researchers, students, individual devs |
| **Pro** | $39 / dev / mo | OSS + private SaaS dashboards (1 project, 30 days history) | Solo AI engineers, scaleup teams |
| **Team** | $20 / dev / mo, 5-seat min | All Pro + run history (12 months), SSO, audit log, scheduled gate alerts | Mid-market AI product teams |
| **Enterprise** | from $30K / yr | All Team + on-prem deploy, custom retention, SOC2 reports, dedicated CSM, custom rules | Banks, defence, foundation labs |
| **Registry** | from $50K / yr | API access for ingesting third-party run data + branding | Eval-platform partners (Braintrust, LangSmith integrations) |

Pricing anchored to comparable AI-eval SaaS (Braintrust Pro $249, LangSmith Plus $39/seat + traces, Galileo Pro $100, Code Climate $49/user/mo).

### 15.2 GTM motion

1. **OSS first.** Ship library + GitHub Action + a strong methodology doc with all the citations. Submit to Anthropic / OpenAI / AISI eval channels.
2. **One reference customer in AI safety.** AISI or METR or Apollo. Free / heavily discounted in exchange for case study.
3. **Land in enterprise via compliance angle.** "How do you defend a release decision to your AI safety board?" → "Here's a signed JSON report."
4. **Partner integrations.** Plugins for Braintrust, LangSmith, W&B Weave. Co-marketing.
5. **Conference talks.** NeurIPS / ICLR workshops on eval reproducibility. The literature is on our side.

### 15.3 The moat

- **Statistics is a hard, citation-heavy area.** Competitors won't catch up in a quarter.
- **Trust + audit trail.** Once a customer's last six release decisions live in EVALSIG's store, switching is expensive.
- **Schema standardisation.** If `RunFrame v1` becomes the de facto interchange format, every harness integrates with us.

---

## 16. Milestones

| Phase | Scope | Duration |
|---|---|---|
| **M0 — Foundation** | Repo scaffold, `types`, `io.inspect_log`, `io.lm_eval`, `inference.paired_t`, `inference.paired_permutation`, `cli.compare`, golden tests against R. | 4 weeks |
| **M1 — Release Gate** | `inference.cluster_bootstrap`, `inference.mcnemar`, `inference.mde`, `inference.power`, `compare.gate`, GitHub Action, pytest plugin. Methodology doc. | 4 weeks |
| **M2 — History** | `store` module (Parquet + manifest), `cli.history`, sequential testing (`inference.sequential`). | 4 weeks |
| **M3 — SaaS MVP** | Postgres + S3 ingest, dashboards (Next.js), auth (Clerk), Stripe billing, first 5 design partners. | 8 weeks |
| **M4 — Compliance & GA** | SOC2 prep, signed reports, Braintrust + LangSmith integration plugins, public launch + HN. | 8 weeks |

Total to GA: ~28 weeks. Two-person team. Founder + one senior backend.

---

## 17. SOLID + Engineering Principles Applied

- **S — Single Responsibility.** `inference` does math, `io` does I/O, `store` does persistence, `cli` does presentation. No module owns two concerns.
- **O — Open/Closed.** Adding a new statistical method = new file in `inference/` + new entry in `compare/_methods.py` registry. Zero edits to existing code.
- **L — Liskov.** `Reader` Protocol in `io/base.py`: all readers return `RunFrame`. Swapping readers never breaks consumers.
- **I — Interface segregation.** No god-class `EvalsigClient`. Each module exports the minimum surface its users need.
- **D — Dependency inversion.** `inference` depends on `numpy`, period. It never imports from `io`, `store`, or `cli`. Higher layers depend on `inference`.

Other principles enforced:
- **Pure functions in `inference`.** Easier to test, parallelise, JIT.
- **Immutable data classes.** `ComparisonResult` is `frozen=True`.
- **Explicit RNG.** Reproducibility is a property, not a hope.
- **No global state.** No `evalsig.set_default_alpha(0.05)`. Pass it.
- **Typed everywhere.** `mypy --strict` clean, runtime-checked Pydantic at boundaries.
- **Fail fast at the edge.** JSON Schema validation before any compute.

---

## 18. Open Questions

1. **Naming for sequential testing.** Should `gate` learn an `--sequential` flag, or is that a separate `evalsig watch` command? Lean: separate command, keeps `gate` synchronous.
2. **First harness for ingest beyond Inspect + lm-eval.** HELM is heavyweight; OpenAI simple-evals is small enough to vendor a reader for. Promptfoo is pass/fail and probably out of scope until v2.
3. **LLM-as-judge variance.** When the metric itself is stochastic (G-Eval, Patronus Glider), do we account for that as a second variance component? Likely v2; requires extension of the `ItemResult` schema.
4. **On-prem story for foundation labs.** They will not send eval data to a SaaS. Need a "single-binary deployable" mode for the dashboard. Docker Compose + Postgres + MinIO + Next.js, day one.
5. **Should `store` support DuckDB-native query mode in OSS?** Or keep it Parquet-only and let SaaS do the query layer? Lean: ship a `duckdb://` URL adapter in OSS, no friction.

---

## 19. References

[1] Anthropic Engineering, "Quantifying infrastructure noise in agentic coding evals," Mar 2025. https://www.anthropic.com/engineering/infrastructure-noise
[2] Mirzadeh et al., "GSM-Symbolic: Understanding the Limitations of Mathematical Reasoning in LLMs," Apple ML Research, Oct 2024. https://machinelearning.apple.com/research/gsm-symbolic
[3] Zhao et al., "Calibrate Before Use: Improving Few-Shot Performance of Language Models," ICML 2021. https://arxiv.org/abs/2102.09690
[4] "Non-Determinism of Deterministic LLM Settings," arXiv:2408.04667. https://arxiv.org/html/2408.04667v5
[5] Thinking Machines, "Defeating Nondeterminism in LLM Inference," 2025. https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/
[6] Miller, "Adding Error Bars to Evals: A Statistical Approach to Language Model Evaluations," Anthropic / ICLR 2025 Building Trust Workshop, arXiv:2411.00640. https://arxiv.org/abs/2411.00640. Companion: https://www.anthropic.com/research/statistical-approach-to-model-evals
[7] SiliconANGLE, "Braintrust Lands $80M Series B," Feb 2026. https://siliconangle.com/2026/02/17/braintrust-lands-80m-series-b-funding-round-become-observability-layer-ai/
[8] Maia Polo et al., "tinyBenchmarks: Evaluating LLMs with Fewer Examples," arXiv:2402.14992, 2024. https://arxiv.org/abs/2402.14992
[9] "Efficient Evaluation of LLM Performance with Statistical Guarantees" (FAQ), arXiv:2601.20251, 2026. https://arxiv.org/abs/2601.20251
[10] "Measuring all the noises of LLM Evals," arXiv:2512.21326, 2025. https://arxiv.org/html/2512.21326v1
[11] Liang et al., "Holistic Evaluation of Language Models" (HELM), arXiv:2211.09110. https://arxiv.org/abs/2211.09110
[12] Inspect AI, UK AISI. https://inspect.aisi.org.uk/. Repo: https://github.com/UKGovernmentBEIS/inspect_ai
[13] EleutherAI, lm-evaluation-harness. https://github.com/EleutherAI/lm-evaluation-harness
[14] Braintrust pricing. https://www.braintrust.dev/pricing
[15] LangSmith pricing. https://www.langchain.com/pricing
