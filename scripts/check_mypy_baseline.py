#!/usr/bin/env python3
"""Fail on new mypy findings while allowing a staged cleanup of existing debt."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASELINE = ROOT / ".github" / "baselines" / "python-mypy.txt"
TARGETS = [
    "node/src",
    "sdks/stigmem-py/src",
]
ERROR_RE = re.compile(r"^(?P<path>[^:]+):(?P<line>\d+): error: (?P<message>.+) \[(?P<code>[^\]]+)\]$")


def _normalize(line: str) -> str | None:
    match = ERROR_RE.match(line.strip())
    if not match:
        return None
    path = Path(match.group("path")).resolve().relative_to(ROOT)
    message = match.group("message").strip()
    return f"{path}:{match.group('line')}:{match.group('code')}:{message}"


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
        "# mypy baseline for staged rollout.",
        "# One issue fingerprint per line: path:line:code:message",
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
        [
            "mypy",
            "--show-error-codes",
            "--hide-error-context",
            "--no-color-output",
            "--no-pretty",
            *TARGETS,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if result.stderr:
        sys.stderr.write(result.stderr)

    issues = {
        normalized
        for line in result.stdout.splitlines()
        for normalized in [_normalize(line)]
        if normalized is not None
    }

    if result.returncode not in (0, 1):
        sys.stderr.write(result.stdout)
        return result.returncode

    if args.write_baseline:
        _write_baseline(BASELINE, issues)
        print(f"Wrote {len(issues)} mypy baseline entries to {BASELINE.relative_to(ROOT)}.")
        return 0

    baseline = _load_baseline(BASELINE)
    new_issues = sorted(issues - baseline)
    resolved = sorted(baseline - issues)

    if new_issues:
        print("New mypy findings not present in the staged baseline:")
        for issue in new_issues:
            print(issue)
        return 1

    print(
        f"mypy baseline check passed: {len(issues)} known issue(s), "
        f"{len(resolved)} resolved since baseline."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
