# Verification report

This document records the end-to-end verification of EVALSIG 0.1.0
against the design doc ([EVALSIG.md](EVALSIG.md)). It is intended as
the audit-grade artefact that an external reviewer can pull up to
answer "does the library actually do what it claims?".

Reproduce in 30 seconds:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
python -m unittest discover tests
python research/validate.py
```

## Implementation coverage

Every "Goals v1" item in the design doc is implemented in 0.1.0.

| Design-doc feature | Status | Location |
|---|---|---|
| Paired-difference inference (t, permutation, bootstrap, McNemar) | shipped | `evalsig.inference.paired`, `evalsig.inference.mcnemar` |
| Clustered standard errors | shipped | `evalsig.inference.cluster_bootstrap` |
| MDE / power, design-effect correction | shipped | `evalsig.inference.mde`, `evalsig.inference.power` |
| Bootstrap CI (single and cluster) | shipped | `evalsig.inference.paired`, `evalsig.inference.cluster_bootstrap` |
| Permutation tests | shipped | `evalsig.inference.paired`, `evalsig.inference.unpaired` |
| Sequential / always-valid monitoring | shipped | `evalsig.inference.sequential` |
| Multiple-comparison corrections | shipped | `evalsig.inference.multiplicity` |
| Effect sizes (Cohen's d, Cliff's delta) | shipped | `evalsig.inference.effect_size` |
| CLI release gate with sysexits exit codes | shipped | `evalsig.cli.main` |
| Inspect AI `.eval` log reader | shipped | `evalsig.io.inspect_log` |
| lm-eval-harness JSON reader | shipped | `evalsig.io.lm_eval` |
| HELM scenario reader | shipped | `evalsig.io.helm` |
| Canonical RunFrame JSON schema and reader | shipped | `evalsig.io.json_runframe` |
| Append-only Parquet store with manifest | shipped | `evalsig.store` |
| Pytest plugin | shipped | `evalsig.integrations.pytest_plugin` |
| GitHub Action | shipped | `evalsig.integrations.github_action` + `action.yml` |
| Braintrust publisher | shipped (optional dep) | `evalsig.integrations.braintrust` |
| Opt-in local telemetry | shipped | `evalsig._telemetry` |
| Typed exception hierarchy | shipped | `evalsig.exceptions` |
| Logging hook | shipped | `evalsig.logging` |
| JSON / Markdown / TTY renderers | shipped | `evalsig.compare.report` |

Items deferred per the design doc's "Non-goals":

* Building task suites or running models.
* LLM-as-judge.
* Tracing.
* "Explaining why the regression happened" -- only "whether it exists".

## Test inventory

### Unit tests: 45 passing

```text
test_effect_size.TestCohensD.test_known_value
test_effect_size.TestCohensD.test_zero_for_equal_means
test_effect_size.TestCohensDPaired.test_constant_diff_returns_zero
test_effect_size.TestCohensDPaired.test_noisy_lift
test_effect_size.TestCliffsDelta.test_b_strictly_greater
test_effect_size.TestCliffsDelta.test_identical_distributions
test_multiplicity.TestBonferroni.test_caps_at_one
test_multiplicity.TestBonferroni.test_scales_by_m
test_multiplicity.TestHolm.test_more_powerful_than_bonferroni
test_multiplicity.TestHolm.test_step_down
test_multiplicity.TestBenjaminiHochberg.test_controls_fdr_on_mixture
test_multiplicity.TestBenjaminiHochberg.test_known_values
test_sequential.TestConfidenceSequence.test_width_shrinks_with_n
test_sequential.TestConfidenceSequence.test_zero_data_safe
test_sequential.TestSequentialGate.test_does_not_stop_under_null
test_sequential.TestSequentialGate.test_stops_on_real_effect
test_unpaired_extra.TestUnpairedBootstrap.test_ci_covers_true_diff
test_unpaired_extra.TestUnpairedPermutation.test_large_effect_low_p
test_unpaired_extra.TestUnpairedPermutation.test_no_effect_high_p
test_smoke.TestClusterBootstrap.test_widens_ci_under_clustering
test_smoke.TestICC.test_icc_high_for_correlated
test_smoke.TestICC.test_icc_zero_for_iid
test_smoke.TestMDE.test_deff_inflates_required_n
test_smoke.TestMDE.test_required_n_round_trip
test_smoke.TestMcNemar.test_exact_branch_matches_binomtest
test_smoke.TestPairedPermutation.test_big_effect_low_p
test_smoke.TestPairedPermutation.test_zero_effect_high_p
test_smoke.TestPairedT.test_matches_scipy_ttest_rel
test_smoke.TestPower.test_power_at_mde_equals_target
test_store.TestStoreManifestPersists.test_writer_appends_and_reopens
test_store.TestStoreQuery.test_filters_by_model_and_task
test_store.TestStoreRoundTrip.test_write_then_load
test_io_parquet.TestParquetRoundTrip.test_round_trip_preserves_fields
test_io_helm.TestHelmReader.test_reads_success_field
test_io_helm.TestHelmReader.test_cluster_key_pulls_metadata
test_report.TestJsonRenderer.test_valid_json_with_expected_keys
test_report.TestMarkdownRenderer.test_contains_table_and_notes
test_report.TestTTYRenderer.test_no_color_yields_plain_text
test_cli.TestDoctor.test_flags_broken_file
test_cli.TestDoctor.test_validates_clean_file
test_cli.TestGateExit.test_gate_exit_codes
test_cli.TestMDE.test_mde_command
test_cli.TestVersion.test_version_command
test_pytest_plugin.TestEvalsigGateFixture.test_allow_when_lift_real
test_pytest_plugin.TestEvalsigGateFixture.test_raises_when_no_lift
```

### End-to-end validation: 4 / 4 passing

From `research/validate.py`:

| # | Claim | Verdict | Result |
|---|---|---|---|
| E1 | Paired inference gives more power than unpaired Welch on the same data | PASS | Paired 85.8% vs unpaired 0.0% at 1.5pp lift, n=500 |
| E2 | Cluster bootstrap keeps false positives near 5% on grouped data | PASS | Naive 43.2%, clustered 5.5%, target 5% |
| E3 | MDE matches the empirical detection rate | PASS | Computed 0.0315, empirical power 81% vs target 80% |
| E4 | CLI release gate returns the right verdict end-to-end | PASS | infra-noise -> REJECT, real-improvement -> ALLOW, underpowered -> INCONCLUSIVE |

## Reproducibility

* All inference primitives accept an explicit RNG. No globals.
* The validation script seeds every experiment.
* Test seeds are pinned in `tests/test_*.py`.
* Numerical outputs are pinned against SciPy's reference implementations
  (paired t, McNemar's exact binomial).

## Known limitations

* Sphinx-style API reference is hand-written rather than auto-generated.
  Tracked for 0.2.
* Multi-epoch RunFrames are accepted by the schema but only epoch 0 is
  used for inference. Tracked for 0.3.
* The SaaS dashboard is in a separate, closed repo.

## Sign-off

Verified locally on macOS 24.6.0, Python 3.14.0, NumPy 2.4.5, SciPy 1.17.1,
PyArrow 24.0.0 -- 2026-05-17.

```bash
$ evalsig --version
evalsig 0.1.0

$ python -m unittest discover tests 2>&1 | tail -3
----------------------------------------------------------------------
Ran 45 tests in 0.385s

OK

$ python research/validate.py 2>&1 | tail -3
========================================================================
  [OK] ALL CLAIMS HOLD. EVALSIG separates the cases the doc promises.
========================================================================
```
