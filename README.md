# Script Chain CLI

A lightweight, dependency-free Python command-line tool for running scripts in
sequence. Each step runs only after the previous step succeeds. If a command
fails, the pipeline stops and returns a non-zero exit status.

## Requirements

- Python 3.9 or newer
- Linux, macOS, or Windows

## Install

From a local checkout:

```bash
python3 -m pip install .
```

Or install the GitHub project with `pipx` for an isolated command-line app:

```bash
pipx install git+https://github.com/CadenMcCullenSoftware/script-chain-cli.git
```

The GitHub CLI (`gh`) is required only for `repos discover`; other commands
work offline against local checkouts.

## Quick start

Run the included example pipeline from the repository directory:

```bash
script-chain run examples/pipeline.json
```

The example reads `examples/source.txt`, writes intermediate and report files
under `examples/build/`, and prints progress as each step runs.

## Manage multiple repositories

The `repos` commands start with the included catalog. If a config file exists,
it becomes the active catalog. The default config location is
`~/.config/script-chain-cli/repos.json`, or
`$XDG_CONFIG_HOME/script-chain-cli/repos.json` when set. Use `--config` on any
`repos` subcommand to choose a different file.

For local operations, put checkouts under one workspace directory using their
repository names (for example, `~/Projects/script-chain-cli`) and pass it with
`--root`. You can instead store a checkout path on an individual configured
repository with `repos add --path`; absolute paths work regardless of `--root`,
and relative paths are resolved from `--root`.

```bash
script-chain repos list
script-chain repos status --root ~/Projects
script-chain repos docs axiom-hive-code-review --root ~/Projects
script-chain repos read-doc axiom-hive-code-review README.md --root ~/Projects
script-chain repos checks --root ~/Projects
script-chain repos add example-org/project --description "Example project" \
  --path /work/project
script-chain repos remove project
script-chain repos discover --owner CadenMcCullenSoftware
script-chain repos discover --owner CadenMcCullenSoftware --import
```

Discovery reads repositories visible to the authenticated GitHub CLI (`gh`).
Without `--import`, it only prints the discovered list. With `--import`, it
merges the results into the selected config file; it does not clone anything.
Inventory, status, and documentation commands are read-only.

`repos checks` detects supported test, lint, and build commands and only
displays them by default. It recognizes npm scripts named `test`, `lint`, or
`build`; Go test, vet, and build commands when `go.mod` exists; Python pytest
or unittest tests; and configured Ruff or Flake8 linting. Detection is
conventional and does not guarantee that required tools or dependencies are
installed. To execute checks, specify one or more repositories and explicitly
pass `--run`. Use `--type` to limit categories:

```bash
script-chain repos checks script-chain-cli --root ~/Projects --run
script-chain repos checks Delta-V1 --type lint --type test --root ~/Projects
```

Checks run sequentially and time out individually after five minutes. The CLI
does not clone, fetch, or pull
repositories and never runs checks across the whole catalog implicitly. Install
the package to use the `script-chain` command, or run
`python3 chain.py repos --help` from the source checkout.

## Create your own pipeline

Create a JSON file with a `steps` list. Each step needs a `command` array:

```json
{
  "steps": [
    {
      "name": "Prepare data",
      "command": ["python3", "scripts/prepare.py", "--input", "source.csv"]
    },
    {
      "name": "Create report",
      "command": ["python3", "scripts/report.py", "--format", "html"]
    }
  ]
}
```

Run it with:

```bash
script-chain run pipeline.json
```

Commands are arrays of arguments, not shell command strings. Keep each argument
as its own string; shell operators such as `|` and `&&` are not interpreted.
This avoids accidental shell interpretation and supports arguments containing
spaces.

Commands run from the pipeline file's directory by default. Use the optional
`cwd` field to select a different working directory for a step. Relative `cwd`
paths are based on the pipeline file's directory; the command then runs inside
that directory:

```json
{
  "steps": [
    {
      "name": "Build app",
      "cwd": "app",
      "command": ["python3", "build.py", "--release"]
    }
  ]
}
```

Step names are optional. If omitted, the CLI labels steps by number. Standard
output and error from each command are shown in the terminal. The runner stops
at the first unsuccessful command and returns its exit status (or `1` if it
could not start).

## Help

```bash
script-chain --help
script-chain run --help
script-chain repos --help
script-chain repos checks --help
```

## Tests

Run the test suite from the repository directory:

```bash
python3 -m unittest discover -s tests -v
```

## Repository guide

- [`WORKFLOW.md`](WORKFLOW.md): user workflow and troubleshooting
- [`examples/`](examples/): runnable sample pipeline and scripts
- [`tests/`](tests/): automated tests

## License

This project is licensed under the Apache-2.0 license. See [`LICENSE`](LICENSE).
