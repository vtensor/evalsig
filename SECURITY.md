# Security policy

## Supported versions

EVALSIG is in 0.x, so only the latest release line receives security
fixes. Once 1.0 ships, we will maintain at least the two most recent
minor versions.

| Version | Status |
|---|---|
| 0.1.x | Supported |
| < 0.1 | Not supported |

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security problems.

Email `security@evalsig.dev` instead. Include:

1. A description of the vulnerability and the impact you believe it has.
2. Steps to reproduce, ideally with a minimal test case.
3. Affected versions.
4. Any suggested fix or mitigation (optional but appreciated).

We will acknowledge receipt within 2 business days and follow up with
a remediation plan inside 7 days. Critical issues get a coordinated
disclosure timeline; non-critical ones go through the normal release
cycle with credit in the changelog.

## Scope

In scope:

* The core library (`src/evalsig`).
* The shipped CLI.
* The published GitHub Action and pre-commit hook.
* The documentation site if hosted at `evalsig.dev`.

Out of scope:

* Vulnerabilities in EVALSIG's *dependencies* (NumPy, SciPy, PyArrow).
  Please report those upstream; we will pull in their fixes promptly.
* Misuse of the library that leaks data (for example, persisting
  user prompts into the Parquet store with no encryption). The
  library makes it easy to avoid that; configuration mistakes are
  the user's responsibility.

## Threat model

EVALSIG is a statistics library and CLI. It does not call the network
unless you opt into the SaaS or set `EVALSIG_TELEMETRY=1`. The local
attack surface is small:

* **File parsing**. Readers (`evalsig.io.*`) consume untrusted JSON
  and Parquet files. We validate against a published schema and use
  PyArrow for Parquet, which has its own hardening.
* **Subprocess.** The CLI shells out to nothing.
* **Eval execution.** EVALSIG does *not* run user-supplied Python; it
  only reads scored outputs.

That said, please treat us like any package: pin a known version,
verify the wheel signature, and review the changelog before upgrading.

## Cryptographic signatures

Each release on PyPI is signed with a Sigstore identity. Verify with:

```bash
pip install sigstore
python -m sigstore verify identity \
    --bundle evalsig-0.1.0-py3-none-any.whl.sigstore \
    --cert-identity 'https://github.com/vtensor/evalsig/.github/workflows/release.yml@refs/tags/v0.1.0' \
    --cert-oidc-issuer 'https://token.actions.githubusercontent.com' \
    evalsig-0.1.0-py3-none-any.whl
```

## Bug bounty

EVALSIG does not run a paid bug bounty program. We do publish a
hall-of-fame acknowledgement in [CHANGELOG.md](docs/changelog.md) for
researchers who report responsibly.
