#!/usr/bin/env python3
"""Validate protocol projections against feature records."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEATURES_DIR = ROOT / "features"
PROTOCOL_INDEX = ROOT / "spec" / "PROTOCOL.md"
CORE_SPECS_DIR = ROOT / "spec" / "specs"
EXPERIMENTAL_DIR = ROOT / "experimental"
SKIP_DIRS = {"feature-template"}
SPEC_ID_RE = re.compile(r"Spec-(?:\d{2}|X\d+)-[A-Za-z0-9-]+")


@dataclass(frozen=True)
class FeatureProtocolRecord:
    feature_id: str
    title: str
    canonical_spec: str
    implementation_path: str
    path: Path

    @property
    def spec_path(self) -> Path:
        return self.path / "spec.md"

    @property
    def spec_relpath(self) -> str:
        return self.spec_path.relative_to(ROOT).as_posix()


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


def load_feature_protocol_records() -> list[FeatureProtocolRecord]:
    records: list[FeatureProtocolRecord] = []
    for feature_dir in sorted(FEATURES_DIR.iterdir()):
        if not feature_dir.is_dir() or feature_dir.name in SKIP_DIRS:
            continue
        readme = feature_dir / "README.md"
        spec = feature_dir / "spec.md"
        if not readme.is_file() or not spec.is_file():
            continue
        metadata = parse_frontmatter(readme)
        required = ["feature_id", "title", "canonical_spec", "implementation_path"]
        missing = [
            field
            for field in required
            if not isinstance(metadata.get(field), str) or not metadata[field]
        ]
        if missing:
            raise ValueError(f"{readme}: missing protocol field(s): {', '.join(missing)}")
        records.append(
            FeatureProtocolRecord(
                feature_id=str(metadata["feature_id"]),
                title=str(metadata["title"]),
                canonical_spec=str(metadata["canonical_spec"]),
                implementation_path=str(metadata["implementation_path"]),
                path=feature_dir,
            )
        )
    return records


def _known_spec_text(canonical_spec: str) -> str:
    if re.fullmatch(r"Spec-\d{2}-[A-Za-z0-9-]+", canonical_spec):
        for path in CORE_SPECS_DIR.glob("*.md"):
            text = path.read_text(encoding="utf-8")
            if f"spec_id: {canonical_spec}" in text:
                return text
    elif re.fullmatch(r"Spec-X\d+-[A-Za-z0-9-]+", canonical_spec):
        for path in EXPERIMENTAL_DIR.glob("*/spec.md"):
            text = path.read_text(encoding="utf-8")
            if f"spec_id: {canonical_spec}" in text:
                return text
    return ""


def _validate_record(
    record: FeatureProtocolRecord,
    protocol_text: str,
) -> list[str]:
    failures: list[str] = []
    feature_spec = record.spec_path.read_text(encoding="utf-8")

    if record.canonical_spec == "none":
        if "no Spec-X assignment" not in feature_spec:
            failures.append(
                f"{record.spec_relpath}: features with canonical_spec none must "
                "explain that no Spec-X assignment exists"
            )
        if SPEC_ID_RE.search(feature_spec):
            failures.append(
                f"{record.spec_relpath}: canonical_spec is none but spec body "
                "mentions a Spec-* id"
            )
        return failures

    if not SPEC_ID_RE.fullmatch(record.canonical_spec):
        failures.append(
            f"{record.path / 'README.md'}: canonical_spec must be none or a Spec-* id"
        )
        return failures

    if record.canonical_spec not in feature_spec:
        failures.append(f"{record.spec_relpath}: must mention {record.canonical_spec}")
    if record.canonical_spec not in protocol_text:
        failures.append(f"{PROTOCOL_INDEX}: missing {record.canonical_spec}")

    if not _known_spec_text(record.canonical_spec):
        failures.append(
            f"{PROTOCOL_INDEX}: {record.canonical_spec} has no matching spec source"
        )
    return failures


def validate() -> list[str]:
    protocol_text = PROTOCOL_INDEX.read_text(encoding="utf-8")
    failures: list[str] = []
    for record in load_feature_protocol_records():
        failures.extend(_validate_record(record, protocol_text))
    return failures


def main() -> int:
    try:
        failures = validate()
    except ValueError as exc:
        print(f"feature-protocol-projection: {exc}", file=sys.stderr)
        return 1

    if failures:
        print("feature-protocol-projection: validation failed", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print("feature-protocol-projection: spec/PROTOCOL.md matches feature records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
