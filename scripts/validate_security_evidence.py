#!/usr/bin/env python3
"""Validate the security evidence registry.

The validator is intentionally mechanical. It proves that evidence is present,
well-formed, and path-valid; it does not decide whether the listed evidence is
security-sufficient.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = REPO_ROOT / "spec" / "security" / "evidence-registry.json"
THREAT_MODEL_PATH = REPO_ROOT / "spec" / "security" / "threat-model.md"
RISK_ID_RE = re.compile(r"^R-\d{2}$")
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+(?:a|b|rc)\d+$|^\d+\.\d+\.\d+$")
REQUIRED_MITIGATED_FIELDS = {
    "title",
    "status",
    "version_introduced",
    "implementation_files",
    "test_files",
    "docs_reference_files",
    "review_decision",
}


def _failures_from_registry(registry: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    risks = registry.get("risks")
    if not isinstance(risks, dict) or not risks:
        return ["registry must contain a non-empty 'risks' object"]

    statuses = set(registry.get("status_vocabulary", []))
    decisions = set(registry.get("review_decision_vocabulary", []))
    failures.extend(_vocabulary_failures(statuses, decisions))

    for risk_id, entry in sorted(risks.items()):
        failures.extend(_risk_entry_failures(risk_id, entry, statuses, decisions))

    return failures


def _vocabulary_failures(statuses: set[str], decisions: set[str]) -> list[str]:
    failures: list[str] = []
    if not statuses:
        failures.append("registry must define status_vocabulary")
    if not decisions:
        failures.append("registry must define review_decision_vocabulary")
    return failures


def _risk_entry_failures(
    risk_id: str,
    entry: Any,
    statuses: set[str],
    decisions: set[str],
) -> list[str]:
    if not RISK_ID_RE.match(risk_id):
        return [f"{risk_id}: risk id must match R-##"]
    if not isinstance(entry, dict):
        return [f"{risk_id}: entry must be an object"]

    failures = _base_risk_failures(risk_id, entry, statuses)
    if entry.get("status") == "Mitigated":
        failures.extend(_mitigated_risk_failures(risk_id, entry, decisions))
    return failures


def _base_risk_failures(
    risk_id: str,
    entry: dict[str, Any],
    statuses: set[str],
) -> list[str]:
    failures: list[str] = []
    status = entry.get("status")
    if status not in statuses:
        failures.append(f"{risk_id}: status {status!r} is not in status_vocabulary")
    if entry.get("title") in {None, ""}:
        failures.append(f"{risk_id}: title is required")
    return failures


def _mitigated_risk_failures(
    risk_id: str,
    entry: dict[str, Any],
    decisions: set[str],
) -> list[str]:
    failures = _mitigated_metadata_failures(risk_id, entry, decisions)
    for field in ("implementation_files", "test_files", "docs_reference_files"):
        failures.extend(_evidence_path_failures(risk_id, field, entry.get(field)))
    return failures


def _mitigated_metadata_failures(
    risk_id: str,
    entry: dict[str, Any],
    decisions: set[str],
) -> list[str]:
    failures: list[str] = []
    missing = REQUIRED_MITIGATED_FIELDS - set(entry)
    if missing:
        failures.append(f"{risk_id}: missing required mitigated fields: {sorted(missing)}")

    version = entry.get("version_introduced")
    if not isinstance(version, str) or not VERSION_RE.match(version):
        failures.append(f"{risk_id}: version_introduced must be a release string, got {version!r}")

    decision = entry.get("review_decision")
    if decision not in decisions:
        failures.append(
            f"{risk_id}: review_decision {decision!r} is not in "
            "review_decision_vocabulary"
        )
    return failures


def _evidence_path_failures(risk_id: str, field: str, values: Any) -> list[str]:
    if not isinstance(values, list) or not values:
        return [f"{risk_id}: {field} must be a non-empty list"]

    failures: list[str] = []
    for rel_path in values:
        failures.extend(_single_evidence_path_failures(risk_id, field, rel_path))
    return failures


def _single_evidence_path_failures(risk_id: str, field: str, rel_path: Any) -> list[str]:
    if not isinstance(rel_path, str) or not rel_path:
        return [f"{risk_id}: {field} contains a non-string path"]
    path = Path(rel_path)
    if path.is_absolute() or ".." in path.parts:
        return [f"{risk_id}: {field} path must be repo-relative: {rel_path!r}"]
    if not (REPO_ROOT / rel_path).exists():
        return [f"{risk_id}: {field} path does not exist: {rel_path}"]
    return []


def _mitigated_risks_from_threat_model(text: str) -> set[str]:
    risks: set[str] = set()
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("| R-"):
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) < 8:
            continue
        risk_id = cells[0]
        status = cells[7].replace("*", "").strip()
        if status == "Mitigated":
            risks.add(risk_id)
    return risks


def _failures_from_threat_model(registry: dict[str, Any], threat_model: str) -> list[str]:
    risks = registry.get("risks", {})
    if not isinstance(risks, dict):
        return []
    registered = set(risks)
    mitigated = _mitigated_risks_from_threat_model(threat_model)
    missing = sorted(mitigated - registered)
    if missing:
        return [f"threat-model Mitigated risks missing from registry: {missing}"]
    return []


def main() -> int:
    failures: list[str] = []
    try:
        registry = json.loads(REGISTRY_PATH.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        rel_path = REGISTRY_PATH.relative_to(REPO_ROOT)
        print(
            f"security-evidence: unable to read {rel_path}: {exc}",
            file=sys.stderr,
        )
        return 2

    try:
        threat_model = THREAT_MODEL_PATH.read_text()
    except OSError as exc:
        rel_path = THREAT_MODEL_PATH.relative_to(REPO_ROOT)
        print(
            f"security-evidence: unable to read {rel_path}: {exc}",
            file=sys.stderr,
        )
        return 2

    if not isinstance(registry, dict):
        failures.append("registry top-level value must be an object")
    else:
        failures.extend(_failures_from_registry(registry))
        failures.extend(_failures_from_threat_model(registry, threat_model))

    if failures:
        for failure in failures:
            print(f"security-evidence: {failure}", file=sys.stderr)
        return 1

    risk_count = len(registry.get("risks", {}))
    print(f"OK: {risk_count} security evidence entr{'y' if risk_count == 1 else 'ies'} validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
