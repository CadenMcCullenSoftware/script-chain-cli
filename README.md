# Script Chain CLI

A small, dependency-free Python CLI for running scripts in sequence. Each step
gets its own command and arguments. The runner stops at the first failure and
returns a non-zero exit status.

## Run a pipeline

Create a JSON file such as `pipeline.json`:

```json
{
  "steps": [
    {
      "name": "prepare data",
      "command": ["python3", "scripts/prepare.py", "--input", "source.csv"]
    },
    {
      "name": "generate report",
      "command": ["python3", "scripts/report.py", "--format", "html"]
    }
  ]
}
```

Then run:

```bash
python3 chain.py run pipeline.json
```

Commands run from the pipeline file's directory by default. Set `"cwd"` on a
step to use a different working directory; relative paths are based on the
pipeline file's directory:

```json
{
  "name": "build",
  "cwd": "app",
  "command": ["python3", "build.py", "--release"]
}
```

Commands are argument arrays rather than shell strings, so spaces and special
characters in arguments are passed safely without shell interpretation. Output
from each script appears in the terminal. The first command that fails stops
the pipeline and identifies the failing step.

## Tests

Run the built-in tests with:

```bash
python3 -m unittest discover -s tests -v
```
