# Installation

EVALSIG ships as a single PyPI package. The core needs only NumPy, SciPy,
and PyArrow.

## Requirements

* Python 3.10 or newer
* macOS, Linux, or Windows
* About 80 MB of disk for the wheel and its dependencies

## Install with pip

```bash
pip install evalsig
```

That gives you everything needed to compare runs, gate releases, write to a
local Parquet store, and use the pytest plugin.

## Install from source

If you want the bleeding-edge version, or are contributing:

```bash
git clone https://github.com/vtensor/evalsig.git
cd evalsig
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

The repo also includes a research validation script:

```bash
python research/validate.py
```

It runs four small Monte Carlo experiments that confirm the library does
what the design doc promises (see [Methodology](../methodology.md) for the
full story).

## Optional extras

| Extra | When to install | Command |
|---|---|---|
| `docs` | Building the documentation site locally | `pip install evalsig[docs]` |
| `dev` | Running the test suite and linters | `pip install evalsig[dev]` |
| `braintrust` | Publishing comparison results to Braintrust | `pip install evalsig[braintrust]` |

## Verify the install

After installing, the CLI should be on your `$PATH`:

```bash
evalsig --version
# evalsig 0.1.0
```

And the Python import should succeed without any optional dependencies:

```python
import evalsig
print(evalsig.__version__)  # '0.1.0'
```

If either fails, double-check that you're using the same Python interpreter
in your shell and your editor. A common gotcha is having `pip` install into a
different environment than the one `python` runs.

## Next steps

* [Quickstart](quickstart.md): the 30-second walkthrough.
* [Your first comparison](first-comparison.md): a longer, hand-held tutorial.
* [Configuration](../usage/configuration.md): every knob the library exposes.
