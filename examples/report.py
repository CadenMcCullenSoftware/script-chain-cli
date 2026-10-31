#!/usr/bin/env python3
"""Create a plain-text summary from the prepared example input."""

import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    lines = [
        line
        for line in args.input.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    report = f"Example report\n==============\nProcessed {len(lines)} lines:\n"
    report += "".join(f"- {line}\n" for line in lines)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(f"Wrote report to {args.output}")


if __name__ == "__main__":
    main()
