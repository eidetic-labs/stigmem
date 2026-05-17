"""Validate ADR-015 certification result index and referenced result files."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT / "data" / "conformance" / "adversarial" / "results"
INDEX_PATH = RESULTS_DIR / "index.json"

INDEX_SCHEMA_VERSION = "adversarial-certification-index-v1"
RESULT_SCHEMA_VERSION = "adversarial-conformance-result-v1"
ALLOWED_STATUSES = {
    "certified",
    "provisional",
    "uncertified",
    "expired",
    "review-needed",
}
LIVE_PROVIDERS = {"openai", "anthropic", "ollama"}


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected JSON object")
    return data


def _require_string(data: dict[str, Any], field: str, path: Path) -> str:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{path}: field {field!r} must be a non-empty string")
    return value


def _parse_timestamp(value: str, path: Path, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{path}: field {field!r} must be ISO 8601") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{path}: field {field!r} must include timezone")
    return parsed.astimezone(UTC)


def _validate_result_file(
    *,
    entry: dict[str, Any],
    index_path: Path,
    corpus_version: str,
) -> None:
    result_path_value = _require_string(entry, "path", index_path)
    result_path = (ROOT / result_path_value).resolve()
    if not result_path.is_relative_to(ROOT):
        raise ValueError(f"{index_path}: result path escapes repository root")
    if not result_path.is_file():
        raise ValueError(f"{index_path}: result file missing: {result_path_value}")

    result = _load_json(result_path)
    if result.get("schema_version") != RESULT_SCHEMA_VERSION:
        raise ValueError(f"{result_path}: unexpected schema_version")
    if result.get("provider") not in LIVE_PROVIDERS:
        raise ValueError(f"{result_path}: reviewed certifications require a live provider")
    result_corpus = result.get("corpus")
    if not isinstance(result_corpus, dict) or result_corpus.get("version") != corpus_version:
        raise ValueError(f"{result_path}: corpus version must match certification index")

    for field in ("provider", "model", "adapter"):
        if result.get(field) != entry.get(field):
            raise ValueError(f"{index_path}: entry {field!r} must match {result_path}")

    summary = result.get("summary")
    if not isinstance(summary, dict) or summary.get("tier") != entry.get("status"):
        raise ValueError(f"{index_path}: entry status must match result summary tier")


def _validate_entry(
    *,
    entry: dict[str, Any],
    index_path: Path,
    corpus_version: str,
    stale_after_days: int,
) -> None:
    for field in ("provider", "model", "adapter", "status", "reviewed_at"):
        _require_string(entry, field, index_path)

    status = entry["status"]
    if status not in ALLOWED_STATUSES:
        raise ValueError(f"{index_path}: unknown certification status {status!r}")

    reviewed_at = _parse_timestamp(entry["reviewed_at"], index_path, "reviewed_at")
    if status in {"certified", "provisional"}:
        stale_cutoff = datetime.now(UTC) - timedelta(days=stale_after_days)
        if reviewed_at < stale_cutoff:
            raise ValueError(
                f"{index_path}: stale {status} entry must be marked expired"
            )

    if "path" in entry:
        _validate_result_file(
            entry=entry,
            index_path=index_path,
            corpus_version=corpus_version,
        )


def validate(index_path: Path = INDEX_PATH) -> int:
    index = _load_json(index_path)
    if index.get("schema_version") != INDEX_SCHEMA_VERSION:
        raise ValueError(f"{index_path}: unexpected schema_version")

    corpus_version = _require_string(index, "corpus_version", index_path)
    rerun_policy = index.get("rerun_policy")
    if not isinstance(rerun_policy, dict):
        raise ValueError(f"{index_path}: rerun_policy must be an object")
    stale_after_days = rerun_policy.get("stale_after_days")
    if not isinstance(stale_after_days, int) or stale_after_days <= 0:
        raise ValueError(f"{index_path}: rerun_policy.stale_after_days must be positive")
    triggers = rerun_policy.get("triggers")
    if not isinstance(triggers, list) or not triggers:
        raise ValueError(f"{index_path}: rerun_policy.triggers must be non-empty")
    if any(not isinstance(trigger, str) or not trigger.strip() for trigger in triggers):
        raise ValueError(f"{index_path}: rerun_policy.triggers must be strings")

    status_definitions = index.get("status_definitions")
    if not isinstance(status_definitions, dict):
        raise ValueError(f"{index_path}: status_definitions must be an object")
    missing_statuses = ALLOWED_STATUSES - set(status_definitions)
    if missing_statuses:
        raise ValueError(f"{index_path}: missing status definitions {sorted(missing_statuses)}")

    reviewed_results = index.get("reviewed_results")
    if not isinstance(reviewed_results, list):
        raise ValueError(f"{index_path}: reviewed_results must be a list")
    for entry in reviewed_results:
        if not isinstance(entry, dict):
            raise ValueError(f"{index_path}: reviewed result entries must be objects")
        _validate_entry(
            entry=entry,
            index_path=index_path,
            corpus_version=corpus_version,
            stale_after_days=stale_after_days,
        )

    print(
        f"OK: {index_path.relative_to(ROOT)} tracks "
        f"{len(reviewed_results)} reviewed certification results"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(validate())
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
