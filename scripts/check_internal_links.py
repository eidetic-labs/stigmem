#!/usr/bin/env python3
"""Validate stale planning filenames and, optionally, markdown links.

Intended to be copied to `scripts/check_internal_links.py` in the Stigmem repo.
It catches two common planning-doc failures:

1. Stale Desktop-style artifact names after files are moved into repo paths.
2. Relative markdown links that point nowhere, when `--check-links` is enabled.

Internal-Comms contains draft artifacts that intentionally reference future
paths in the Stigmem repo. For that corpus, run the default stale-name check.
After copying artifacts into the Stigmem repo, enable `--check-links`.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Sequence
from pathlib import Path

LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")

STALE_PATTERNS = [
    "stigmem-openclaw-audit.md",
    "stigmem-openclaw-adapter-v0.9.py",
    "stigmem-openclaw-README-v0.9.md",
    "stigmem-strengthening-plan.md",
    "stigmem-version-prioritization.md",
    "stigmem-repo-structure-review.md",
    "stigmem-feature-extraction-analysis.md",
]


def iter_markdown_files(root: Path) -> Sequence[Path]:
    skip = {".git", ".venv", "node_modules", "dist", "build"}
    files: list[Path] = []
    for path in root.rglob("*.md"):
        if any(part in skip for part in path.parts):
            continue
        files.append(path)
    return files


def normalize_link_target(raw: str) -> str | None:
    target = raw.strip()
    if not target or target.startswith("#"):
        return None
    if "://" in target or target.startswith("mailto:"):
        return None
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    return target.split("#", 1)[0]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".", help="repository root")
    parser.add_argument(
        "--check-links",
        action="store_true",
        help="also fail on broken relative markdown links",
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    errors: list[str] = []

    for md_file in iter_markdown_files(root):
        text = md_file.read_text(encoding="utf-8")
        rel = md_file.relative_to(root)

        for stale in STALE_PATTERNS:
            if stale in text:
                errors.append(f"{rel}: stale artifact name found: {stale}")

        if args.check_links:
            for match in LINK_RE.finditer(text):
                target = normalize_link_target(match.group(1))
                if target is None:
                    continue
                candidate = (md_file.parent / target).resolve()
                if not str(candidate).startswith(str(root)):
                    continue
                if not candidate.exists():
                    errors.append(f"{rel}: broken link target: {match.group(1)}")

    if not errors:
        return 0

    print("INTERNAL LINK CHECK FAILED", file=sys.stderr)
    for error in errors:
        print(f"  {error}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
