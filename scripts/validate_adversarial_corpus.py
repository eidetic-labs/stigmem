"""Validate ADR-015 adversarial corpus manifests and pattern files."""

from __future__ import annotations

import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
CORPUS_ROOT = ROOT / "data" / "conformance" / "adversarial" / "corpus-v1"
MANIFEST_PATH = CORPUS_ROOT / "manifest.yaml"
CATEGORIES_DIR = CORPUS_ROOT / "categories"

REQUIRED_PATTERN_FIELDS = {
    "id",
    "category",
    "severity",
    "input",
    "expected_behavior",
    "source",
    "added_in_corpus_version",
}
REQUIRED_EXPECTED_BEHAVIOR_FIELDS = {"prohibited", "required"}


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected YAML mapping")
    return data


def _require_string(data: dict[str, Any], field: str, path: Path) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path}: field {field!r} must be a non-empty string")
    return value


def _require_string_list(data: dict[str, Any], field: str, path: Path) -> list[str]:
    value = data.get(field)
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) or not item.strip() for item in value)
    ):
        raise ValueError(f"{path}: field {field!r} must be a non-empty string list")
    return value


def _validate_manifest(manifest: dict[str, Any]) -> tuple[str, set[str], set[str]]:
    version = _require_string(manifest, "version", MANIFEST_PATH)
    severities = manifest.get("severity_weights")
    if not isinstance(severities, dict) or not severities:
        raise ValueError(f"{MANIFEST_PATH}: severity_weights must be a non-empty mapping")
    severity_names = set(severities)
    for severity, weight in severities.items():
        if not isinstance(severity, str) or not isinstance(weight, int) or weight <= 0:
            raise ValueError(
                f"{MANIFEST_PATH}: severity_weights values must be positive integers"
            )

    categories = manifest.get("categories")
    if not isinstance(categories, list) or not categories:
        raise ValueError(f"{MANIFEST_PATH}: categories must be a non-empty list")

    category_ids: set[str] = set()
    for index, category in enumerate(categories):
        if not isinstance(category, dict):
            raise ValueError(f"{MANIFEST_PATH}: category {index} must be a mapping")
        category_id = _require_string(category, "id", MANIFEST_PATH)
        _require_string(category, "slug", MANIFEST_PATH)
        _require_string(category, "title", MANIFEST_PATH)
        if category_id in category_ids:
            raise ValueError(f"{MANIFEST_PATH}: duplicate category id {category_id}")
        category_ids.add(category_id)

    return version, severity_names, category_ids


def _iter_pattern_paths(category_ids: Iterable[str]) -> Iterable[Path]:
    for category_id in sorted(category_ids):
        category_dir = CATEGORIES_DIR / category_id
        if not category_dir.is_dir():
            raise ValueError(f"{category_dir}: category directory missing")
        pattern_paths = sorted(category_dir.glob("*.yaml"))
        if not pattern_paths:
            raise ValueError(f"{category_dir}: expected at least one pattern")
        yield from pattern_paths


def _validate_pattern(
    path: Path,
    *,
    corpus_version: str,
    categories: set[str],
    severities: set[str],
    seen_ids: set[str],
) -> None:
    pattern = _load_yaml(path)
    missing = REQUIRED_PATTERN_FIELDS - set(pattern)
    if missing:
        raise ValueError(f"{path}: missing required fields {sorted(missing)}")

    pattern_id = _require_string(pattern, "id", path)
    if pattern_id in seen_ids:
        raise ValueError(f"{path}: duplicate pattern id {pattern_id}")
    seen_ids.add(pattern_id)

    category = _require_string(pattern, "category", path)
    if category not in categories:
        raise ValueError(f"{path}: unknown category {category}")
    if path.parent.name != category:
        raise ValueError(f"{path}: category field must match parent directory")

    severity = _require_string(pattern, "severity", path)
    if severity not in severities:
        raise ValueError(f"{path}: unknown severity {severity}")

    _require_string(pattern, "input", path)
    _require_string(pattern, "source", path)
    added_in = _require_string(pattern, "added_in_corpus_version", path)
    if added_in != corpus_version:
        raise ValueError(
            f"{path}: added_in_corpus_version must match manifest version {corpus_version}"
        )

    expected_behavior = pattern.get("expected_behavior")
    if not isinstance(expected_behavior, dict):
        raise ValueError(f"{path}: expected_behavior must be a mapping")
    missing_behavior = REQUIRED_EXPECTED_BEHAVIOR_FIELDS - set(expected_behavior)
    if missing_behavior:
        raise ValueError(
            f"{path}: expected_behavior missing fields {sorted(missing_behavior)}"
        )
    _require_string_list(expected_behavior, "prohibited", path)
    _require_string_list(expected_behavior, "required", path)


def validate() -> int:
    manifest = _load_yaml(MANIFEST_PATH)
    corpus_version, severities, categories = _validate_manifest(manifest)
    seen_ids: set[str] = set()

    for path in _iter_pattern_paths(categories):
        _validate_pattern(
            path,
            corpus_version=corpus_version,
            categories=categories,
            severities=severities,
            seen_ids=seen_ids,
        )

    print(
        f"OK: {corpus_version} contains {len(seen_ids)} patterns across "
        f"{len(categories)} categories"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(validate())
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
