# Script Chain CLI

A lightweight, dependency-free Python command-line tool for running scripts in
sequence. Each step runs only after the previous step succeeds. If a command
fails, the pipeline stops and returns a non-zero exit status.

## Requirements

- Python 3.9 or newer
- Linux, macOS, or Windows

## Install

From the repository directory:

```bash
python3 -m pip install .
```

This installs the `script-chain` command. To install from a source checkout
without installing:

```bash
python3 chain.py run examples/pipeline.json
```

## Quick start

Run the included example pipeline from the repository directory:

```bash
script-chain run examples/pipeline.json
```

The example reads `examples/source.txt`, writes intermediate and report files
under `examples/build/`, and prints progress as each step runs.

## Manage multiple repositories

The `repos` commands use the included catalog, with optional persistent
configuration under `~/.config/script-chain-cli/repos.json` (or
`$XDG_CONFIG_HOME/script-chain-cli/repos.json`). Use `--config` on any `repos`
subcommand to select another config file. For local operations, place each
checkout under a workspace directory using its repository name (for example,
`~/Projects/script-chain-cli`) and pass that directory with `--root`. An
explicit configured checkout path can be set with `repos add --path`.

```bash
script-chain repos list
script-chain repos status --root ~/Projects
script-chain repos docs axiom-hive-code-review --root ~/Projects
script-chain repos read-doc axiom-hive-code-review README.md --root ~/Projects
script-chain repos checks --root ~/Projects
script-chain repos add example-org/project --description "Example project"
script-chain repos remove project
script-chain repos discover --owner CadenMcCullenSoftware
script-chain repos discover --owner CadenMcCullenSoftware --import
```

Discovery reads repository metadata using the authenticated GitHub CLI (`gh`);
`--import` explicitly writes the discovered catalog to config. Inventory,
status, and documentation commands are read-only. `repos checks` detects
conventional test, lint, and build commands and only displays them by default.
To execute checks, specify one or more repositories and explicitly pass
`--run`. Use `--type` to limit the check categories:

```bash
script-chain repos checks script-chain-cli --root ~/Projects --run
script-chain repos checks Delta-V1 --type lint --type test --root ~/Projects
```

Checks time out after five minutes. The CLI does not clone, fetch, or pull
repositories and never runs checks across the whole catalog implicitly. Install
the package to use the `script-chain` command, or run
`python3 chain.py repos --help` from the source checkout.

### Install for regular use

Install from a local checkout:

```bash
python3 -m pip install .
```

Or install the GitHub project with `pipx` for an isolated command-line app:

```bash
pipx install git+https://github.com/CadenMcCullenSoftware/script-chain-cli.git
```

The GitHub CLI (`gh`) is only required for `repos discover`; other commands
work offline against local checkouts.

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
