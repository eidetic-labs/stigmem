"""Recall-time processing pipeline — spec §19.4.4, §19.7.

Pipeline order (§19.7.5):
    Storage layer
    → Scope/garden ACL (done in facts.py)
    → Source-trust multiplier applied to effective_confidence  ← here
    → Content sanitizer                                        ← here
    → API response serializer

Exported surface:
    apply_recall_pipeline(records, identity, include_low_trust) -> list[FactRecord]
    run_sanitizer(record) -> FactRecord  (exposed for tests)
"""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .auth import Identity
    from .models import FactRecord

logger = logging.getLogger("stigmem.recall")

# ---------------------------------------------------------------------------
# Sentinel patterns (§19.7.2) — compiled once at module load
# ---------------------------------------------------------------------------

_DEFAULT_PATTERNS: list[str] = [
    r"\bignore\s+(all\s+)?previous\s+instructions?\b",
    r"\bdisregard\s+(all\s+)?previous\s+(prompt|instructions?)\b",
    r"\byou\s+are\s+now\s+(?:in\s+)?(?:a\s+)?(?:different|new)\s+mode\b",
    r"\bact\s+as\s+(?:an?\s+)?(?:evil|unfiltered|uncensored|dan\b)",
    r"\bsystem\s+prompt\s*:\s*",
    r"<\|im_start\|>",
    r"<\|im_end\|>",
    r"\[INST\]",
    r"\[\/INST\]",
    r"\bHuman:\s*",
    r"\bAssistant:\s*",
    r'\{\s*"__proto__"\s*:',
    r'\{\s*"constructor"\s*:',
]

# Invisible / bidi control characters to strip (§19.7.2)
_BIDI_CONTROLS = frozenset(
    chr(c) for c in [
        0x200F, 0x200E,
        *range(0x202A, 0x202F),
        *range(0x2066, 0x206A),
        *range(0x200B, 0x200E),
        0xFEFF,
    ]
)

# Control characters forbidden in string/text output (§19.7.3)
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")


def _load_compiled_patterns() -> list[re.Pattern[str]]:
    from .settings import settings

    patterns = list(_DEFAULT_PATTERNS)

    extra_file = settings.sanitizer_extra_patterns_file
    if extra_file:
        try:
            with open(extra_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        patterns.append(line)
        except FileNotFoundError:
            logger.warning("sanitizer_extra_patterns_file not found: %s", extra_file)
        except Exception as exc:
            logger.error("Failed to read sanitizer_extra_patterns_file: %s", exc)

    return [re.compile(p, re.IGNORECASE) for p in patterns]


# Lazy-load compiled patterns; reset if settings change.
_compiled_patterns: list[re.Pattern[str]] | None = None


def _get_patterns() -> list[re.Pattern[str]]:
    global _compiled_patterns
    if _compiled_patterns is None:
        _compiled_patterns = _load_compiled_patterns()
    return _compiled_patterns


def reset_pattern_cache() -> None:
    global _compiled_patterns
    _compiled_patterns = None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def apply_recall_pipeline(
    records: list["FactRecord"],
    identity: "Identity | None" = None,
    include_low_trust: bool = False,
) -> list["FactRecord"]:
    """Apply trust multiplier and content sanitizer to a list of FactRecords.

    Returns a filtered/annotated list.  Records that should be fully excluded
    (block mode) are replaced with a placeholder FactRecord with sanitizer_redacted=True.
    """
    from .settings import settings

    trust_mode = settings.trust_mode
    sanitizer_mode = settings.sanitizer_mode

    if trust_mode == "off":
        sanitizer_mode = "off"

    result: list["FactRecord"] = []

    for record in records:
        # Skip quarantined facts from normal recall results (§19.5.2)
        # (rejected facts have confidence=0 and are caught by min_confidence filter)
        if record.quarantine_status == "pending":
            continue

        # 1. Source-trust multiplier (§19.4.4)
        eff_conf = record.confidence
        if trust_mode != "off":
            from .source_trust import compute_source_trust
            t = compute_source_trust(record.source, record.scope, identity)
            eff_conf = record.confidence * t
            record = record.model_copy(update={"effective_confidence": eff_conf, "source_trust": t})

            # In strict mode, filter facts below 0.3 effective confidence unless
            # caller opts in (§19.4.4). In relaxed mode, MUST NOT filter based
            # solely on a low score (§19.4.3).
            if trust_mode == "strict" and eff_conf < 0.3 and not include_low_trust:
                continue

        # 2. Content sanitizer (§19.7)
        if sanitizer_mode != "off":
            record = _run_sanitizer(record, sanitizer_mode, eff_conf)

        result.append(record)

    return result


def _run_sanitizer(record: "FactRecord", mode: str, effective_confidence: float) -> "FactRecord":
    """Run content sanitizer on one fact record.  Returns possibly-modified record."""
    from .models import FactRecord, FactValue

    value = record.value
    if value.type not in ("string", "text"):
        # Schema type enforcement for non-string types (§19.7.3)
        return _enforce_schema_types(record)

    # Normalize to NFKC, strip bidi controls (§19.7.2)
    raw_v = str(value.v) if value.v is not None else ""
    normalized = unicodedata.normalize("NFKC", raw_v)
    stripped = "".join(c for c in normalized if c not in _BIDI_CONTROLS)
    # Strip control chars (§19.7.3)
    cleaned = _CONTROL_CHARS_RE.sub("", stripped)

    # Pattern matching
    matched_patterns: list[str] = []
    for pat in _get_patterns():
        if pat.search(cleaned):
            matched_patterns.append(pat.pattern)

    if not matched_patterns:
        # No sentinel match; apply cleaned value if content was modified
        if cleaned != raw_v:
            return record.model_copy(
                update={"value": FactValue(type=value.type, v=cleaned)}
            )
        return record

    # Sentinel matched — apply enforcement mode
    if mode == "warn":
        return record.model_copy(
            update={"sanitizer_warnings": matched_patterns, "value": FactValue(type=value.type, v=cleaned)}
        )

    if mode == "block":
        logger.debug("Sanitizer blocked fact %s (matched: %s)", record.id, matched_patterns[0])
        return record.model_copy(
            update={
                "sanitizer_redacted": True,
                "sanitizer_warnings": matched_patterns,
                "value": FactValue(type=value.type, v=None),
            }
        )

    if mode == "quarantine":
        _quarantine_via_sanitizer(record.id, matched_patterns[0])
        logger.info("Sanitizer quarantined fact %s", record.id)
        # Return redacted record for this response
        return record.model_copy(
            update={
                "sanitizer_redacted": True,
                "sanitizer_warnings": matched_patterns,
                "value": FactValue(type=value.type, v=None),
            }
        )

    return record


def _enforce_schema_types(record: "FactRecord") -> "FactRecord":
    """Enforce schema correctness for non-string FactValue types (§19.7.3)."""
    from .models import FactValue
    import math

    v = record.value
    redacted = False

    if v.type == "number":
        if v.v is None or (isinstance(v.v, float) and (math.isnan(v.v) or math.isinf(v.v))):
            return record.model_copy(
                update={"value": FactValue(type="number", v=None), "sanitizer_redacted": True}
            )

    if v.type == "ref":
        raw = str(v.v) if v.v is not None else ""
        if "://" not in raw and not raw.startswith("urn:"):
            return record.model_copy(
                update={"value": FactValue(type="ref", v=None), "sanitizer_redacted": True}
            )

    return record


def _quarantine_via_sanitizer(fact_id: str, matched_pattern: str) -> None:
    """Move a fact to the node's quarantine garden (sanitizer quarantine mode)."""
    from .settings import settings
    from .db import db
    from datetime import UTC, datetime

    qg_id = settings.quarantine_garden_id
    if not qg_id:
        logger.warning(
            "Sanitizer quarantine mode set but quarantine_garden_id not configured; "
            "fact %s will not be quarantined", fact_id
        )
        return

    now = datetime.now(UTC).isoformat()

    try:
        with db() as conn:
            # Resolve garden UUID
            qg_row = conn.execute(
                "SELECT id FROM gardens WHERE (id = ? OR slug = ?) AND quarantine = 1",
                (qg_id, qg_id),
            ).fetchone()
            if qg_row is None:
                logger.warning("Quarantine garden %s not found; skipping sanitizer quarantine", qg_id)
                return

            conn.execute(
                """UPDATE facts
                   SET quarantine_garden_id = ?,
                       quarantine_status = 'pending',
                       quarantine_reason = ?
                   WHERE id = ?""",
                (qg_row["id"], f"sanitizer: {matched_pattern}", fact_id),
            )

            # Audit (§19.7.6)
            import uuid
            audit_id = str(uuid.uuid4())
            conn.execute(
                """INSERT INTO fact_audit (id, fact_id, event_type, entity_uri, oidc_sub, source, attested_key_id, ts)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (audit_id, fact_id, "sanitizer_quarantine", "system:stigmem", None, "system:stigmem", None, now),
            )
    except Exception as exc:
        logger.error("Failed to quarantine fact %s via sanitizer: %s", fact_id, exc)
