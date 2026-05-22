#!/usr/bin/env python3
"""Check source and test files against Stigmem size conventions."""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

SKIP_DIRS = {
    ".git",
    ".mypy_cache",
    ".next",
    ".pytest_cache",
    ".ruff_cache",
    ".turbo",
    ".venv",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "playwright-report",
    "test-results",
}
SKIP_PREFIXES = {
    Path("docs/archive"),
    Path("spec/archive"),
}
LOCKFILES = {"package-lock.json", "pnpm-lock.yaml", "uv.lock"}
SOURCE_EXTENSIONS = {".go", ".js", ".jsx", ".md", ".mdx", ".py", ".ts", ".tsx"}
GENERATED_MARKER = "AUTO-GENERATED"
LARGE_FILE_MARKER = "LARGE-FILE-JUSTIFIED"

SOURCE_SOFT_LIMIT = 500
SOURCE_HARD_LIMIT = 1500
TEST_SOFT_LIMIT = 1000
TEST_HARD_LIMIT = 2000

KNOWN_GENERATED_PATHS = {
    Path("sdks/stigmem-ts/src/generated.ts"),
    Path("spec/PROTOCOL.md"),
}
KNOWN_GENERATED_PREFIXES = {
    Path("docs/docs/reference/api/generated"),
}


@dataclass(frozen=True)
class Finding:
    severity: str
    path: Path
    lines: int
    message: str


def _is_under(path: Path, parent: Path) -> bool:
    return path == parent or parent in path.parents


def _iter_files() -> list[Path]:
    files: list[Path] = []
    for directory, dirnames, filenames in os.walk(ROOT):
        base = Path(directory)
        rel_dir = base.relative_to(ROOT)
        if any(part in SKIP_DIRS for part in rel_dir.parts):
            dirnames[:] = []
            continue
        if any(_is_under(rel_dir, prefix) for prefix in SKIP_PREFIXES):
            dirnames[:] = []
            continue

        dirnames[:] = [
            dirname
            for dirname in dirnames
            if dirname not in SKIP_DIRS
            and not any(_is_under(rel_dir / dirname, prefix) for prefix in SKIP_PREFIXES)
        ]

        for filename in filenames:
            path = base / filename
            if path.name in LOCKFILES:
                continue
            if path.suffix not in SOURCE_EXTENSIONS:
                continue
            files.append(path)
    return sorted(files)


def _is_test_file(rel: Path) -> bool:
    parts = rel.parts
    return (
        "tests" in parts
        or rel.name.startswith("test_")
        or rel.name.endswith(".test.ts")
        or rel.name.endswith(".test.tsx")
        or rel.name.endswith(".spec.ts")
        or rel.name.endswith(".spec.tsx")
    )


def _is_known_generated(rel: Path) -> bool:
    if rel in KNOWN_GENERATED_PATHS:
        return True
    return any(_is_under(rel, prefix) for prefix in KNOWN_GENERATED_PREFIXES)


def _generated_prefix_has_marker(rel: Path) -> bool:
    for prefix in KNOWN_GENERATED_PREFIXES:
        if _is_under(rel, prefix):
            marker = ROOT / prefix / ".generated"
            return marker.exists() and GENERATED_MARKER in marker.read_text(encoding="utf-8")
    return False


def _line_count(text: str) -> int:
    if not text:
        return 0
    return text.count("\n") + (0 if text.endswith("\n") else 1)


def _has_marker(text: str, marker: str) -> bool:
    return marker in "\n".join(text.splitlines()[:20])


def _check_file(path: Path) -> list[Finding]:
    rel = path.relative_to(ROOT)
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return [
            Finding(
                "error",
                rel,
                0,
                "source-like file is not UTF-8; add an explicit skip if this is generated",
            )
        ]

    lines = _line_count(text)
    if _is_known_generated(rel):
        if not _has_marker(text, GENERATED_MARKER) and not _generated_prefix_has_marker(rel):
            return [
                Finding(
                    "error",
                    rel,
                    lines,
                    "generated file is missing an AUTO-GENERATED header marker",
                )
            ]
        return []

    soft_limit = TEST_SOFT_LIMIT if _is_test_file(rel) else SOURCE_SOFT_LIMIT
    hard_limit = TEST_HARD_LIMIT if _is_test_file(rel) else SOURCE_HARD_LIMIT

    if lines > hard_limit and not _has_marker(text, LARGE_FILE_MARKER):
        return [
            Finding(
                "error",
                rel,
                lines,
                f"exceeds hard limit {hard_limit}; split it or add LARGE-FILE-JUSTIFIED",
            )
        ]
    if lines > soft_limit:
        return [
            Finding(
                "warning",
                rel,
                lines,
                f"exceeds soft limit {soft_limit}; consider decomposition during nearby work",
            )
        ]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--warnings-as-errors",
        action="store_true",
        help="Treat soft-limit warnings as build failures.",
    )
    args = parser.parse_args()

    findings = [finding for path in _iter_files() for finding in _check_file(path)]
    for finding in findings:
        print(
            f"{finding.severity}: {finding.path}:{finding.lines}: {finding.message}",
            file=sys.stderr if finding.severity == "error" else sys.stdout,
        )

    errors = [finding for finding in findings if finding.severity == "error"]
    warnings = [finding for finding in findings if finding.severity == "warning"]
    print(
        f"file-size: {len(errors)} error(s), {len(warnings)} warning(s), "
        f"{len(_iter_files())} files checked"
    )
    if errors or (args.warnings_as_errors and warnings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
