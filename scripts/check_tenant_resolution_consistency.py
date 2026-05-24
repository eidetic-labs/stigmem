#!/usr/bin/env python3
"""Validate TenantContext construction carries explicit source metadata."""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCAN_ROOTS = (ROOT / "node/src/stigmem_node",)
ALLOWED_SOURCES = frozenset({"hook", "pinned", "resolved", "system"})


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _is_tenant_context_call(node: ast.Call) -> bool:
    if isinstance(node.func, ast.Name):
        return node.func.id == "TenantContext"
    if isinstance(node.func, ast.Attribute):
        return node.func.attr == "TenantContext"
    return False


def _source_from_metadata(node: ast.Call) -> str | None:
    for keyword in node.keywords:
        if keyword.arg != "metadata":
            continue
        if not isinstance(keyword.value, ast.Dict):
            return None
        for key, value in zip(keyword.value.keys, keyword.value.values, strict=False):
            if isinstance(key, ast.Constant) and key.value == "tenant_context_source":
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    return value.value
                return None
    return None


def _tenant_id_literal(node: ast.Call) -> str | None:
    for keyword in node.keywords:
        if (
            keyword.arg == "tenant_id"
            and isinstance(keyword.value, ast.Constant)
            and isinstance(keyword.value.value, str)
        ):
            return keyword.value.value
    if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
        return node.args[0].value
    return None


def _python_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_file() and path.suffix == ".py":
            files.append(path)
        elif path.is_dir():
            files.extend(sorted(path.rglob("*.py")))
    return [path for path in sorted(files) if "__pycache__" not in path.parts]


def check_paths(paths: list[Path]) -> list[str]:
    failures: list[str] = []
    for path in _python_files(paths):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=path.as_posix())
        except SyntaxError as exc:
            failures.append(
                f"{_display_path(path)}:{exc.lineno}: unable to parse Python: {exc.msg}"
            )
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not _is_tenant_context_call(node):
                continue
            source = _source_from_metadata(node)
            display = _display_path(path)
            if source not in ALLOWED_SOURCES:
                failures.append(
                    f"{display}:{node.lineno}: TenantContext missing explicit "
                    "metadata tenant_context_source in {'hook', 'pinned', "
                    "'resolved', 'system'}."
                )
                continue
            tenant_id = _tenant_id_literal(node)
            if source == "pinned" and tenant_id != "default":
                failures.append(
                    f"{display}:{node.lineno}: pinned TenantContext must use "
                    'tenant_id="default".'
                )
            if source == "resolved" and tenant_id == "default":
                failures.append(
                    f"{display}:{node.lineno}: resolved TenantContext must not "
                    "pin the default tenant."
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
    failures = check_paths(args.paths or list(DEFAULT_SCAN_ROOTS))
    if failures:
        print("Tenant-resolution consistency failures:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print("OK: TenantContext construction declares tenant_context_source consistently.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
