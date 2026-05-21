#!/usr/bin/env python3
"""Validate migrated feature records.

The validator is intentionally scoped to directories already present under
features/. It skips the template so the repo can migrate incrementally while
still rejecting partial or inconsistent feature records as soon as they enter
the new structure.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FEATURES_DIR = ROOT / "features"
SKIP_DIRS = {"feature-template"}

REQUIRED_FILES = {
    "README.md",
    "spec.md",
    "status.md",
    "evidence.md",
    "security.md",
    "changelog.md",
}

REQUIRED_SCALARS = {
    "feature_id",
    "title",
    "status",
    "stability",
    "since",
    "owner",
    "feature_type",
    "default_surface",
    "canonical_spec",
    "implementation_path",
}

RECOMMENDED_LISTS = {"adr_refs", "security_refs", "release_lines"}

ENUMS = {
    "status": {"proposed", "active", "shipped", "deferred", "superseded"},
    "stability": {"stable", "beta", "experimental", "deprecated"},
    "feature_type": {
        "core",
        "plugin",
        "adapter",
        "sdk",
        "deployment",
        "protocol",
        "tooling",
        "docs",
    },
    "default_surface": {"default", "opt-in", "experimental", "internal", "external"},
}

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def parse_frontmatter(path: Path) -> tuple[dict[str, object], list[str]]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        return {}, [f"{path}: missing opening frontmatter delimiter"]

    try:
        end = lines[1:].index("---") + 1
    except ValueError:
        return {}, [f"{path}: missing closing frontmatter delimiter"]

    metadata: dict[str, object] = {}
    errors: list[str] = []
    current_list_key: str | None = None

    for line_no, raw in enumerate(lines[1:end], start=2):
        if not raw.strip():
            continue

        if raw.startswith("  - "):
            if current_list_key is None:
                errors.append(f"{path}:{line_no}: list item without a list key")
                continue
            value = raw[4:].strip()
            if not value:
                errors.append(f"{path}:{line_no}: empty list item")
                continue
            metadata.setdefault(current_list_key, [])
            assert isinstance(metadata[current_list_key], list)
            metadata[current_list_key].append(value)
            continue

        current_list_key = None
        if ":" not in raw:
            errors.append(f"{path}:{line_no}: expected 'key: value'")
            continue

        key, value = raw.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            errors.append(f"{path}:{line_no}: empty metadata key")
            continue
        if key in metadata:
            errors.append(f"{path}:{line_no}: duplicate metadata key '{key}'")
            continue

        if value:
            metadata[key] = value
        else:
            metadata[key] = []
            current_list_key = key

    return metadata, errors


def feature_dirs() -> list[Path]:
    if not FEATURES_DIR.exists():
        return []
    return sorted(
        path
        for path in FEATURES_DIR.iterdir()
        if path.is_dir() and path.name not in SKIP_DIRS
    )


def validate_feature(path: Path) -> tuple[dict[str, object], list[str]]:
    errors: list[str] = []

    if not SLUG_RE.fullmatch(path.name):
        errors.append(f"{path}: feature directory must use lowercase kebab case")

    missing = sorted(name for name in REQUIRED_FILES if not (path / name).is_file())
    for name in missing:
        errors.append(f"{path}: missing required file {name}")

    metadata: dict[str, object] = {}
    readme = path / "README.md"
    if readme.is_file():
        metadata, fm_errors = parse_frontmatter(readme)
        errors.extend(fm_errors)

        for field in sorted(REQUIRED_SCALARS):
            value = metadata.get(field)
            if not isinstance(value, str) or not value.strip():
                errors.append(f"{readme}: missing required scalar field '{field}'")

        for field in sorted(RECOMMENDED_LISTS):
            value = metadata.get(field)
            if value is None:
                errors.append(f"{readme}: missing recommended list field '{field}'")
            elif not isinstance(value, list) or not value:
                errors.append(f"{readme}: field '{field}' must be a non-empty list")

        feature_id = metadata.get("feature_id")
        if isinstance(feature_id, str):
            if not SLUG_RE.fullmatch(feature_id):
                errors.append(f"{readme}: feature_id must use lowercase kebab case")
            if feature_id != path.name:
                errors.append(f"{readme}: feature_id must match directory name")

        for field, allowed in ENUMS.items():
            value = metadata.get(field)
            if isinstance(value, str) and value not in allowed:
                allowed_text = ", ".join(sorted(allowed))
                errors.append(
                    f"{readme}: {field} '{value}' is not one of: {allowed_text}"
                )

    return metadata, errors


def main() -> int:
    dirs = feature_dirs()
    if not dirs:
        print("feature-records: no migrated feature directories found; template only")
        return 0

    errors: list[str] = []
    feature_ids: dict[str, Path] = {}
    canonical_specs: dict[str, Path] = {}

    for path in dirs:
        metadata, feature_errors = validate_feature(path)
        errors.extend(feature_errors)

        feature_id = metadata.get("feature_id")
        if isinstance(feature_id, str) and feature_id:
            previous = feature_ids.get(feature_id)
            if previous is not None:
                errors.append(
                    f"{path / 'README.md'}: duplicate feature_id '{feature_id}' "
                    f"also used by {previous / 'README.md'}"
                )
            feature_ids[feature_id] = path

        canonical_spec = metadata.get("canonical_spec")
        if (
            isinstance(canonical_spec, str)
            and canonical_spec
            and canonical_spec != "none"
        ):
            previous = canonical_specs.get(canonical_spec)
            if previous is not None:
                errors.append(
                    f"{path / 'README.md'}: duplicate canonical_spec "
                    f"'{canonical_spec}' also used by {previous / 'README.md'}"
                )
            canonical_specs[canonical_spec] = path

    if errors:
        print("feature-records: validation failed", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"feature-records: validated {len(dirs)} migrated feature record(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
