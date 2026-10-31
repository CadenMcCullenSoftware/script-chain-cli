# User workflow: running a command pipeline

This guide explains how to set up and run a sequence of scripts with Script
Chain CLI. Run commands in a terminal.

## 1. Open the project folder

```bash
cd ~/Desktop/script-chain-cli
```

Python 3.9 or newer is required. Check that it is available:

```bash
python3 --version
```

For the simplest setup, install the CLI from this folder:

```bash
python3 -m pip install .
```

After installation, run it with `script-chain`. If you prefer not to install it,
use `python3 chain.py` in the commands below.

## 2. Add the scripts you want to run

Put your scripts in this folder or in a subfolder. For example:

```text
script-chain-cli/
├── chain.py
├── pipeline.json
└── scripts/
    ├── prepare.py
    └── report.py
```

Each script should work when run on its own. If a script needs command-line
options, test those options before adding it to a pipeline.

## 3. Create a pipeline file

Create `pipeline.json` in the project folder. List commands in the order they
should run:

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

Each `command` is a list: the executable comes first, followed by its
arguments. Keep each argument as a separate string. Do not write a single
shell-command string. The optional `name` gives the step a readable label.

Commands run with the pipeline file's folder as their working directory.
Relative script and data paths in commands are resolved from that folder. You
can set an optional `"cwd"` on a step to change its working directory; relative
`cwd` paths are also resolved from the pipeline file's folder.

## 4. Run the pipeline

From the project folder, run:

```bash
script-chain run pipeline.json
```

Without installing, run `python3 chain.py run pipeline.json` instead.

You will see each step printed as it starts, followed by the script's output.
The next step starts only after the current one succeeds. The pipeline stops
at the first failed command and prints the step name and exit status.

You can also provide a pipeline path directly:

```bash
script-chain run ~/Desktop/script-chain-cli/pipeline.json
```

If you did not install the CLI, substitute
`python3 ~/Desktop/script-chain-cli/chain.py run` for `script-chain run`.

## 5. Handle errors

- **Cannot read pipeline:** Check the pipeline path and make sure its contents
  are valid JSON.
- **Pipeline must contain a `steps` list:** Add a top-level `"steps"` array
  with at least one step.
- **Step needs a command:** Make sure every step has a non-empty `command`
  array of strings.
- **No such file or directory:** Check that the executable, script, and input
  paths exist. Relative paths are based on the pipeline file's directory (or
  the step's `cwd` for paths used by the command).
- **A step exited with a status:** Run that script by itself with the displayed
  arguments to inspect its error, fix the script or inputs, and run the
  pipeline again.

The CLI returns `0` when all steps succeed and a non-zero status if the
pipeline is invalid or a command fails.
