#!/usr/bin/env python3
"""Fail on new Python lint/type issues in files changed by the current branch."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUFF_PREFIXES = (
    Path("node/src"),
    Path("node/tests"),
    Path("sdks/stigmem-py/src"),
    Path("sdks/stigmem-py/tests"),
    Path("adapters"),
)
MYPY_PREFIXES = (
    Path("node/src"),
    Path("sdks/stigmem-py/src"),
)


def _run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=ROOT,
        check=check,
        text=True,
        capture_output=True,
    )


def _detect_base_ref() -> str | None:
    explicit = os.environ.get("CHECK_CHANGED_BASE_SHA")
    if explicit:
        return explicit

    base_ref = os.environ.get("GITHUB_BASE_REF")
    if base_ref:
        remote_ref = f"origin/{base_ref}"
        _run(["git", "fetch", "origin", base_ref, "--depth=1"], check=False)
        candidate = _run(["git", "merge-base", "HEAD", remote_ref], check=False)
        if candidate.returncode == 0:
            return candidate.stdout.strip()

    before = os.environ.get("GITHUB_EVENT_BEFORE")
    if before and before != "0000000000000000000000000000000000000000":
        return before

    return None


def _changed_python_files(base_ref: str) -> list[Path]:
    diff = _run(["git", "diff", "--name-only", f"{base_ref}...HEAD"])
    files: list[Path] = []
    for raw in diff.stdout.splitlines():
        path = Path(raw.strip())
        if path.suffix != ".py":
            continue
        if not any(path.is_relative_to(prefix) for prefix in RUFF_PREFIXES):
            continue
        if not (ROOT / path).exists():
            continue
        files.append(path)
    return files


def _print_output(result: subprocess.CompletedProcess[str]) -> None:
    if result.stdout:
        sys.stdout.write(result.stdout)
    if result.stderr:
        sys.stderr.write(result.stderr)


def main() -> int:
    base_ref = _detect_base_ref()
    if not base_ref:
        print("Changed-file Python quality check skipped: no diff base available.")
        return 0

    changed_files = _changed_python_files(base_ref)
    if not changed_files:
        print(f"Changed-file Python quality check skipped: no matching Python files since {base_ref}.")
        return 0

    changed_args = [str(path) for path in changed_files]
    print("Running strict Ruff on changed Python files:")
    for path in changed_args:
        print(f"  - {path}")
    ruff = _run(["ruff", "check", *changed_args], check=False)
    _print_output(ruff)
    if ruff.returncode != 0:
        return ruff.returncode

    mypy_targets = [
        str(path)
        for path in changed_files
        if any(path.is_relative_to(prefix) for prefix in MYPY_PREFIXES)
    ]
    if not mypy_targets:
        print("Changed-file mypy check skipped: no changed production Python files.")
        return 0

    print("Running strict mypy on changed production Python files:")
    for path in mypy_targets:
        print(f"  - {path}")
    mypy = _run(
        [
            "mypy",
            "--show-error-codes",
            "--hide-error-context",
            "--no-color-output",
            "--no-pretty",
            *mypy_targets,
        ],
        check=False,
    )
    _print_output(mypy)
    if mypy.returncode not in (0, 1):
        return mypy.returncode
    return mypy.returncode


if __name__ == "__main__":
    raise SystemExit(main())
