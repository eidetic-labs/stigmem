#!/usr/bin/env python3
"""Validate public feature projections against ADR-020 feature records."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FEATURES_DIR = ROOT / "features"
FEATURE_TRACKER = ROOT / "docs" / "internal" / "feature-tracker.md"
FEATURE_MATRIX = ROOT / "docs" / "docs" / "concepts" / "features.md"
EXPERIMENTAL_INDEX = ROOT / "docs" / "docs" / "reference" / "experimental-features.md"

SKIP_DIRS = {"feature-template"}
EXPERIMENTAL_SURFACES = {"opt-in", "experimental", "external", "internal"}


@dataclass(frozen=True)
class FeatureRecord:
    feature_id: str
    title: str
    stability: str
    default_surface: str
    canonical_spec: str
    path: Path


def parse_frontmatter(path: Path) -> dict[str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        raise ValueError(f"{path}: missing frontmatter")
    try:
        end = lines[1:].index("---") + 1
    except ValueError as exc:
        raise ValueError(f"{path}: unterminated frontmatter") from exc

    metadata: dict[str, str] = {}
    for raw in lines[1:end]:
        if not raw.strip() or raw.startswith("  - "):
            continue
        if ":" not in raw:
            continue
        key, value = raw.split(":", 1)
        value = value.strip()
        if value:
            metadata[key.strip()] = value
    return metadata


def load_feature_records() -> dict[str, FeatureRecord]:
    records: dict[str, FeatureRecord] = {}
    for feature_dir in sorted(FEATURES_DIR.iterdir()):
        if not feature_dir.is_dir() or feature_dir.name in SKIP_DIRS:
            continue
        readme = feature_dir / "README.md"
        if not readme.is_file():
            continue
        metadata = parse_frontmatter(readme)
        required = [
            "feature_id",
            "title",
            "stability",
            "default_surface",
            "canonical_spec",
        ]
        missing = [field for field in required if not metadata.get(field)]
        if missing:
            raise ValueError(f"{readme}: missing projection field(s): {', '.join(missing)}")
        record = FeatureRecord(
            feature_id=metadata["feature_id"],
            title=metadata["title"],
            stability=metadata["stability"],
            default_surface=metadata["default_surface"],
            canonical_spec=metadata["canonical_spec"],
            path=feature_dir,
        )
        records[record.feature_id] = record
    return records


def migrated_feature_ids() -> set[str]:
    text = FEATURE_TRACKER.read_text(encoding="utf-8")
    ids: set[str] = set()
    for raw in text.splitlines():
        if not raw.startswith("| `"):
            continue
        cells = [cell.strip() for cell in raw.strip("|").split("|")]
        if len(cells) < 9:
            continue
        feature_id = _strip_code(cells[0])
        status = _strip_code(cells[8])
        if status == "migrated":
            ids.add(feature_id)
    return ids


def _strip_code(value: str) -> str:
    value = value.strip()
    if value.startswith("`") and value.endswith("`"):
        return value[1:-1]
    return value


def normalized(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower())


def projection_tokens(record: FeatureRecord) -> list[str]:
    tokens = [record.feature_id, record.title]
    if record.canonical_spec != "none":
        tokens.append(record.canonical_spec)
    tokens.append(f"features/{record.feature_id}")
    return tokens


def mentions_record(surface_text: str, record: FeatureRecord) -> bool:
    surface = normalized(surface_text)
    return any(normalized(token).strip() in surface for token in projection_tokens(record))


def validate() -> list[str]:
    errors: list[str] = []
    records = load_feature_records()
    migrated_ids = migrated_feature_ids()
    feature_matrix = FEATURE_MATRIX.read_text(encoding="utf-8")
    experimental_index = EXPERIMENTAL_INDEX.read_text(encoding="utf-8")

    missing_records = sorted(migrated_ids - set(records))
    for feature_id in missing_records:
        errors.append(f"{FEATURE_TRACKER}: migrated feature '{feature_id}' has no record")

    for feature_id in sorted(migrated_ids & set(records)):
        record = records[feature_id]
        if not mentions_record(feature_matrix, record):
            errors.append(
                f"{FEATURE_MATRIX}: missing migrated feature projection for "
                f"'{feature_id}'"
            )
        if record.default_surface in EXPERIMENTAL_SURFACES or record.stability == "experimental":
            if not mentions_record(experimental_index, record):
                errors.append(
                    f"{EXPERIMENTAL_INDEX}: missing experimental feature projection for "
                    f"'{feature_id}'"
                )

    return errors


def main() -> int:
    try:
        errors = validate()
    except ValueError as exc:
        print(f"feature-projections: {exc}", file=sys.stderr)
        return 1

    if errors:
        print("feature-projections: validation failed", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(
        "feature-projections: public feature matrix and experimental index "
        "match migrated feature records"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
