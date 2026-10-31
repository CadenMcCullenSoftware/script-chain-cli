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
