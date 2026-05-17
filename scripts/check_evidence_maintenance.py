#!/usr/bin/env python3
"""Validate cross-phase evidence-maintenance wiring.

This check is intentionally mechanical. It proves that the recurring maintenance
controls have documented owners/triggers and that CI still invokes the core
validators. It does not decide whether the evidence is security-sufficient.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

REQUIRED_FILES = [
    "docs/internal/evidence-maintenance.md",
    "docs/internal/dependency-currency.md",
    "docs/internal/security-evidence-registry.md",
    "docs/internal/release-cadence.md",
    "docs/internal/major-version-holds.md",
    ".github/workflows/dependency-currency.yml",
    ".github/workflows/ci.yml",
    "scripts/validate_security_evidence.py",
    "scripts/check_security_documentation.py",
]

REQUIRED_TEXT = {
    "docs/internal/evidence-maintenance.md": [
        "Dependency currency",
        "Major-version holds",
        "Security evidence registry",
        "Per-feature security docs",
        "Release security artifacts",
        "Release-Candidate Gate",
    ],
    "docs/internal/dependency-currency.md": [
        "weekly",
        "before release candidates",
        "after security advisories",
        "docs/internal/major-version-holds.md",
    ],
    "docs/internal/security-evidence-registry.md": [
        "spec/security/evidence-registry.json",
        "scripts/validate_security_evidence.py",
        "Mitigated",
    ],
    "docs/internal/release-cadence.md": [
        "Update security artifacts",
        "risk-register summary",
        "threat-model page status header",
        "CHANGELOG",
        "SBOM",
    ],
    ".github/workflows/dependency-currency.yml": [
        "schedule:",
        "workflow_dispatch:",
        "pnpm outdated",
        "uv tree --outdated",
        "retention-days:",
    ],
    ".github/workflows/ci.yml": [
        "scripts/validate_security_evidence.py",
        "scripts/check_security_documentation.py",
        "scripts/check_evidence_maintenance.py",
    ],
}


def _missing_files() -> list[str]:
    return [rel_path for rel_path in REQUIRED_FILES if not (REPO_ROOT / rel_path).exists()]


def _missing_text() -> list[str]:
    failures: list[str] = []
    for rel_path, snippets in REQUIRED_TEXT.items():
        text = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
        for snippet in snippets:
            if snippet not in text:
                failures.append(f"{rel_path}: missing required text {snippet!r}")
    return failures


def main() -> int:
    failures = [f"missing required file: {path}" for path in _missing_files()]
    if not failures:
        failures.extend(_missing_text())

    if failures:
        for failure in failures:
            print(f"evidence-maintenance: {failure}", file=sys.stderr)
        return 1

    print("OK: cross-phase evidence maintenance wiring validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
