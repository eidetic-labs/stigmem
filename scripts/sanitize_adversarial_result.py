"""Sanitize ADR-015 live result JSON before publication.

Raw model output is review input, not public evidence. This script keeps the
certification metadata, aggregate summary, per-pattern identifiers, outcomes,
and rubric notes while replacing raw responses with bounded redacted excerpts.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REDACTIONS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "api-key",
        re.compile(
            r"\b(?:sk-[A-Za-z0-9_-]{16,}|"
            r"gh[pousr]_[A-Za-z0-9_]{20,}|"
            r"xox[baprs]-[A-Za-z0-9-]{20,})\b"
        ),
    ),
    (
        "bearer-token",
        re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{16,}", re.IGNORECASE),
    ),
    (
        "local-path",
        re.compile(r"/Users/[A-Za-z0-9._-]+/[^\s\"'<>)]*"),
    ),
    (
        "email",
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    ),
    (
        "environment-assignment",
        re.compile(
            r"\b[A-Z][A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL)"
            r"\s*=\s*[^\s\"']+"
        ),
    ),
    (
        "system-prompt",
        re.compile(
            r"\b(?:system|developer|adapter|tool)\s+"
            r"(?:prompt|message|instruction)s?\s*:\s*.+",
            re.IGNORECASE,
        ),
    ),
)


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected JSON object")
    return data


def _redact(text: str) -> tuple[str, list[str]]:
    redactions: list[str] = []
    sanitized = text
    for label, pattern in REDACTIONS:
        if pattern.search(sanitized):
            redactions.append(label)
        sanitized = pattern.sub(f"[REDACTED:{label}]", sanitized)
    return sanitized, sorted(set(redactions))


def _excerpt(text: str, max_chars: int) -> tuple[str, bool]:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= max_chars:
        return compact, False
    return compact[: max_chars - 1].rstrip() + "…", True


def sanitize_result(document: dict[str, Any], *, max_response_chars: int) -> dict[str, Any]:
    sanitized = dict(document)
    sanitized["publication_status"] = "review-needed"
    sanitized["sanitized_at"] = datetime.now(UTC).replace(microsecond=0).isoformat()
    sanitized["sanitization"] = {
        "raw_model_output_removed": True,
        "response_field": "sanitized excerpt only",
        "max_response_chars": max_response_chars,
        "redaction_labels": [label for label, _ in REDACTIONS],
    }

    sanitized_patterns: list[dict[str, Any]] = []
    for item in document.get("patterns", []):
        if not isinstance(item, dict):
            continue
        raw_response = item.get("response", "")
        if not isinstance(raw_response, str):
            raw_response = ""
        redacted, labels = _redact(raw_response)
        excerpt, truncated = _excerpt(redacted, max_response_chars)
        sanitized_item = {
            "id": item.get("id"),
            "category": item.get("category"),
            "severity": item.get("severity"),
            "outcome": item.get("outcome"),
            "rubric_notes": item.get("rubric_notes", []),
            "response_excerpt": excerpt,
            "response_excerpt_truncated": truncated,
            "redactions": labels,
            "source": item.get("source"),
            "path": item.get("path"),
        }
        sanitized_patterns.append(sanitized_item)
    sanitized["patterns"] = sanitized_patterns
    return sanitized


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--max-response-chars", type=int, default=600)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.max_response_chars < 80:
        raise ValueError("--max-response-chars must be at least 80")
    document = _load_json(args.input)
    sanitized = sanitize_result(document, max_response_chars=args.max_response_chars)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(sanitized, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote sanitized result {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
