#!/usr/bin/env python3
"""Docs drift watchdog — flags forbidden strings, stale quarter dates,
absolute claims, and bare ticket IDs in the docs tree."""

from __future__ import annotations

import fnmatch
import json
import re
import sys
from pathlib import Path

DOCS_ROOT = Path(__file__).resolve().parent.parent
RULES_PATH = Path(__file__).resolve().parent / "drift-rules.json"

SKIP_DIRS = {"node_modules", ".docusaurus", "__pycache__"}
SCAN_EXTENSIONS = {".md", ".mdx", ".tsx", ".jsx", ".ts", ".js", ".css"}


def load_rules(path: Path) -> dict:
    with open(path) as f:
        return json.load(f)


def scan_files(root: Path) -> list[Path]:
    build_output = root / "build"
    files: list[Path] = []
    for p in root.rglob("*"):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        if p.is_relative_to(build_output):
            continue
        if p.is_file() and p.suffix in SCAN_EXTENSIONS:
            files.append(p)
    return sorted(files)


def rel(path: Path) -> str:
    return str(path.relative_to(DOCS_ROOT.parent))


def matches_exempt(filepath: Path, exempt_globs: list[str]) -> bool:
    relative = str(filepath.relative_to(DOCS_ROOT.parent))
    return any(fnmatch.fnmatch(relative, g) for g in exempt_globs)


def compile_pattern(pattern: str, flags: str = "") -> re.Pattern:
    rf = re.IGNORECASE if "i" in flags else 0
    return re.compile(pattern, rf)


def check_forbidden_strings(
    lines: list[str], filepath: Path, rules: list[dict]
) -> list[str]:
    violations: list[str] = []
    for rule in rules:
        pat = compile_pattern(rule["pattern"], rule.get("flags", ""))
        for lineno, line in enumerate(lines, 1):
            if pat.search(line):
                violations.append(
                    f"  {rel(filepath)}:{lineno}: forbidden string "
                    f"'{rule['pattern']}' — {rule['description']}"
                )
    return violations


def check_calendar_quarters(
    lines: list[str], filepath: Path, rule: dict
) -> list[str]:
    if matches_exempt(filepath, rule.get("exempt_globs", [])):
        return []
    pat = re.compile(rule["pattern"])
    violations: list[str] = []
    for lineno, line in enumerate(lines, 1):
        if pat.search(line):
            violations.append(
                f"  {rel(filepath)}:{lineno}: calendar quarter reference "
                f"— {rule['description']}"
            )
    return violations


def check_stale_claims(
    lines: list[str], filepath: Path, rules: list[dict]
) -> list[str]:
    violations: list[str] = []
    for rule in rules:
        pat = compile_pattern(rule["pattern"], rule.get("flags", ""))
        for lineno, line in enumerate(lines, 1):
            if pat.search(line):
                violations.append(
                    f"  {rel(filepath)}:{lineno}: stale claim "
                    f"'{rule['pattern']}' — {rule['description']}"
                )
    return violations


def check_bare_ticket_ids(
    lines: list[str], filepath: Path, rule: dict
) -> list[str]:
    prefixes = rule.get("tracker_prefixes", [])
    if not prefixes:
        return []
    prefix_alt = "|".join(re.escape(p) for p in prefixes)
    pat = re.compile(rf"\b({prefix_alt})-\d+\b")
    violations: list[str] = []
    for lineno, line in enumerate(lines, 1):
        for m in pat.finditer(line):
            violations.append(
                f"  {rel(filepath)}:{lineno}: bare ticket ID "
                f"'{m.group()}' — {rule['description']}"
            )
    return violations


def main() -> int:
    rules = load_rules(RULES_PATH)
    files = scan_files(DOCS_ROOT)

    all_violations: list[str] = []

    for filepath in files:
        try:
            lines = filepath.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError as exc:
            all_violations.append(f"{filepath}: could not decode as UTF-8: {exc}")
            continue
        except OSError as exc:
            all_violations.append(f"{filepath}: could not read file: {exc}")
            continue

        all_violations.extend(
            check_forbidden_strings(lines, filepath, rules.get("forbidden_strings", []))
        )
        if "calendar_quarters" in rules:
            all_violations.extend(
                check_calendar_quarters(lines, filepath, rules["calendar_quarters"])
            )
        all_violations.extend(
            check_stale_claims(lines, filepath, rules.get("stale_claims", []))
        )
        if "bare_ticket_ids" in rules:
            all_violations.extend(
                check_bare_ticket_ids(lines, filepath, rules["bare_ticket_ids"])
            )

    if all_violations:
        print(f"docs-drift: {len(all_violations)} violation(s) found:\n")
        print("\n".join(all_violations))
        return 1

    print("docs-drift: clean ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
