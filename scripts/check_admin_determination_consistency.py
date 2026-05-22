#!/usr/bin/env python3
"""Validate that admin gates use the dedicated admin capability."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCAN_ROOTS = (ROOT / "node/src/stigmem_node",)

PATTERNS = (
    re.compile(r"\b\w+\.can_write\(\)\s*and\s*\w+\.can_federate\(\)"),
    re.compile(r"\b\w+\.can_federate\(\)\s*and\s*\w+\.can_write\(\)"),
    re.compile(r'"admin"\s*in\s*\w+\.permissions'),
    re.compile(r"'admin'\s*in\s*\w+\.permissions"),
)


def check_paths(paths: list[Path]) -> list[str]:
    failures: list[str] = []
    files: list[Path] = []
    for path in paths:
        if path.is_file() and path.suffix == ".py":
            files.append(path)
        elif path.is_dir():
            files.extend(sorted(path.rglob("*.py")))

    for path in sorted(files):
        if "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        for index, line in enumerate(text.splitlines(), start=1):
            for pattern in PATTERNS:
                if pattern.search(line):
                    try:
                        display = path.relative_to(ROOT).as_posix()
                    except ValueError:
                        display = path.as_posix()
                    failures.append(
                        f"{display}:{index}: admin gate uses a capability-combination "
                        "proxy instead of identity.is_admin()."
                    )
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="Python files or directories to scan. Defaults to node/src/stigmem_node.",
    )
    args = parser.parse_args(argv)
    paths = args.paths or list(DEFAULT_SCAN_ROOTS)
    failures = check_paths(paths)
    if failures:
        print("Admin-determination consistency failures:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print("OK: admin determination uses identity.is_admin() consistently.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
