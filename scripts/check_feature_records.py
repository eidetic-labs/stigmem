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
EXPERIMENTAL_DIR = ROOT / "experimental"
FEATURE_INVENTORY = ROOT / "docs" / "internal" / "feature-tracker.md"
SKIP_DIRS = {"feature-template"}
EXPERIMENTAL_SKIP_DIRS = {"__pycache__", "node_modules", ".pytest_cache", ".next", ".turbo"}

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

INVENTORY_STATUSES = {"migrated", "pending", "deferred", "superseded"}
INVENTORY_HEADING = "## Feature Record Migration Inventory"
INVENTORY_HEADERS = [
    "Feature ID",
    "Feature",
    "Type",
    "Stability",
    "Default surface",
    "Canonical spec",
    "Legacy owner",
    "Target record",
    "Migration status",
    "Horizon",
    "Notes",
]

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
        path for path in FEATURES_DIR.iterdir() if path.is_dir() and path.name not in SKIP_DIRS
    )


def _cell_text(value: str) -> str:
    value = value.strip()
    if value.startswith("`") and value.endswith("`"):
        return value[1:-1]
    if value.startswith("[`") and "`]" in value:
        start = value.find("`") + 1
        end = value.find("`]", start)
        return value[start:end]
    if value.startswith("[") and "](" in value:
        return value[1 : value.find("](")]
    return value


def _parse_inventory_table() -> tuple[list[dict[str, str]], list[str]]:
    if not FEATURE_INVENTORY.exists():
        return [], [f"{FEATURE_INVENTORY}: missing feature migration inventory"]

    lines = FEATURE_INVENTORY.read_text(encoding="utf-8").splitlines()
    try:
        start = lines.index(INVENTORY_HEADING)
    except ValueError:
        return [], [f"{FEATURE_INVENTORY}: missing '{INVENTORY_HEADING}' section"]

    table_lines: list[str] = []
    for raw in lines[start + 1 :]:
        if raw.startswith("|"):
            table_lines.append(raw)
        elif table_lines:
            break

    if len(table_lines) < 3:
        return [], [f"{FEATURE_INVENTORY}: inventory table is missing or empty"]

    headers = [_cell_text(cell) for cell in table_lines[0].strip("|").split("|")]
    if headers != INVENTORY_HEADERS:
        return [], [
            f"{FEATURE_INVENTORY}: inventory headers must be: {', '.join(INVENTORY_HEADERS)}"
        ]

    rows: list[dict[str, str]] = []
    errors: list[str] = []
    for offset, raw in enumerate(table_lines[2:], start=start + 3):
        cells = [_cell_text(cell) for cell in raw.strip("|").split("|")]
        if len(cells) != len(INVENTORY_HEADERS):
            errors.append(f"{FEATURE_INVENTORY}:{offset}: inventory row has {len(cells)} cells")
            continue
        rows.append(dict(zip(INVENTORY_HEADERS, cells, strict=True)))

    return rows, errors


def validate_inventory(feature_metadata: dict[str, dict[str, object]]) -> list[str]:
    rows, errors = _parse_inventory_table()
    if errors:
        return errors
    migrated_feature_ids = set(feature_metadata)

    seen: set[str] = set()
    legacy_experimental_ids: set[str] = set()
    for row in rows:
        feature_id = row["Feature ID"]
        feature_type = row["Type"]
        stability = row["Stability"]
        default_surface = row["Default surface"]
        status = row["Migration status"]
        canonical_spec = row["Canonical spec"]
        legacy_owner = row["Legacy owner"]
        target = row["Target record"]

        if not SLUG_RE.fullmatch(feature_id):
            errors.append(f"{FEATURE_INVENTORY}: feature id '{feature_id}' must use kebab case")
        if feature_id in seen:
            errors.append(f"{FEATURE_INVENTORY}: duplicate inventory feature id '{feature_id}'")
        seen.add(feature_id)

        if feature_type not in ENUMS["feature_type"]:
            errors.append(f"{FEATURE_INVENTORY}: {feature_id} has invalid type '{feature_type}'")
        if stability not in ENUMS["stability"]:
            errors.append(f"{FEATURE_INVENTORY}: {feature_id} has invalid stability '{stability}'")
        if default_surface not in ENUMS["default_surface"]:
            errors.append(
                f"{FEATURE_INVENTORY}: {feature_id} has invalid default surface '{default_surface}'"
            )
        if status not in INVENTORY_STATUSES:
            errors.append(f"{FEATURE_INVENTORY}: {feature_id} has invalid status '{status}'")
        if canonical_spec != "none" and not re.fullmatch(r"Spec-(?:X)?[0-9]+-.+", canonical_spec):
            errors.append(
                f"{FEATURE_INVENTORY}: {feature_id} canonical spec '{canonical_spec}' "
                "must be 'none' or a Spec-* id"
            )
        if not target.startswith("features/") or not target.endswith("/"):
            errors.append(f"{FEATURE_INVENTORY}: {feature_id} target must be features/<slug>/")
        expected_target = f"features/{feature_id}/"
        if target != expected_target:
            errors.append(f"{FEATURE_INVENTORY}: {feature_id} target must be {expected_target}")
        if legacy_owner.startswith("experimental/"):
            legacy_id = legacy_owner.removeprefix("experimental/").strip("/")
            if legacy_id:
                legacy_experimental_ids.add(legacy_id)

        target_path = ROOT / target
        if status == "migrated":
            if feature_id not in migrated_feature_ids:
                errors.append(
                    f"{FEATURE_INVENTORY}: migrated row '{feature_id}' has no validated "
                    "feature record"
                )
            if not target_path.is_dir():
                errors.append(f"{FEATURE_INVENTORY}: migrated target does not exist: {target}")
            else:
                metadata = feature_metadata.get(feature_id, {})
                expected_fields = {
                    "Feature": metadata.get("title"),
                    "Type": metadata.get("feature_type"),
                    "Stability": metadata.get("stability"),
                    "Default surface": metadata.get("default_surface"),
                    "Canonical spec": metadata.get("canonical_spec"),
                }
                for field, expected in expected_fields.items():
                    if isinstance(expected, str) and row[field] != expected:
                        errors.append(
                            f"{FEATURE_INVENTORY}: {feature_id} {field} must match "
                            f"feature record value '{expected}'"
                        )
        elif legacy_owner != "none" and not (ROOT / legacy_owner).exists():
            errors.append(
                f"{FEATURE_INVENTORY}: legacy owner for non-migrated row '{feature_id}' "
                f"does not exist: {legacy_owner}"
            )

    untracked_feature_records = sorted(migrated_feature_ids - seen)
    for feature_id in untracked_feature_records:
        errors.append(
            f"{FEATURE_INVENTORY}: feature record '{feature_id}' is missing from inventory"
        )

    errors.extend(validate_experimental_inventory(legacy_experimental_ids))
    return errors


def validate_experimental_inventory(legacy_experimental_ids: set[str]) -> list[str]:
    if not EXPERIMENTAL_DIR.exists():
        return []

    errors: list[str] = []
    experimental_ids = {
        path.name
        for path in EXPERIMENTAL_DIR.iterdir()
        if path.is_dir()
        and not path.name.startswith(".")
        and path.name not in EXPERIMENTAL_SKIP_DIRS
    }
    missing = sorted(experimental_ids - legacy_experimental_ids)
    for feature_id in missing:
        errors.append(f"{FEATURE_INVENTORY}: experimental/{feature_id}/ has no inventory row")
    return errors


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
                errors.append(f"{readme}: {field} '{value}' is not one of: {allowed_text}")

    return metadata, errors


def main() -> int:
    dirs = feature_dirs()
    if not dirs:
        print("feature-records: no migrated feature directories found; template only")
        return 0

    errors: list[str] = []
    feature_paths: dict[str, Path] = {}
    feature_metadata: dict[str, dict[str, object]] = {}
    canonical_specs: dict[str, Path] = {}

    for path in dirs:
        metadata, feature_errors = validate_feature(path)
        errors.extend(feature_errors)

        feature_id = metadata.get("feature_id")
        if isinstance(feature_id, str) and feature_id:
            previous = feature_paths.get(feature_id)
            if previous is not None:
                errors.append(
                    f"{path / 'README.md'}: duplicate feature_id '{feature_id}' "
                    f"also used by {previous / 'README.md'}"
                )
            feature_paths[feature_id] = path
            feature_metadata[feature_id] = metadata

        canonical_spec = metadata.get("canonical_spec")
        if isinstance(canonical_spec, str) and canonical_spec and canonical_spec != "none":
            previous = canonical_specs.get(canonical_spec)
            if previous is not None:
                errors.append(
                    f"{path / 'README.md'}: duplicate canonical_spec "
                    f"'{canonical_spec}' also used by {previous / 'README.md'}"
                )
            canonical_specs[canonical_spec] = path

    errors.extend(validate_inventory(feature_metadata))

    if errors:
        print("feature-records: validation failed", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"feature-records: validated {len(dirs)} migrated feature record(s) and inventory")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
