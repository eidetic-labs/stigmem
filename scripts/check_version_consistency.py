#!/usr/bin/env python3
"""Version consistency check (manifest-driven, per ADR-019).

Reads release/version-surfaces.yaml, derives the canonical release from the
PEP 440 anchor (root pyproject.toml), then asserts every other surface in the
manifest references the same release — normalized across PEP 440 and semver
spellings to a canonical key.

Per ADR-001: version drift is a hard error.
Per ADR-019: per-ecosystem spelling is expected; the normalizer maps
    0.9.0a1 (PEP 440) and 0.9.0-alpha.1 (semver) to the same canonical key.

Usage:
    python scripts/check_version_consistency.py
    python scripts/check_version_consistency.py --verbose

Exit codes:
    0 — every surface in the manifest agrees with the canonical release
    1 — at least one mismatch (details on stderr)
    2 — environmental error (missing manifest, missing PyYAML, etc.)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.stderr.write("ERROR: PyYAML required. Install: pip install pyyaml\n")
    sys.exit(2)

try:
    import tomllib  # Python 3.11+
except ImportError:  # pragma: no cover
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError:
        sys.stderr.write("ERROR: tomllib (3.11+) or tomli is required.\n")
        sys.exit(2)


REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST = REPO_ROOT / "release" / "version-surfaces.yaml"
ANCHOR = REPO_ROOT / "pyproject.toml"  # Canonical release source: PEP 440 string here

# ---------------------------------------------------------------------------
# Normalizer — maps PEP 440 and semver spellings to a single canonical key
# ---------------------------------------------------------------------------

PEP440_PRE = re.compile(
    r"^(?P<release>\d+\.\d+\.\d+)"
    r"(?:(?P<kind>a|b|rc)(?P<n>\d+))?$"
)

SEMVER_PRE = re.compile(
    r"^(?P<release>\d+\.\d+\.\d+)"
    r"(?:-(?P<kind>alpha|beta|rc)\.(?P<n>\d+))?$"
)


def normalize(version_string: str) -> str | None:
    """Return canonical key (e.g. '0.9.0.alpha.1') or None if unparseable.

    Maps PEP 440 (0.9.0a1) and semver (0.9.0-alpha.1) and shorthand (v0.9.0a1)
    to a single canonical key for cross-ecosystem comparison.
    """
    if not version_string:
        return None
    s = version_string.strip().lstrip("v")

    # PEP 440 form
    m = PEP440_PRE.match(s)
    if m:
        release = m.group("release")
        kind = m.group("kind")
        n = m.group("n")
        if not kind:
            return f"{release}"
        kind_full = {"a": "alpha", "b": "beta", "rc": "rc"}[kind]
        return f"{release}.{kind_full}.{n}"

    # Semver form
    m = SEMVER_PRE.match(s)
    if m:
        release = m.group("release")
        kind = m.group("kind")
        n = m.group("n")
        if not kind:
            return f"{release}"
        return f"{release}.{kind}.{n}"

    return None


# ---------------------------------------------------------------------------
# Per-spelling extractors — read the version string from a file at a given field
# ---------------------------------------------------------------------------


def extract_toml(path: Path, field: str) -> str | None:
    """Read a dotted field from a TOML file. Field path: 'project.version'."""
    if not path.exists():
        return None
    data: Any = tomllib.loads(path.read_text())
    parts = field.split(".")
    cur = data
    for p in parts:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(p)
        if cur is None:
            return None
    return str(cur) if cur is not None else None


def extract_json(path: Path, field: str) -> str | None:
    """Read a dotted field from a JSON file. Field path: 'project.version' or 'version'."""
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    parts = field.split(".")
    cur: Any = data
    for p in parts:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(p)
        if cur is None:
            return None
    return str(cur) if cur is not None else None


def extract_yaml(path: Path, field: str) -> str | None:
    """Read a dotted field from a YAML file. Field path: 'appVersion'."""
    if not path.exists():
        return None
    data = yaml.safe_load(path.read_text()) or {}
    parts = field.split(".")
    cur = data
    for p in parts:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(p)
        if cur is None:
            return None
    return str(cur) if cur is not None else None


def extract_version_from_file(file_path: Path, field: str | None) -> str | None:
    """Dispatch by extension. Field is required for structured files."""
    if not field:
        return None
    suffix = file_path.suffix.lower()
    if suffix == ".toml":
        return extract_toml(file_path, field)
    if suffix == ".json":
        return extract_json(file_path, field)
    if suffix in {".yaml", ".yml"}:
        return extract_yaml(file_path, field)
    return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def fail(msg: str) -> None:
    sys.stderr.write(f"version-consistency: {msg}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    if not MANIFEST.exists():
        fail(f"manifest not found at {MANIFEST.relative_to(REPO_ROOT)}")
        return 2

    try:
        manifest = yaml.safe_load(MANIFEST.read_text())
    except yaml.YAMLError as e:
        fail(f"YAML parse error in manifest: {e}")
        return 2

    surfaces = manifest.get("surfaces", []) if isinstance(manifest, dict) else []
    if not surfaces:
        fail("no surfaces in manifest")
        return 2

    # Anchor: read root pyproject.toml as the canonical release source
    canonical = extract_toml(ANCHOR, "project.version")
    if not canonical:
        fail(f"could not read project.version from {ANCHOR.relative_to(REPO_ROOT)}")
        return 2
    canonical_key = normalize(canonical)
    if not canonical_key:
        fail(f"anchor version {canonical!r} is not a parseable PEP 440 / semver string")
        return 2

    if args.verbose:
        print(f"Canonical (anchor): {canonical} → key {canonical_key}")

    mismatches: list[tuple[str, str, str | None, str | None]] = []
    skipped: list[str] = []
    checked = 0

    for entry in surfaces:
        sid = entry["id"]

        # Skip retired (tombstoned) entries
        if entry.get("retired"):
            skipped.append(f"{sid} (retired {entry['retired']})")
            continue

        # File-backed surfaces only — protocol-only surfaces (no file) are documented
        # but not version-checked here; they're enforced at runtime by their spec.
        file_rel = entry.get("file")
        field = entry.get("field")
        if not file_rel or not field:
            skipped.append(f"{sid} (no file/field; protocol-only)")
            continue

        # Documentation surfaces with `spelling: shorthand` and free-form prose
        # files (README, CHANGELOG, LIMITATIONS, SECURITY) need a different
        # extractor — defer to a future enhancement (regex match against
        # the canonical release inside a known anchor line). Skip for now
        # with a clear message rather than a false pass.
        kind = entry.get("kind")
        suffix = Path(file_rel).suffix.lower()
        if kind == "documentation" and suffix == ".md":
            skipped.append(f"{sid} (markdown prose; not yet checked)")
            continue
        if kind == "internal-protocol" and suffix == ".py":
            skipped.append(f"{sid} (Python source; spec-defined, not yet checked)")
            continue

        file_path = REPO_ROOT / file_rel
        actual = extract_version_from_file(file_path, field)
        actual_key = normalize(actual) if actual else None

        checked += 1
        if args.verbose:
            print(f"  {sid:<32}  {file_rel}::{field}  =  {actual!r}  → {actual_key}")

        if actual_key != canonical_key:
            mismatches.append((sid, file_rel, actual, actual_key))

    if mismatches:
        fail(f"\n{len(mismatches)} mismatch(es) against canonical {canonical} (key={canonical_key}):")
        for sid, file_rel, actual, actual_key in mismatches:
            fail(f"  {sid:<32}  {file_rel:<40}  got {actual!r} (key={actual_key})")
        return 1

    print(
        f"OK: {checked} surface(s) match canonical {canonical} (key={canonical_key}). "
        f"{len(skipped)} skipped (deferred or retired)."
    )
    if args.verbose and skipped:
        for s in skipped:
            print(f"  skipped: {s}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
