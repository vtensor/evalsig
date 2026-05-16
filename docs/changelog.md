# Changelog

EVALSIG follows [Semantic Versioning](https://semver.org/). The current
line is 0.x, which means anything tagged `*.minor.*` may include
breaking changes; we will flag them clearly when they happen.

## 0.1.0 (2026-05-17)

Initial release. This is the version the design doc was written
against; every "Goals v1" item is shipped except as noted.

### Library

* `evalsig.types`: ItemResult, RunFrame, ComparisonResult, MDEResult.
* `evalsig.exceptions`: typed error hierarchy.
* `evalsig.inference.paired`: paired t-test, paired permutation,
  paired bootstrap.
* `evalsig.inference.unpaired`: Welch's t-test, two-sample
  permutation, two-sample bootstrap.
* `evalsig.inference.mcnemar`: exact-binomial and chi-squared-with-
  continuity branches.
* `evalsig.inference.cluster_bootstrap`: block bootstrap over the
  cluster id.
* `evalsig.inference.mde`: closed-form MDE, required-N inverse,
  one-way-ANOVA ICC estimator.
* `evalsig.inference.power`: power-for-delta under both fixed and
  clustered designs.
* `evalsig.inference.effect_size`: Cohen's d, paired Cohen's d,
  Cliff's delta.
* `evalsig.inference.sequential`: Howard 2021 asymptotic confidence
  sequence; streaming `sequential_gate`.
* `evalsig.inference.multiplicity`: Bonferroni, Holm, Benjamini-
  Hochberg.
* `evalsig.compare.compare`: orchestration with auto-method selection.
* `evalsig.compare.gate`: ALLOW / REJECT / INCONCLUSIVE state machine
  with required-N suggestions.
* `evalsig.compare.report`: JSON, Markdown, and TTY renderers.

### I/O and store

* `evalsig.io.json_runframe`: read/write the canonical EVALSIG JSON
  schema.
* `evalsig.io.lm_eval`: read EleutherAI's `samples_*.jsonl`.
* `evalsig.io.inspect_log`: read Inspect AI JSON exports.
* `evalsig.io.helm`: read HELM `scenario_state.json`.
* `evalsig.io.parquet`: read/write the canonical Parquet schema.
* `evalsig.io.base`: Reader protocol and a small format registry.
* `evalsig.store`: append-only writer, manifest, and read/query API.

### CLI

* `evalsig compare`, `evalsig gate`, `evalsig mde`, `evalsig watch`,
  `evalsig doctor`, `evalsig history`, `evalsig version`.
* `--output {tty,json,markdown}` on every result-producing command.
* BSD sysexits-style exit codes.

### Integrations

* `evalsig.integrations.pytest_plugin`: `evalsig_gate` fixture with
  `assert_no_regression`.
* `evalsig.integrations.github_action`: the entry point used by the
  shipped GitHub Action (`action.yml`).
* `evalsig.integrations.braintrust`: optional Braintrust publisher.
* `evalsig._telemetry`: opt-in local usage log (off by default).

### Tests

* 45 unit tests covering every primitive (paired, unpaired, mcnemar,
  cluster bootstrap, MDE/power, effect sizes, multiplicity, sequential
  testing, the store, the IO layer, the report renderers, the CLI,
  and the pytest plugin).
* 4 end-to-end Monte Carlo experiments in `research/validate.py`.
  All pass on each release.

### Known omissions

* Sphinx-style reference pages are not auto-generated yet; the
  per-module docs in `docs/modules/` are hand-written.
* The SaaS dashboard, billing, and the closed-source ingestion layer
  are tracked in a separate repo.
