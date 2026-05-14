#!/usr/bin/env python3
"""Generate the protocol composition index from modular spec frontmatter."""

from __future__ import annotations

import argparse
import difflib
import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPECS_DIR = ROOT / "spec" / "specs"
PROTOCOL_PATH = ROOT / "spec" / "PROTOCOL.md"

REQUIRED_FIELDS = (
    "spec_id",
    "version",
    "status",
    "applies_to",
    "last_updated",
    "supersedes",
    "depends_on",
)
VALID_STATUSES = {"Draft", "Experimental", "Stable", "Superseded", "Deprecated"}


@dataclass(frozen=True)
class SpecMetadata:
    path: Path
    spec_id: str
    version: str
    status: str
    applies_to: str
    last_updated: str
    supersedes: str
    depends_on: tuple[str, ...]


def _fail(message: str) -> None:
    raise ValueError(message)


def _parse_frontmatter(path: Path) -> dict[str, str | list[str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        _fail(f"{path}: missing opening YAML frontmatter marker")

    try:
        end = lines[1:].index("---") + 1
    except ValueError as exc:
        raise ValueError(f"{path}: missing closing YAML frontmatter marker") from exc

    metadata: dict[str, str | list[str]] = {}
    current_key: str | None = None

    for line_number, raw_line in enumerate(lines[1:end], start=2):
        if not raw_line.strip():
            continue

        if raw_line.startswith("  - "):
            if current_key != "depends_on":
                _fail(f"{path}:{line_number}: list item is only supported for depends_on")
            value = raw_line[4:].strip()
            if not value:
                _fail(f"{path}:{line_number}: empty depends_on entry")
            depends_on = metadata.setdefault("depends_on", [])
            if not isinstance(depends_on, list):
                _fail(f"{path}:{line_number}: depends_on must be a list")
            depends_on.append(value)
            continue

        if ":" not in raw_line:
            _fail(f"{path}:{line_number}: expected key: value frontmatter entry")

        key, raw_value = raw_line.split(":", 1)
        key = key.strip()
        value = raw_value.strip()
        current_key = key

        if key == "depends_on":
            if value == "[]":
                metadata[key] = []
            elif value:
                _fail(f"{path}:{line_number}: depends_on must use [] or indented list items")
            else:
                metadata[key] = []
            continue

        if not value:
            _fail(f"{path}:{line_number}: {key} must not be empty")
        metadata[key] = value

    return metadata


def _require_string(
    metadata: dict[str, str | list[str]],
    path: Path,
    field: str,
) -> str:
    value = metadata.get(field)
    if not isinstance(value, str):
        _fail(f"{path}: {field} must be a scalar string")
    return value


def _load_spec(path: Path) -> SpecMetadata:
    metadata = _parse_frontmatter(path)
    missing = [field for field in REQUIRED_FIELDS if field not in metadata]
    if missing:
        _fail(f"{path}: missing required frontmatter field(s): {', '.join(missing)}")

    spec_id = _require_string(metadata, path, "spec_id")
    version = _require_string(metadata, path, "version")
    status = _require_string(metadata, path, "status")
    applies_to = _require_string(metadata, path, "applies_to")
    last_updated = _require_string(metadata, path, "last_updated")
    supersedes = _require_string(metadata, path, "supersedes")
    depends_raw = metadata["depends_on"]

    if not isinstance(depends_raw, list) or not all(
        isinstance(item, str) for item in depends_raw
    ):
        _fail(f"{path}: depends_on must be a list of strings")

    spec_match = re.fullmatch(r"Spec-(\d{2})-[A-Za-z0-9-]+", spec_id)
    if spec_match is None:
        _fail(f"{path}: spec_id must look like Spec-01-Core")

    file_number = path.stem.split("-", 1)[0]
    if file_number != spec_match.group(1):
        _fail(f"{path}: filename number does not match {spec_id}")

    if status not in VALID_STATUSES:
        _fail(f"{path}: status must be one of {', '.join(sorted(VALID_STATUSES))}")

    return SpecMetadata(
        path=path,
        spec_id=spec_id,
        version=version,
        status=status,
        applies_to=applies_to,
        last_updated=last_updated,
        supersedes=supersedes,
        depends_on=tuple(depends_raw),
    )


def load_specs() -> list[SpecMetadata]:
    paths = sorted(SPECS_DIR.glob("*.md"))
    if not paths:
        _fail(f"{SPECS_DIR}: no modular spec files found")

    specs = [_load_spec(path) for path in paths]
    ids = {spec.spec_id for spec in specs}
    for spec in specs:
        unknown = [
            dependency
            for dependency in spec.depends_on
            if dependency.split(maxsplit=1)[0] not in ids
        ]
        if unknown:
            _fail(
                f"{spec.path}: depends_on references unknown spec(s): "
                f"{', '.join(unknown)}"
            )
    return specs


def _markdown_link(spec: SpecMetadata) -> str:
    return f"[`{spec.spec_id}`](specs/{spec.path.name})"


def _dependency_text(spec: SpecMetadata) -> str:
    if not spec.depends_on:
        return "None"
    return "<br>".join(f"`{dependency}`" for dependency in spec.depends_on)


def render_protocol(specs: list[SpecMetadata]) -> str:
    latest_update = max(spec.last_updated for spec in specs)
    lines = [
        "# Stigmem Protocol Composition",
        "",
        "> Generated by `scripts/generate_protocol_md.py`; do not edit by hand.",
        "",
        "This file records the ADR-010 modular specification composition for the "
        "Stigmem protocol. It is generated from YAML frontmatter in "
        "[`spec/specs/`](specs/).",
        "",
        f"**Metadata last updated:** {latest_update}",
        "",
        "## Core Specs",
        "",
        "| Spec | Version | Status | Applies to | Last updated |",
        "|---|---|---|---|---|",
    ]

    for spec in specs:
        lines.append(
            f"| {_markdown_link(spec)} | `{spec.version}` | {spec.status} | "
            f"{spec.applies_to} | {spec.last_updated} |"
        )

    lines.extend(
        [
            "",
            "## Dependency Graph",
            "",
            "| Spec | Depends on | Supersedes |",
            "|---|---|---|",
        ]
    )

    for spec in specs:
        lines.append(
            f"| `{spec.spec_id}` | {_dependency_text(spec)} | {spec.supersedes} |"
        )

    lines.extend(
        [
            "",
            "## Extraction Status",
            "",
            "The files in `spec/specs/` are ADR-010 frontmatter-bearing core-spec "
            "stubs. They establish stable spec identifiers, dependencies, and "
            "version metadata for the migration. Normative prose remains in "
            "[`spec/stigmem-spec-v0.9.0a1.md`](stigmem-spec-v0.9.0a1.md) until "
            "section-by-section extraction PRs move that text into the modular "
            "spec files.",
            "",
            "Experimental and deferred material remains colocated under "
            "`experimental/<feature>/spec.md`; ADR-010 frontmatter migration for "
            "those documents is tracked as follow-up work.",
            "",
        ]
    )
    return "\n".join(lines)


def check_protocol(rendered: str) -> int:
    if not PROTOCOL_PATH.exists():
        print(f"{PROTOCOL_PATH} is missing; run scripts/generate_protocol_md.py")
        return 1

    current = PROTOCOL_PATH.read_text(encoding="utf-8")
    if current == rendered:
        return 0

    diff = difflib.unified_diff(
        current.splitlines(keepends=True),
        rendered.splitlines(keepends=True),
        fromfile=str(PROTOCOL_PATH),
        tofile="generated",
    )
    sys.stdout.writelines(diff)
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate spec/PROTOCOL.md from modular spec frontmatter.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if spec/PROTOCOL.md is not up to date",
    )
    args = parser.parse_args(argv)

    try:
        rendered = render_protocol(load_specs())
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1

    if args.check:
        return check_protocol(rendered)

    PROTOCOL_PATH.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
