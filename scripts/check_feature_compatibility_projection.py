#!/usr/bin/env python3
"""Validate compatibility projections against feature records."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEATURES_DIR = ROOT / "features"
COMPATIBILITY_YAML = ROOT / "docs" / "compatibility-matrix.yaml"
COMPATIBILITY_PAGE = ROOT / "docs" / "docs" / "operators" / "compatibility.md"
SKIP_DIRS = {"feature-template"}


@dataclass(frozen=True)
class FeatureCompatibilityRecord:
    feature_id: str
    title: str
    stability: str
    default_surface: str
    feature_type: str
    implementation_path: str
    package: str
    release_lines: tuple[str, ...]
    path: Path

    @property
    def readme_relpath(self) -> str:
        return (self.path / "README.md").relative_to(ROOT).as_posix()


def parse_frontmatter(path: Path) -> dict[str, object]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        raise ValueError(f"{path}: missing frontmatter")
    try:
        end = lines[1:].index("---") + 1
    except ValueError as exc:
        raise ValueError(f"{path}: unterminated frontmatter") from exc

    metadata: dict[str, object] = {}
    current_list: str | None = None
    for raw in lines[1:end]:
        if not raw.strip():
            continue
        if raw.startswith("  - "):
            if current_list is None:
                raise ValueError(f"{path}: list item without list key: {raw}")
            item = raw[4:].strip()
            if not item:
                raise ValueError(f"{path}: empty list item in {current_list}")
            values = metadata.setdefault(current_list, [])
            if not isinstance(values, list):
                raise ValueError(f"{path}: {current_list} mixes scalar and list values")
            values.append(item)
            continue

        current_list = None
        if ":" not in raw:
            continue
        key, value = raw.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value:
            metadata[key] = value
        else:
            metadata[key] = []
            current_list = key
    return metadata


def load_feature_compatibility_records() -> list[FeatureCompatibilityRecord]:
    records: list[FeatureCompatibilityRecord] = []
    for feature_dir in sorted(FEATURES_DIR.iterdir()):
        if not feature_dir.is_dir() or feature_dir.name in SKIP_DIRS:
            continue
        readme = feature_dir / "README.md"
        if not readme.is_file():
            continue
        metadata = parse_frontmatter(readme)
        required_scalars = [
            "feature_id",
            "title",
            "stability",
            "default_surface",
            "feature_type",
            "implementation_path",
        ]
        missing = [
            field
            for field in required_scalars
            if not isinstance(metadata.get(field), str) or not metadata[field]
        ]
        if missing:
            raise ValueError(f"{readme}: missing compatibility field(s): {', '.join(missing)}")
        package = metadata.get("package", "none")
        release_lines = metadata.get("release_lines")
        if not isinstance(package, str) or not package:
            raise ValueError(f"{readme}: package must be a scalar")
        if not isinstance(release_lines, list) or not release_lines:
            raise ValueError(f"{readme}: release_lines must be a non-empty list")
        releases = tuple(line for line in release_lines if isinstance(line, str))
        records.append(
            FeatureCompatibilityRecord(
                feature_id=str(metadata["feature_id"]),
                title=str(metadata["title"]),
                stability=str(metadata["stability"]),
                default_surface=str(metadata["default_surface"]),
                feature_type=str(metadata["feature_type"]),
                implementation_path=str(metadata["implementation_path"]),
                package=package,
                release_lines=releases,
                path=feature_dir,
            )
        )
    return records


def _yaml_feature_blocks(text: str) -> dict[str, str]:
    blocks: dict[str, str] = {}
    current_id: str | None = None
    current_lines: list[str] = []
    in_features = False

    for raw in text.splitlines():
        if raw == "features:":
            in_features = True
            continue
        if in_features and raw and not raw.startswith((" ", "-")):
            break
        if not in_features:
            continue

        match = re.match(r"  - id: ([a-z0-9-]+)$", raw)
        if match:
            if current_id is not None:
                blocks[current_id] = "\n".join(current_lines)
            current_id = match.group(1)
            current_lines = [raw]
            continue
        if current_id is not None:
            current_lines.append(raw)

    if current_id is not None:
        blocks[current_id] = "\n".join(current_lines)
    return blocks


def _table_rows_after_heading(text: str, heading: str) -> list[list[str]]:
    lines = text.splitlines()
    try:
        start = lines.index(heading)
    except ValueError:
        return []

    rows: list[list[str]] = []
    in_table = False
    for raw in lines[start + 1 :]:
        if raw.startswith("## ") and in_table:
            break
        if not raw.startswith("|"):
            if in_table and raw.strip():
                break
            continue
        cells = [cell.strip() for cell in raw.strip("|").split("|")]
        if len(cells) < 2:
            continue
        if set(cells[0]) <= {"-", ":"}:
            continue
        rows.append(cells)
        in_table = True
    return rows[1:] if rows and "Feature" in rows[0][0] else rows


def _validate_yaml(records: list[FeatureCompatibilityRecord], yaml_text: str) -> list[str]:
    failures: list[str] = []
    blocks = _yaml_feature_blocks(yaml_text)
    for record in records:
        block = blocks.get(record.feature_id)
        if block is None:
            failures.append(
                f"{COMPATIBILITY_YAML}: missing feature compatibility entry for "
                f"{record.feature_id}"
            )
            continue
        required_tokens = [
            f"name: {record.title}",
            f"feature_record: {record.readme_relpath}",
            f"feature_type: {record.feature_type}",
            f"default_surface: {record.default_surface}",
            f"stability: {record.stability}",
        ]
        if record.package != "none":
            required_tokens.append(f"package: {record.package}")
        if record.implementation_path != "none":
            required_tokens.append(f"implementation_path: {record.implementation_path}")
        required_tokens.extend(f'- "{release}"' for release in record.release_lines)

        for token in required_tokens:
            if token not in block:
                failures.append(
                    f"{COMPATIBILITY_YAML}: {record.feature_id} missing projection "
                    f"token: {token}"
                )
    return failures


def _validate_public_page(
    records: list[FeatureCompatibilityRecord],
    page_text: str,
) -> list[str]:
    failures: list[str] = []
    rows = _table_rows_after_heading(page_text, "## Feature Record Compatibility")
    if not rows:
        return [f"{COMPATIBILITY_PAGE}: missing feature record compatibility table"]

    rows_by_path: dict[str, list[str]] = {}
    for cells in rows:
        row_text = " | ".join(cells)
        for match in re.findall(r"features/[a-z0-9-]+/README\.md", row_text):
            rows_by_path[match] = cells

    for record in records:
        cells = rows_by_path.get(record.readme_relpath)
        if cells is None:
            failures.append(
                f"{COMPATIBILITY_PAGE}: missing compatibility row for {record.feature_id}"
            )
            continue
        row_text = " | ".join(cells)
        required_tokens = [
            record.title,
            record.stability,
            record.default_surface,
            record.feature_type,
            record.implementation_path,
        ]
        if record.package != "none":
            required_tokens.append(record.package)
        required_tokens.extend(record.release_lines)
        for token in required_tokens:
            if token not in row_text:
                failures.append(
                    f"{COMPATIBILITY_PAGE}: {record.feature_id} missing projection "
                    f"token: {token}"
                )
    return failures


def validate() -> list[str]:
    records = load_feature_compatibility_records()
    yaml_text = COMPATIBILITY_YAML.read_text(encoding="utf-8")
    page_text = COMPATIBILITY_PAGE.read_text(encoding="utf-8")
    failures: list[str] = []
    failures.extend(_validate_yaml(records, yaml_text))
    failures.extend(_validate_public_page(records, page_text))
    return failures


def main() -> int:
    try:
        failures = validate()
    except ValueError as exc:
        print(f"feature-compatibility-projection: {exc}", file=sys.stderr)
        return 1

    if failures:
        print("feature-compatibility-projection: validation failed", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print(
        "feature-compatibility-projection: compatibility matrix matches "
        "feature records"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
