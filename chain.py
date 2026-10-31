#!/usr/bin/env python3
"""Run commands from a JSON pipeline in order."""

import argparse
import json
import subprocess
import sys
from pathlib import Path


class PipelineError(Exception):
    """Raised when a pipeline file is invalid or cannot be read."""


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


def main():
    parser = argparse.ArgumentParser(description="Run scripts in a JSON pipeline, in order.")
    subparsers = parser.add_subparsers(dest="action", required=True)
    run_parser = subparsers.add_parser("run", help="run a pipeline file")
    run_parser.add_argument("pipeline", type=Path, help="path to a pipeline JSON file")
    arguments = parser.parse_args()

    try:
        return run_pipeline(arguments.pipeline)
    except PipelineError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
