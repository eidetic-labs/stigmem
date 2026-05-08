#!/usr/bin/env python3
"""Translate a stigmem release version between PEP 440 and semver spellings.

Per ADR-019 §Per-ecosystem spelling: stigmem releases are spelled differently
in different ecosystems. The git tag uses PEP 440 shorthand (e.g. v0.9.0a1).
This script translates that shorthand to:
  - canonical PEP 440 (drops the leading v): 0.9.0a1
  - canonical semver: 0.9.0-alpha.1

Used by .github/workflows/publish.yml to stamp the right form into npm
package.json (semver) and GHCR image tags (both forms, for adopter
flexibility).

Mapping:
  PEP 440        Semver
  ─────────      ─────────────
  X.Y.ZaN     →  X.Y.Z-alpha.N
  X.Y.ZbN     →  X.Y.Z-beta.N
  X.Y.ZrcN    →  X.Y.Z-rc.N
  X.Y.Z       →  X.Y.Z         (final releases unchanged)

Usage:
    python scripts/translate_version.py <tag>           # prints both forms
    python scripts/translate_version.py <tag> --pep440  # prints PEP 440 only
    python scripts/translate_version.py <tag> --semver  # prints semver only
    python scripts/translate_version.py <tag> --gh-output  # writes to $GITHUB_OUTPUT

Examples:
    $ python scripts/translate_version.py v0.9.0a1
    pep440=0.9.0a1
    semver=0.9.0-alpha.1

    $ python scripts/translate_version.py v1.0.0 --pep440
    1.0.0
"""

from __future__ import annotations

import argparse
import os
import re
import sys

# (X.Y.Z) optional (a|b|rc)(N) — anchored
PEP440_RE = re.compile(r"^(?P<x>\d+)\.(?P<y>\d+)\.(?P<z>\d+)(?:(?P<kind>a|b|rc)(?P<n>\d+))?$")

PEP440_TO_SEMVER = {"a": "alpha", "b": "beta", "rc": "rc"}


def parse(tag: str) -> tuple[str, str]:
    """Return (pep440, semver) forms. Raises ValueError on parse failure."""
    s = tag.strip().lstrip("v")
    m = PEP440_RE.match(s)
    if not m:
        raise ValueError(
            f"unparseable release tag: {tag!r} (expected v<MAJOR>.<MINOR>.<PATCH>"
            f" optionally followed by aN, bN, or rcN — e.g. v0.9.0a1, v1.0.0rc2, v1.0.0)"
        )
    base = f"{m['x']}.{m['y']}.{m['z']}"
    kind = m["kind"]
    n = m["n"]

    if not kind:
        # final release: same in both ecosystems
        return base, base

    pep440 = f"{base}{kind}{n}"
    semver_kind = PEP440_TO_SEMVER[kind]
    semver = f"{base}-{semver_kind}.{n}"
    return pep440, semver


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag", help="git tag, e.g. v0.9.0a1")
    fmt = parser.add_mutually_exclusive_group()
    fmt.add_argument("--pep440", action="store_true")
    fmt.add_argument("--semver", action="store_true")
    parser.add_argument(
        "--gh-output",
        action="store_true",
        help="Append pep440=<x> and semver=<x> lines to the file at $GITHUB_OUTPUT",
    )
    args = parser.parse_args()

    try:
        pep440, semver = parse(args.tag)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    if args.pep440:
        print(pep440)
    elif args.semver:
        print(semver)
    else:
        print(f"pep440={pep440}")
        print(f"semver={semver}")

    if args.gh_output:
        out_path = os.environ.get("GITHUB_OUTPUT")
        if not out_path:
            print("error: --gh-output requires GITHUB_OUTPUT env var", file=sys.stderr)
            return 1
        with open(out_path, "a", encoding="utf-8") as f:
            f.write(f"pep440={pep440}\n")
            f.write(f"semver={semver}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
