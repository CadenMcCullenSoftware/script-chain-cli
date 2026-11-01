#!/usr/bin/env python3
"""Run commands from a JSON pipeline in order."""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from repos_catalog import REPOSITORIES

SKIPPED_DOC_DIRS = {".git", "node_modules", ".venv", "venv", "dist", "build"}
CHECK_TIMEOUT_SECONDS = 300


class PipelineError(Exception):
    """Raised when a pipeline file is invalid or cannot be read."""


class RepositoryError(Exception):
    """Raised when the repository catalog cannot be loaded."""


def load_steps(pipeline_path):
    try:
        data = json.loads(pipeline_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PipelineError(f"cannot read pipeline {pipeline_path}: {error}") from error

    if not isinstance(data, dict) or not isinstance(data.get("steps"), list):
        raise PipelineError("pipeline must be a JSON object with a 'steps' list")
    if not data["steps"]:
        raise PipelineError("pipeline must contain at least one step")

    for index, step in enumerate(data["steps"], start=1):
        if not isinstance(step, dict):
            raise PipelineError(f"step {index} must be an object")
        command = step.get("command")
        if (
            not isinstance(command, list)
            or not command
            or any(not isinstance(argument, str) or not argument for argument in command)
        ):
            raise PipelineError(f"step {index} needs a non-empty string list in 'command'")
        if "cwd" in step and not isinstance(step["cwd"], str):
            raise PipelineError(f"step {index} 'cwd' must be a string")
    return data["steps"]


def run_pipeline(pipeline_path):
    steps = load_steps(pipeline_path)
    base_dir = pipeline_path.resolve().parent

    for index, step in enumerate(steps, start=1):
        name = step.get("name", f"step {index}")
        working_dir = (base_dir / step.get("cwd", ".")).resolve()
        command = step["command"]
        print(f"==> {name}: {' '.join(command)}", flush=True)

        try:
            result = subprocess.run(command, cwd=working_dir, check=False)
        except OSError as error:
            print(f"Error in {name}: {error}", file=sys.stderr)
            return 1

        if result.returncode:
            print(f"Error: {name} exited with status {result.returncode}", file=sys.stderr)
            return result.returncode if result.returncode > 0 else 1

    print(f"Completed {len(steps)} step(s).")
    return 0


def load_catalog():
    return [dict(repo) for repo in REPOSITORIES]


def default_config_path():
    config_home = os.environ.get("XDG_CONFIG_HOME")
    base = Path(config_home).expanduser() if config_home else Path.home() / ".config"
    return base / "script-chain-cli" / "repos.json"


def load_configured_catalog(config_path):
    if not config_path.exists():
        return load_catalog()
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RepositoryError(f"cannot read repository config {config_path}: {error}") from error
    if not isinstance(data, dict) or not isinstance(data.get("repositories"), list):
        raise RepositoryError("repository config must contain a 'repositories' list")
    catalog = []
    for repo in data["repositories"]:
        if (
            not isinstance(repo, dict)
            or not valid_repo_name(repo.get("name"))
            or not isinstance(repo.get("description", ""), str)
            or not isinstance(repo.get("language", "docs"), str)
            or ("path" in repo and not isinstance(repo["path"], str))
        ):
            raise RepositoryError("repository config has an invalid repository entry")
        catalog.append(
            {
                "name": repo["name"],
                "description": repo.get("description", ""),
                "language": repo.get("language", "docs"),
                **({"path": repo["path"]} if repo.get("path") else {}),
            }
        )
    names = [repo["name"] for repo in catalog]
    if len(set(names)) != len(names):
        raise RepositoryError("repository config contains duplicate repository names")
    return catalog


def valid_repo_name(name):
    if not isinstance(name, str):
        return False
    parts = name.split("/")
    return (
        len(parts) == 2
        and all(part not in {".", ".."} for part in parts)
        and all(re.fullmatch(r"[A-Za-z0-9_.-]+", part) for part in parts)
    )


def save_catalog(config_path, catalog):
    config_path = config_path.expanduser()
    temporary_path = None
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=config_path.parent,
            prefix=config_path.name + ".",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
            json.dump({"repositories": catalog}, temporary_file, indent=2)
            temporary_file.write("\n")
        os.replace(temporary_path, config_path)
    except OSError as error:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
        raise RepositoryError(f"cannot write repository config {config_path}: {error}") from error


def repo_slug(repo):
    return repo["name"].rsplit("/", 1)[-1]


def find_repo(catalog, name):
    matches = [repo for repo in catalog if name in (repo["name"], repo_slug(repo))]
    if len(matches) != 1:
        raise RepositoryError(f"unknown repository: {name}")
    return matches[0]


def local_repo_path(root, repo):
    configured_path = repo.get("path")
    if configured_path:
        path = Path(configured_path).expanduser()
        if path.is_absolute():
            return path.resolve()
        return (root.expanduser().resolve() / path).resolve()
    return root.expanduser().resolve() / repo_slug(repo)


def list_repositories(catalog, as_json=False):
    if as_json:
        print(json.dumps(catalog, indent=2))
        return 0
    for repo in catalog:
        description = repo["description"] or "No description"
        print(f'{repo["name"]} [{repo.get("language", "docs")}]: {description}')
    print(f"{len(catalog)} repositories")
    return 0


def repository_status(catalog, root):
    failures = 0
    for repo in catalog:
        path = local_repo_path(root, repo)
        if not path.is_dir():
            print(f'{repo["name"]}: not found ({path})')
            failures += 1
            continue
        try:
            result = subprocess.run(
                [
                    "git",
                    "--no-optional-locks",
                    "-C",
                    str(path),
                    "status",
                    "--short",
                    "--branch",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError as error:
            print(f'{repo["name"]}: cannot run git: {error}', file=sys.stderr)
            failures += 1
            continue
        if result.returncode:
            detail = result.stderr.strip() or f"git exited with status {result.returncode}"
            print(f'{repo["name"]}: {detail}')
            failures += 1
            continue
        output = result.stdout.strip() or "clean (no status output)"
        print(f'{repo["name"]}: {output.replace(os.linesep, os.linesep + "  ")}')
    return 1 if failures else 0


def documentation_files(path):
    if not path.is_dir():
        return []
    files = []
    for candidate in path.rglob("*.md"):
        relative = candidate.relative_to(path)
        if any(part in SKIPPED_DOC_DIRS or part.startswith(".") for part in relative.parts):
            continue
        if candidate.is_file():
            files.append(relative.as_posix())
    return sorted(files, key=str.casefold)


def list_documentation(catalog, root, name=None):
    repos = [find_repo(catalog, name)] if name else catalog
    missing = 0
    for repo in repos:
        path = local_repo_path(root, repo)
        if not path.is_dir():
            print(f'{repo["name"]}: not found ({path})')
            missing += 1
            continue
        files = documentation_files(path)
        print(f'{repo["name"]}:')
        if files:
            for filename in files:
                print(f"  {filename}")
        else:
            print("  no Markdown documentation found")
    return 1 if missing else 0


def read_documentation(catalog, root, name, filename):
    repo = find_repo(catalog, name)
    repo_path = local_repo_path(root, repo)
    candidate = (repo_path / filename).resolve()
    try:
        relative = candidate.relative_to(repo_path.resolve())
    except ValueError as error:
        raise RepositoryError("documentation path must stay inside the repository") from error
    if (
        any(part in SKIPPED_DOC_DIRS or part.startswith(".") for part in relative.parts)
        or candidate.suffix.lower() not in {".md", ".txt"}
        or not candidate.is_file()
    ):
        raise RepositoryError(f"documentation file not found or not readable: {filename}")
    try:
        if candidate.stat().st_size > 200_000:
            raise RepositoryError("documentation file exceeds the 200 KB display limit")
        contents = candidate.read_text(encoding="utf-8")
    except RepositoryError:
        raise
    except (OSError, UnicodeDecodeError) as error:
        raise RepositoryError(f"cannot read documentation file {filename}: {error}") from error
    print(contents, end="" if contents.endswith("\n") else "\n")
    return 0


def discover_repositories(owner=None):
    command = ["gh", "repo", "list"]
    if owner:
        command.append(owner)
    command.extend(
        ["--limit", "1000", "--json", "nameWithOwner,description,primaryLanguage"]
    )
    try:
        result = subprocess.run(command, check=False, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise RepositoryError(f"cannot run GitHub CLI discovery: {error}") from error
    if result.returncode:
        detail = result.stderr.strip() or f"gh exited with status {result.returncode}"
        raise RepositoryError(f"GitHub repository discovery failed: {detail}")
    try:
        remote_repos = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise RepositoryError(f"GitHub CLI returned invalid JSON: {error}") from error
    if not isinstance(remote_repos, list):
        raise RepositoryError("GitHub CLI returned an unexpected repository list")
    discovered = []
    for item in remote_repos:
        if not isinstance(item, dict) or not valid_repo_name(item.get("nameWithOwner")):
            raise RepositoryError("GitHub CLI returned an invalid repository entry")
        language = item.get("primaryLanguage")
        if isinstance(language, dict):
            language = language.get("name")
        discovered.append(
            {
                "name": item["nameWithOwner"],
                "language": language if isinstance(language, str) else "docs",
                "description": item.get("description") or "",
            }
        )
    return discovered


def merge_repositories(catalog, discovered):
    merged = [dict(repo) for repo in catalog]
    by_name = {repo["name"]: repo for repo in merged}
    for remote in discovered:
        current = by_name.get(remote["name"])
        if current:
            for key in ("language", "description"):
                if remote.get(key):
                    current[key] = remote[key]
        else:
            added = dict(remote)
            merged.append(added)
            by_name[added["name"]] = added
    return merged


def add_repository(catalog, config_path, name, description="", language="docs", path=None):
    if not valid_repo_name(name):
        raise RepositoryError("repository name must use OWNER/REPOSITORY format")
    if any(repo["name"] == name for repo in catalog):
        raise RepositoryError(f"repository is already configured: {name}")
    repo = {"name": name, "description": description, "language": language}
    if path:
        repo["path"] = str(path)
    updated = [dict(item) for item in catalog]
    updated.append(repo)
    save_catalog(config_path, updated)
    print(f"Added {name} to {config_path}")
    return 0


def remove_repository(catalog, config_path, name):
    repo = find_repo(catalog, name)
    updated = [dict(item) for item in catalog if item["name"] != repo["name"]]
    save_catalog(config_path, updated)
    print(f'Removed {repo["name"]} from {config_path}')
    return 0


def check_commands(path):
    commands = []
    package_json = path / "package.json"
    if package_json.is_file():
        try:
            package = json.loads(package_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            return None, f"cannot read package.json: {error}"
        if isinstance(package, dict) and isinstance(package.get("scripts"), dict):
            for check_type in ("test", "lint", "build"):
                if check_type in package["scripts"]:
                    commands.append((check_type, ["npm", "run", check_type]))

    if (path / "go.mod").is_file():
        commands.extend(
            [
                ("test", ["go", "test", "./..."]),
                ("lint", ["go", "vet", "./..."]),
                ("build", ["go", "build", "./..."]),
            ]
        )

    tests_dir = path / "tests"
    project_config = ""
    pyproject = path / "pyproject.toml"
    if pyproject.is_file():
        try:
            project_config = pyproject.read_text(encoding="utf-8").lower()
        except OSError as error:
            return None, f"cannot read pyproject.toml: {error}"

    if "[tool.ruff" in project_config or "ruff" in project_config:
        commands.append(("lint", [sys.executable, "-m", "ruff", "check", "."]))
    elif (path / ".flake8").is_file() or "[flake8]" in project_config:
        commands.append(("lint", [sys.executable, "-m", "flake8", "."]))

    if tests_dir.is_dir():
        pytest_config = any(
            (path / filename).is_file()
            for filename in ("pytest.ini", "setup.cfg", "tox.ini")
        )
        pytest_config = pytest_config or "pytest" in project_config
        if pytest_config:
            commands.append(("test", [sys.executable, "-m", "pytest", "-q"]))
        else:
            test_sources = list(tests_dir.rglob("test_*.py")) + list(
                tests_dir.rglob("*_test.py")
            )
            for test_source in test_sources:
                try:
                    source = test_source.read_text(encoding="utf-8")
                except OSError as error:
                    return None, f"cannot read test file {test_source}: {error}"
                if "unittest" in source:
                    commands.append(
                        (
                            "test",
                            [
                                sys.executable,
                                "-m",
                                "unittest",
                                "discover",
                                "-s",
                                "tests",
                                "-v",
                            ],
                        )
                    )
                    break

    return commands, None


def repository_checks(catalog, root, names=None, execute=False, selected_types=None):
    if execute and not names:
        print("Error: specify repository names when using --run", file=sys.stderr)
        return 2
    repos = [find_repo(catalog, name) for name in names] if names else catalog
    failures = 0
    for repo in repos:
        path = local_repo_path(root, repo)
        if not path.is_dir():
            print(f'{repo["name"]}: not found ({path})')
            failures += 1
            continue
        checks, error = check_commands(path)
        if error:
            print(f'{repo["name"]}: {error}')
            continue
        if selected_types:
            checks = [check for check in checks if check[0] in selected_types]
        if not checks:
            wanted = ", ".join(selected_types) if selected_types else "supported"
            print(f'{repo["name"]}: no {wanted} checks detected')
            continue
        for check_type, command in checks:
            print(f'{repo["name"]} [{check_type}]: {" ".join(command)}')
            if not execute:
                print("  not run; pass --run with selected repositories to execute")
                continue
            try:
                result = subprocess.run(
                    command, cwd=path, check=False, timeout=CHECK_TIMEOUT_SECONDS
                )
            except subprocess.TimeoutExpired:
                print(
                    f'{repo["name"]} [{check_type}]: timed out after '
                    f"{CHECK_TIMEOUT_SECONDS} seconds",
                    file=sys.stderr,
                )
                failures += 1
                continue
            except OSError as error:
                print(
                    f'{repo["name"]} [{check_type}]: cannot start command: {error}',
                    file=sys.stderr,
                )
                failures += 1
                continue
            if result.returncode:
                print(
                    f'{repo["name"]} [{check_type}]: exited with status {result.returncode}',
                    file=sys.stderr,
                )
                failures += 1
    return 1 if failures else 0


def main():
    parser = argparse.ArgumentParser(
        description="Run command pipelines and manage a multi-repository workspace."
    )
    subparsers = parser.add_subparsers(dest="action", required=True)
    run_parser = subparsers.add_parser("run", help="run a pipeline file")
    run_parser.add_argument("pipeline", type=Path, help="path to a pipeline JSON file")
    repos_parser = subparsers.add_parser("repos", help="manage the multi-repository workspace")
    repo_actions = repos_parser.add_subparsers(dest="repo_action", required=True)

    def add_config_argument(action_parser):
        action_parser.add_argument(
            "--config", type=Path, default=default_config_path(), help="repository config file"
        )

    list_parser = repo_actions.add_parser(
        "list", aliases=["inventory"], help="list repositories in the built-in catalog"
    )
    list_parser.add_argument("--json", action="store_true", help="print machine-readable JSON")
    add_config_argument(list_parser)
    status_parser = repo_actions.add_parser("status", help="show local Git status")
    status_parser.add_argument("--root", type=Path, default=Path.cwd(), help="workspace directory")
    add_config_argument(status_parser)
    docs_parser = repo_actions.add_parser("docs", help="list Markdown documentation")
    docs_parser.add_argument("repository", nargs="?", help="repository name or GitHub slug")
    docs_parser.add_argument("--root", type=Path, default=Path.cwd(), help="workspace directory")
    add_config_argument(docs_parser)
    read_parser = repo_actions.add_parser("read-doc", help="display a Markdown file")
    read_parser.add_argument("repository", help="repository name or GitHub slug")
    read_parser.add_argument("file", help="repository-relative documentation path")
    read_parser.add_argument("--root", type=Path, default=Path.cwd(), help="workspace directory")
    add_config_argument(read_parser)
    checks_parser = repo_actions.add_parser("checks", help="show or run a repository test command")
    checks_parser.add_argument("repositories", nargs="*", help="repository names or GitHub slugs")
    checks_parser.add_argument("--root", type=Path, default=Path.cwd(), help="workspace directory")
    checks_parser.add_argument(
        "--run",
        action="store_true",
        help="execute detected test commands for the selected repositories",
    )
    checks_parser.add_argument(
        "--type",
        choices=("test", "lint", "build"),
        action="append",
        dest="check_types",
        help="show or run only this check type (repeatable)",
    )
    add_config_argument(checks_parser)
    discover_parser = repo_actions.add_parser(
        "discover", help="list repositories visible to GitHub CLI"
    )
    discover_parser.add_argument("--owner", help="GitHub account or organization (defaults to gh)")
    discover_parser.add_argument(
        "--import", dest="import_repositories", action="store_true",
        help="merge discovered repositories into the persistent config",
    )
    add_config_argument(discover_parser)
    add_parser = repo_actions.add_parser("add", help="add a repository to persistent config")
    add_parser.add_argument("name", help="repository name as OWNER/REPOSITORY")
    add_parser.add_argument("--description", default="")
    add_parser.add_argument("--language", default="docs")
    add_parser.add_argument("--path", help="local checkout path, absolute or relative to --root")
    add_parser.add_argument("--root", type=Path, default=Path.cwd(), help="workspace directory")
    add_config_argument(add_parser)
    remove_parser = repo_actions.add_parser("remove", help="remove a repository from persistent config")
    remove_parser.add_argument("repository", help="repository name or GitHub slug")
    remove_parser.add_argument("--root", type=Path, default=Path.cwd(), help="workspace directory")
    add_config_argument(remove_parser)
    arguments = parser.parse_args()

    try:
        if arguments.action == "repos":
            catalog = load_configured_catalog(arguments.config.expanduser())
            if arguments.repo_action in ("list", "inventory"):
                return list_repositories(catalog, arguments.json)
            if arguments.repo_action == "status":
                return repository_status(catalog, arguments.root)
            if arguments.repo_action == "docs":
                return list_documentation(catalog, arguments.root, arguments.repository)
            if arguments.repo_action == "read-doc":
                return read_documentation(
                    catalog, arguments.root, arguments.repository, arguments.file
                )
            if arguments.repo_action == "checks":
                return repository_checks(
                    catalog,
                    arguments.root,
                    arguments.repositories,
                    arguments.run,
                    arguments.check_types,
                )
            if arguments.repo_action == "discover":
                discovered = discover_repositories(arguments.owner)
                if arguments.import_repositories:
                    catalog = merge_repositories(catalog, discovered)
                    save_catalog(arguments.config, catalog)
                    print(f"Imported {len(discovered)} discovered repositories into {arguments.config}")
                else:
                    list_repositories(discovered)
                return 0
            if arguments.repo_action == "add":
                return add_repository(
                    catalog,
                    arguments.config,
                    arguments.name,
                    arguments.description,
                    arguments.language,
                    arguments.path,
                )
            return remove_repository(catalog, arguments.config, arguments.repository)
        return run_pipeline(arguments.pipeline)
    except (PipelineError, RepositoryError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
