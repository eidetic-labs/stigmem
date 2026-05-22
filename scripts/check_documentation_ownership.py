#!/usr/bin/env python3
"""Validate the high-signal documentation ownership inventory."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OWNERSHIP_DOC = ROOT / "docs" / "internal" / "documentation-ownership.md"

REQUIRED_PATH_TOKENS = [
    "README.md",
    "LIMITATIONS.md",
    "SECURITY.md",
    "CHANGELOG.md",
    "ROADMAP.md",
    "CONTRIBUTING.md",
    "OPERATING.md",
    "MAINTAINERS.md",
    "LOG.md",
    "features/<feature>/README.md",
    "features/<feature>/spec.md",
    "features/<feature>/status.md",
    "features/<feature>/evidence.md",
    "features/<feature>/security.md",
    "features/<feature>/changelog.md",
    "spec/specs/",
    "experimental/<feature>/",
    "docs/internal/documentation-ownership.md",
    "docs/internal/feature-tracker.md",
    "docs/internal/features/feature-record-migration.md",
    "docs/internal/roadmap-standards.md",
    "docs/internal/releases/",
    "docs/internal/release-cadence.md",
    "docs/internal/development.md",
    "docs/internal/evidence-maintenance.md",
    "docs/internal/major-version-holds.md",
    "docs/internal/security-evidence-registry*.md",
    "docs/docs/reference/api/generated/",
    "spec/PROTOCOL.md",
    "docs/compatibility-matrix.yaml",
    "archive/",
    "docs/archive/",
    "spec/archive/",
]

REQUIRED_SECTION_HEADINGS = [
    "## Canonical Homes",
    "## Document Classes",
    "## Current Ownership Inventory",
    "## Release Security Rule",
    "## Review Checklist",
    "## Validation",
]


def main() -> int:
    if not OWNERSHIP_DOC.exists():
        print(f"documentation-ownership: missing {OWNERSHIP_DOC}", file=sys.stderr)
        return 1

    text = OWNERSHIP_DOC.read_text(encoding="utf-8")
    errors: list[str] = []

    for heading in REQUIRED_SECTION_HEADINGS:
        if heading not in text:
            errors.append(f"{OWNERSHIP_DOC.relative_to(ROOT)}: missing heading {heading!r}")

    for token in REQUIRED_PATH_TOKENS:
        if f"`{token}`" not in text:
            errors.append(
                f"{OWNERSHIP_DOC.relative_to(ROOT)}: missing ownership row/token `{token}`"
            )

    if "TBD" in text or "TODO" in text:
        errors.append(
            f"{OWNERSHIP_DOC.relative_to(ROOT)}: ownership inventory must not contain TBD/TODO"
        )

    if errors:
        print("documentation-ownership: validation failed", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("documentation-ownership: high-signal ownership inventory passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
