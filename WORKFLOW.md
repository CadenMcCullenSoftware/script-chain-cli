# User workflow: Script Chain CLI

Script Chain runs JSON command pipelines and provides read-only management
commands for a multi-repository workspace. Commands that execute repository
checks require explicit repository selection and the `--run` flag.

## 1. Install

Python 3.9 or newer is required. Install from a checkout:

```bash
cd ~/Projects/script-chain-cli
python3 -m pip install .
```

Alternatively, install the published GitHub repository with `pipx`:

```bash
pipx install git+https://github.com/CadenMcCullenSoftware/script-chain-cli.git
```

For a source checkout without installation, replace `script-chain` with
`python3 /path/to/script-chain-cli/chain.py`.

## 2. Set up repository workspaces

By default, local commands expect each repository checkout in a workspace
directory under its repository name:

```text
~/Projects/
├── script-chain-cli/
├── Delta-V1/
└── project-cerberus/
```

Pass the workspace directory to local commands with `--root`:

```bash
script-chain repos status --root ~/Projects
```

The initial repository catalog is included with the CLI. A persistent config,
when present, replaces that catalog. Its default location is
`~/.config/script-chain-cli/repos.json`, or
`$XDG_CONFIG_HOME/script-chain-cli/repos.json` when the environment variable is
set. Pass `--config /path/to/repos.json` to any `repos` command to use another
config file.

## 3. Inventory and configure repositories

List the active catalog in human-readable or JSON form:

```bash
script-chain repos list
script-chain repos list --json
```

Add a repository to the persistent config. `--path` is optional; absolute
paths work directly, and relative paths are resolved from `--root` by local
commands:

```bash
script-chain repos add example-org/project \
  --description "Example project" \
  --language Python \
  --path /work/project
```

Remove a configured repository by its full `OWNER/REPOSITORY` name or by a
unique repository slug:

```bash
script-chain repos remove project
```

Discover repositories visible to the GitHub CLI:

```bash
gh auth status
script-chain repos discover --owner CadenMcCullenSoftware
```

Discovery requires `gh` to be installed and authenticated. By default, the
results are displayed without changing config. Add `--import` to merge the
discovered repository metadata into the selected config:

```bash
script-chain repos discover --owner CadenMcCullenSoftware --import
```

Discovery does not clone repositories.

## 4. Check local repositories

Show the Git branch and working-tree status for each configured checkout:

```bash
script-chain repos status --root ~/Projects
```

List Markdown documentation for every checkout, or for one repository:

```bash
script-chain repos docs --root ~/Projects
script-chain repos docs project --root ~/Projects
```

Display a Markdown or text file from within a repository:

```bash
script-chain repos read-doc project README.md --root ~/Projects
```

The requested file must be inside the repository, must not be in a hidden or
generated directory, and must be no larger than 200 KB.

## 5. Preview or run project checks

Preview conventional test, lint, and build commands without running them:

```bash
script-chain repos checks --root ~/Projects
script-chain repos checks Delta-V1 --type lint --type test --root ~/Projects
```

Execute checks only for explicitly named repositories, adding `--run`:

```bash
script-chain repos checks script-chain-cli --root ~/Projects --run
script-chain repos checks ccops Delta-V1 --type test --run --root ~/Projects
```

The CLI recognizes npm `test`, `lint`, and `build` scripts; Go test, vet, and
build commands when a `go.mod` file exists; Python tests configured for pytest
or using unittest; and Ruff or Flake8 lint configuration. Check detection is
conventional, so inspect the displayed commands and install project
dependencies before running them. Checks run sequentially, with a five-minute
timeout per command. No repository is checked by default unless you explicitly
add `--run`.

## 6. Run a command pipeline

Create a JSON file with a `steps` list. Each step has a command as an array of
arguments, not a shell command string:

```json
{
  "steps": [
    {
      "name": "Prepare data",
      "command": ["python3", "scripts/prepare.py", "--input", "source.csv"]
    },
    {
      "name": "Create report",
      "cwd": "app",
      "command": ["python3", "report.py", "--format", "html"]
    }
  ]
}
```

Run the pipeline with:

```bash
script-chain run pipeline.json
```

Commands run from the pipeline file's directory unless a step sets `cwd`.
Relative `cwd` values are resolved from the pipeline file's directory. The
pipeline stops at the first failing step and returns a non-zero status.

## Troubleshooting

- **Repository not found:** Confirm it is checked out under its repository
  slug, check `--root`, or add the correct path using `repos add --path`.
- **Unknown repository:** Run `repos list` and use the exact name or a unique
  slug. Duplicate slugs require the full `OWNER/REPOSITORY` name.
- **GitHub discovery fails:** Install `gh`, authenticate with `gh auth login`,
  and verify access with `gh auth status`.
- **No supported checks found:** The project may use a test/lint/build system
  that is not detected, or its test runner may not be configured conventionally.
- **Check command fails:** Install the project's development dependencies,
  inspect the command shown by `repos checks`, and run it manually from that
  repository to inspect its full error.
- **Pipeline cannot read its file:** Verify that the path exists and contains
  valid JSON with a non-empty `steps` array.
- **Pipeline command fails:** Run the displayed command manually from the
  pipeline's working directory and check its executable and input paths.

## Tests

Run Script Chain's own test suite from its checkout:

```bash
python3 -m unittest discover -s tests -v
```
