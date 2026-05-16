# `evalsig.cli`

The Click-free, argparse-based command-line interface. One entry point
(`evalsig.cli.main.main`), one subcommand per verb.

## Subcommands

| Subcommand | Purpose | Exit codes |
|---|---|---|
| `compare` | Print delta, CI, p, MDE. No policy. | 0 always |
| `gate` | Same as compare plus a min-delta policy | 0 / 1 / 2 |
| `mde` | MDE / required-N planner | 0 always |
| `watch` | Always-valid sequential test | 0 / 2 |
| `doctor` | Validate one or more RunFrame JSON files | 0 / 65 |
| `history` | List the local store | 0 always |
| `version` | Print the package version | 0 |

See [CLI reference](../usage/cli.md) for the full flag table.

## How the parser is wired

`build_parser()` returns a fully-configured `argparse.ArgumentParser`.
Each subcommand registers a `cmd_*` callback via `set_defaults(func=...)`.
The entry-point script (`evalsig` on your `$PATH`) calls
`evalsig.cli.main.main(sys.argv[1:])`, which dispatches to the chosen
callback and translates exceptions:

* `ValueError`, `FileNotFoundError` -> exit 65 (data error)
* anything else uncaught -> exit 70 (internal error)

## Reusing the CLI from Python

You can call `main()` programmatically. This is how the test suite drives
the subcommands without spawning subprocesses:

```python
from evalsig.cli.main import main

# Same as running:  evalsig gate --baseline a.json --candidate b.json --min-delta 0.005
exit_code = main([
    "gate",
    "--baseline", "a.json",
    "--candidate", "b.json",
    "--min-delta", "0.005",
])
```

## Output routing

* `--output {tty,json,markdown}` chooses the renderer for stdout.
* `--json path` writes a JSON copy regardless of the stdout renderer.

If stdout is not a terminal, the TTY renderer drops ANSI colors
automatically.

## See also

* [CLI reference](../usage/cli.md) for the full flag list.
* [Output formats](../usage/output-formats.md) for renderer details.
