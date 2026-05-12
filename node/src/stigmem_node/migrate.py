"""Entity alias population sweep — spec §2.6.6 migration guide."""

from __future__ import annotations

import logging
import sqlite3
from datetime import UTC, datetime

from .entity_normalizer import NormalizationError, normalize_entity_uri

logger = logging.getLogger(__name__)


def normalize_entities_sweep(
    db_path: str,
    *,
    dry_run: bool = False,
) -> tuple[int, int]:
    """Scan facts for non-canonical entity/source URIs and populate entity_aliases.

    Collects every distinct entity and source URI from the facts table, normalizes
    each via normalize_entity_uri, and inserts raw→canonical rows into entity_aliases
    for any URI that differs from its canonical form.

    Safe to re-run: uses INSERT OR IGNORE so existing rows are skipped.

    Returns:
        (registered, already_present) — counts of newly inserted vs skipped aliases.
        When dry_run=True, prints the would-be pairs to stdout and returns
        (would_register, 0) without touching the database.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        raw_uris: set[str] = set()
        for row in conn.execute("SELECT DISTINCT entity FROM facts"):
            raw_uris.add(row[0])
        for row in conn.execute("SELECT DISTINCT source FROM facts"):
            raw_uris.add(row[0])

        pairs: list[tuple[str, str]] = []
        for raw in sorted(raw_uris):
            try:
                canonical = normalize_entity_uri(raw)
            except NormalizationError as exc:
                logger.warning("skipping non-normalizable entity/source URI %r: %s", raw, exc)
                continue
            if raw != canonical:
                pairs.append((raw, canonical))

        if dry_run:
            for raw, canonical in pairs:
                print(f"{raw!r} → {canonical!r}")
            return len(pairs), 0

        now = datetime.now(UTC).isoformat()
        registered = 0
        already_present = 0
        for raw, canonical in pairs:
            cur = conn.execute(
                "INSERT OR IGNORE INTO entity_aliases (raw_uri, canonical_uri, created_at)"
                " VALUES (?, ?, ?)",
                (raw, canonical, now),
            )
            if cur.rowcount > 0:
                registered += 1
            else:
                already_present += 1

        conn.commit()
        return registered, already_present
    finally:
        conn.close()
