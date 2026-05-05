#!/usr/bin/env python3
"""Fail on new Ruff findings while allowing a staged cleanup of existing debt."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASELINE = ROOT / ".github" / "baselines" / "python-ruff.txt"
TARGETS = [
    "node/src",
    "sdks/stigmem-py/src",
    "node/tests",
    "sdks/stigmem-py/tests",
    "adapters",
]


def _normalize(issue: dict[str, object]) -> str:
    filename = Path(str(issue["filename"])).resolve().relative_to(ROOT)
    location = issue["location"]
    assert isinstance(location, dict)
    row = int(location["row"])
    column = int(location["column"])
    code = str(issue["code"])
    message = str(issue["message"])
    return f"{filename}:{row}:{column}:{code}:{message}"


def _load_baseline(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    }


def _write_baseline(path: Path, issues: set[str]) -> None:
    header = [
        "# Ruff baseline for staged rollout.",
        "# One issue fingerprint per line: path:row:col:code:message",
        "",
    ]
    body = sorted(issues)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(header + body) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help="Refresh the committed baseline from the current tool output.",
    )
    args = parser.parse_args()

    result = subprocess.run(
        ["ruff", "check", "--output-format", "json", *TARGETS],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if result.stderr:
        sys.stderr.write(result.stderr)

    try:
        raw_issues = json.loads(result.stdout or "[]")
    except json.JSONDecodeError:
        sys.stderr.write(result.stdout)
        return result.returncode or 1

    if not isinstance(raw_issues, list):
        sys.stderr.write("Unexpected Ruff output format.\n")
        return 1

    issues = {_normalize(issue) for issue in raw_issues}

    if args.write_baseline:
        _write_baseline(BASELINE, issues)
        print(f"Wrote {len(issues)} Ruff baseline entries to {BASELINE.relative_to(ROOT)}.")
        return 0

    baseline = _load_baseline(BASELINE)
    new_issues = sorted(issues - baseline)
    resolved = sorted(baseline - issues)

    if new_issues:
        print("New Ruff findings not present in the staged baseline:")
        for issue in new_issues:
            print(issue)
        return 1

    print(
        f"Ruff baseline check passed: {len(issues)} known issue(s), "
        f"{len(resolved)} resolved since baseline."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
