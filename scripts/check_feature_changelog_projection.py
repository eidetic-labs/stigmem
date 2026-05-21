#!/usr/bin/env python3
"""Validate CHANGELOG.md against feature-level changelog records."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEATURES_DIR = ROOT / "features"
CHANGELOG = ROOT / "CHANGELOG.md"
SKIP_DIRS = {"feature-template"}


@dataclass(frozen=True)
class FeatureChangelogRecord:
    feature_id: str
    title: str
    status: str
    release_lines: tuple[str, ...]
    path: Path

    @property
    def changelog_path(self) -> Path:
        return self.path / "changelog.md"

    @property
    def changelog_relpath(self) -> str:
        return self.changelog_path.relative_to(ROOT).as_posix()


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


def load_feature_changelog_records() -> list[FeatureChangelogRecord]:
    records: list[FeatureChangelogRecord] = []
    for feature_dir in sorted(FEATURES_DIR.iterdir()):
        if not feature_dir.is_dir() or feature_dir.name in SKIP_DIRS:
            continue
        readme = feature_dir / "README.md"
        changelog = feature_dir / "changelog.md"
        if not readme.is_file() or not changelog.is_file():
            continue
        metadata = parse_frontmatter(readme)
        feature_id = metadata.get("feature_id")
        title = metadata.get("title")
        status = metadata.get("status")
        release_lines = metadata.get("release_lines")
        if not isinstance(feature_id, str) or not feature_id:
            raise ValueError(f"{readme}: missing feature_id")
        if not isinstance(title, str) or not title:
            raise ValueError(f"{readme}: missing title")
        if not isinstance(status, str) or not status:
            raise ValueError(f"{readme}: missing status")
        if not isinstance(release_lines, list) or not release_lines:
            raise ValueError(f"{readme}: release_lines must be a non-empty list")
        releases = tuple(line for line in release_lines if isinstance(line, str))
        records.append(
            FeatureChangelogRecord(
                feature_id=feature_id,
                title=title,
                status=status,
                release_lines=releases,
                path=feature_dir,
            )
        )
    return records


def _table_rows_after_heading(text: str, heading: str) -> list[list[str]]:
    lines = text.splitlines()
    try:
        start = lines.index(heading)
    except ValueError:
        return []

    rows: list[list[str]] = []
    in_table = False
    for raw in lines[start + 1 :]:
        if (raw.startswith("## ") or raw.startswith("### ")) and in_table:
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


def _validate_feature_changelog_records(
    records: list[FeatureChangelogRecord],
) -> list[str]:
    failures: list[str] = []
    for record in records:
        body = record.changelog_path.read_text(encoding="utf-8")
        if "## Unreleased" not in body:
            failures.append(f"{record.changelog_relpath}: missing Unreleased section")
        for release_line in record.release_lines:
            if release_line.startswith("v") and release_line not in body:
                failures.append(
                    f"{record.changelog_relpath}: body must mention {release_line}"
                )
    return failures


def _validate_feature_changelog_table(
    records: list[FeatureChangelogRecord],
    changelog_text: str,
) -> list[str]:
    failures: list[str] = []
    rows = _table_rows_after_heading(changelog_text, "### Feature Change Records")
    if not rows:
        return [f"{CHANGELOG}: missing feature change records table"]

    rows_by_path: dict[str, list[str]] = {}
    for cells in rows:
        row_text = " | ".join(cells)
        for match in re.findall(r"features/[a-z0-9-]+/changelog\.md", row_text):
            rows_by_path[match] = cells

    for record in records:
        cells = rows_by_path.get(record.changelog_relpath)
        if cells is None:
            failures.append(
                f"{CHANGELOG}: missing feature changelog link for {record.feature_id}"
            )
            continue
        row_text = " | ".join(cells)
        if record.title not in row_text:
            failures.append(f"{CHANGELOG}: missing title projection for {record.feature_id}")
        if record.status not in row_text:
            failures.append(f"{CHANGELOG}: missing status projection for {record.feature_id}")
        for release_line in record.release_lines:
            if release_line not in row_text:
                failures.append(
                    f"{CHANGELOG}: missing {release_line} projection for "
                    f"{record.feature_id}"
                )
    return failures


def validate() -> list[str]:
    records = load_feature_changelog_records()
    changelog_text = CHANGELOG.read_text(encoding="utf-8")
    failures: list[str] = []
    failures.extend(_validate_feature_changelog_records(records))
    failures.extend(_validate_feature_changelog_table(records, changelog_text))
    return failures


def main() -> int:
    try:
        failures = validate()
    except ValueError as exc:
        print(f"feature-changelog-projection: {exc}", file=sys.stderr)
        return 1

    if failures:
        print("feature-changelog-projection: validation failed", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print("feature-changelog-projection: CHANGELOG.md matches feature changelog records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
