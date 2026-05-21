#!/usr/bin/env python3
"""Validate SECURITY.md against feature-level security records."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEATURES_DIR = ROOT / "features"
SECURITY_POLICY = ROOT / "SECURITY.md"
SKIP_DIRS = {"feature-template"}
RISK_RE = re.compile(r"R-\d{2}")


@dataclass(frozen=True)
class FeatureSecurityRecord:
    feature_id: str
    title: str
    security_refs: tuple[str, ...]
    path: Path

    @property
    def security_path(self) -> Path:
        return self.path / "security.md"

    @property
    def security_relpath(self) -> str:
        return self.security_path.relative_to(ROOT).as_posix()


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


def load_feature_security_records() -> list[FeatureSecurityRecord]:
    records: list[FeatureSecurityRecord] = []
    for feature_dir in sorted(FEATURES_DIR.iterdir()):
        if not feature_dir.is_dir() or feature_dir.name in SKIP_DIRS:
            continue
        readme = feature_dir / "README.md"
        security = feature_dir / "security.md"
        if not readme.is_file() or not security.is_file():
            continue
        metadata = parse_frontmatter(readme)
        feature_id = metadata.get("feature_id")
        title = metadata.get("title")
        security_refs = metadata.get("security_refs")
        if not isinstance(feature_id, str) or not feature_id:
            raise ValueError(f"{readme}: missing feature_id")
        if not isinstance(title, str) or not title:
            raise ValueError(f"{readme}: missing title")
        if not isinstance(security_refs, list) or not security_refs:
            raise ValueError(f"{readme}: security_refs must be a non-empty list")
        refs = tuple(ref for ref in security_refs if isinstance(ref, str) and ref != "none")
        records.append(
            FeatureSecurityRecord(
                feature_id=feature_id,
                title=title,
                security_refs=refs,
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
    return rows[1:] if rows and "Finding" in rows[0][0] else rows


def _validate_feature_security_records(
    records: list[FeatureSecurityRecord],
) -> list[str]:
    failures: list[str] = []
    for record in records:
        body = record.security_path.read_text(encoding="utf-8")
        if "## Advisories and Findings" not in body:
            failures.append(
                f"{record.security_relpath}: missing Advisories and Findings section"
            )
        for risk_id in record.security_refs:
            if not RISK_RE.fullmatch(risk_id):
                failures.append(
                    f"{record.path / 'README.md'}: security_refs entry must match R-##: "
                    f"{risk_id}"
                )
            if risk_id not in body:
                failures.append(f"{record.security_relpath}: body must mention {risk_id}")
    return failures


def _validate_feature_security_table(
    records: list[FeatureSecurityRecord],
    security_text: str,
) -> list[str]:
    failures: list[str] = []
    rows = _table_rows_after_heading(security_text, "## Feature Security Records")
    if not rows:
        return [f"{SECURITY_POLICY}: missing feature security records table"]

    rows_by_path: dict[str, list[str]] = {}
    for cells in rows:
        row_text = " | ".join(cells)
        for match in re.findall(r"features/[a-z0-9-]+/security\.md", row_text):
            rows_by_path[match] = cells

    for record in records:
        cells = rows_by_path.get(record.security_relpath)
        if cells is None:
            failures.append(
                f"{SECURITY_POLICY}: missing feature security link for {record.feature_id}"
            )
            continue
        row_text = " | ".join(cells)
        for risk_id in record.security_refs:
            if risk_id not in row_text:
                failures.append(
                    f"{SECURITY_POLICY}: missing {risk_id} projection for {record.feature_id}"
                )
    return failures


def _validate_advisory_policy(security_text: str) -> list[str]:
    failures: list[str] = []
    required_policy_phrases = [
        "Critical and High vulnerabilities that affect a published artifact are "
        "disclosed with a GitHub repository security advisory",
        "Medium and Low vulnerabilities are documented in release notes, "
        "security posture docs, or operator guidance",
    ]
    for phrase in required_policy_phrases:
        if phrase not in security_text:
            failures.append(f"{SECURITY_POLICY}: missing advisory policy phrase: {phrase}")

    stale_phrases = [
        "Held for the next publication batch",
        "future PR",
        "queued as draft on GitHub",
    ]
    for phrase in stale_phrases:
        if phrase.lower() in security_text.lower():
            failures.append(f"{SECURITY_POLICY}: stale security-publication framing: {phrase}")
    return failures


def _validate_internal_audit_table(security_text: str) -> list[str]:
    failures: list[str] = []
    rows = _table_rows_after_heading(security_text, "### Internal audit dispositions — v0.9.0a2")
    if not rows:
        return [f"{SECURITY_POLICY}: missing internal audit disposition table"]

    for cells in rows:
        if len(cells) < 4:
            failures.append(f"{SECURITY_POLICY}: malformed internal audit row: {' | '.join(cells)}")
            continue
        finding, severity, advisory = cells[0], cells[1].lower(), cells[2]
        has_ghsa = "GHSA-" in advisory
        documented_here = "None; documented per policy" in advisory
        if severity.startswith("critical") or severity.startswith("high"):
            if not has_ghsa:
                failures.append(f"{SECURITY_POLICY}: {finding} is {cells[1]} but has no GHSA")
        elif severity.startswith("medium") or severity.startswith("low"):
            if has_ghsa:
                failures.append(
                    f"{SECURITY_POLICY}: {finding} is {cells[1]} but uses a GHSA without "
                    "an explicit policy carve-out"
                )
            if not documented_here:
                failures.append(
                    f"{SECURITY_POLICY}: {finding} is {cells[1]} but is not documented "
                    "as a policy disposition"
                )
    return failures


def validate() -> list[str]:
    records = load_feature_security_records()
    security_text = SECURITY_POLICY.read_text(encoding="utf-8")
    failures: list[str] = []
    failures.extend(_validate_advisory_policy(security_text))
    failures.extend(_validate_internal_audit_table(security_text))
    failures.extend(_validate_feature_security_records(records))
    failures.extend(_validate_feature_security_table(records, security_text))
    return failures


def main() -> int:
    try:
        failures = validate()
    except ValueError as exc:
        print(f"feature-security-projection: {exc}", file=sys.stderr)
        return 1

    if failures:
        print("feature-security-projection: validation failed", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print("feature-security-projection: SECURITY.md matches feature security records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
