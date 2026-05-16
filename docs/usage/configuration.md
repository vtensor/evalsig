# Configuration

EVALSIG has no required configuration file. Every knob is either a CLI
flag, a Python argument, or an environment variable, and every default is
documented below.

## Defaults

| Knob | Default | Where to override |
|---|---|---|
| `alpha` | 0.05 | `--alpha` / `alpha=` |
| `power` | 0.80 | `--power` / `target_power=` |
| `method` | `auto` | `--method` / `method=` |
| `n_resamples` | 10,000 | `--resamples` / `n_resamples=` |
| `one-sided` | off | `--one-sided` / `one_sided=` |
| `rng seed` | 0 | `--seed` / `rng=` |
| Output renderer | `tty` | `--output {tty,json,markdown}` |
| Store project id | `default` | `--project` / `project_id=` |

The minimum-detectable-effect policy (`--min-delta`) is the one
parameter with no default: every gate invocation must declare what
"meaningfully better" means.

## Environment variables

| Variable | Default | Meaning |
|---|---|---|
| `EVALSIG_LOG_LEVEL` | `WARNING` | Stdlib log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `EVALSIG_TELEMETRY` | off | Set to `1` to enable opt-in local usage logging |
| `EVALSIG_TELEMETRY_PATH` | `~/.evalsig/usage.jsonl` | Where the telemetry file lives |

EVALSIG never writes telemetry unless `EVALSIG_TELEMETRY=1` is set, and
even then it only writes a local JSONL file. No network traffic.

## Choosing a method

The default `method="auto"` picks based on the data shape:

* Both runs are 0/1 and no cluster id -> `mcnemar`
* A cluster id is set -> `cluster_bootstrap`
* Otherwise -> `paired_permutation`

Override when you have a reason: very large n with normal-looking diffs
benefits from `paired_t` (~100x faster), and `paired_bootstrap` is the
right call when you want a percentile CI rather than a t-distribution
CI.

## Choosing min-delta

A common rule of thumb:

| Eval type | Suggested min-delta |
|---|---|
| Large, low-noise (MMLU, BBH) | 0.005 (0.5pp) |
| Agentic / long-context | 0.01 to 0.02 (1 to 2pp) |
| Small or noisy judge-graded | 0.02 to 0.05 |

If your run can't afford the items needed for a tight min-delta, relax
the policy. Pretending the run is bigger than it is just hides the
problem.

## Choosing alpha and power

`alpha = 0.05` and `power = 0.80` are the standard defaults from the
literature. Departures we have seen:

* Very high-stakes shipments (foundation model releases) use `alpha = 0.01`.
* Power of 0.90 cuts the chance of an inconclusive run but requires
  about 33% more items.
* Two-sided is the right default for "is this different?"; one-sided
  is the right default for "is this better?", which is the usual
  release question.

## Reproducibility

Always pass a `rng` argument (Python) or `--seed` (CLI). EVALSIG never
uses a global random state, so without an explicit seed your runs are
non-reproducible. Default is 0 to make accidental non-determinism rare.

## Limits

* `n_pairs` must be at least 2 for any test.
* `n_resamples` of 10,000 is a sensible default. Below 1,000 the p-value
  is too granular for typical alpha values; above 100,000 you usually
  hit a memory bound before you hit a precision bound.
* The cluster bootstrap concatenates per-cluster slices, which is fine
  up to about a million items in a single resample. For larger runs,
  switch to chunked Parquet reads (`evalsig.io.read_runframe_parquet`)
  and resample at the cluster level only.

## See also

* [CLI reference](cli.md) for every flag.
* [Python API](python-api.md) for every keyword argument.
* [Output formats](output-formats.md) for renderer details.
