"""Lexical recall search stage."""

from __future__ import annotations

import re
from typing import Any

from .common import logger

_FTS5_SPECIAL = re.compile(r'["()\^*\-:,]+')

def _fts_query(q: str) -> str:
    """Sanitise a user query string for SQLite FTS5 MATCH."""
    cleaned = _FTS5_SPECIAL.sub(" ", q).strip()
    return cleaned or '""'


def _like_search(
    conn: Any,
    query: str,
    scope: str,
    tenant_id: str,
    k: int,
    min_confidence: float,
    now: str,
) -> dict[str, float]:
    """LIKE-based text scan — fallback when FTS5 is unavailable (libsql, postgres)."""
    words = [w for w in re.sub(r"[^\w]", " ", query).split() if len(w) >= 2][:5]
    if not words:
        return {}
    clauses = " OR ".join("(value_v LIKE ? OR entity LIKE ?)" for _ in words)
    params: list[Any] = []
    for w in words:
        pat = f"%{w}%"
        params.extend([pat, pat])
    params.extend([scope, tenant_id, min_confidence, now, k])
    sql = (
        "SELECT id AS fact_id, confidence AS rank FROM facts"  # noqa: S608
        f" WHERE ({clauses})"  # nosec B608 — clauses built from literal "?" placeholders
        " AND scope = ? AND tenant_id = ? AND confidence >= ?"
        " AND (valid_until IS NULL OR valid_until > ?)"
        " ORDER BY confidence DESC LIMIT ?"
    )
    try:
        rows = conn.execute(sql, params).fetchall()
    except Exception as exc:
        logger.warning("LIKE fallback search failed: %s", exc)
        return {}
    if not rows:
        return {}
    max_conf = max(float(row["rank"]) for row in rows)
    if max_conf <= 0:
        return {}
    return {row["fact_id"]: float(row["rank"]) / max_conf for row in rows}


# ---------------------------------------------------------------------------
# Lexical search (FTS5 / BM25)
# ---------------------------------------------------------------------------


def _lexical_search(
    conn: Any,
    query: str,
    scope: str,
    tenant_id: str,
    k: int,
    min_confidence: float,
    now: str,
) -> dict[str, float]:
    """Return {fact_id: normalised_bm25_score}. Returns {} on FTS unavailability."""
    fts_q = _fts_query(query)
    try:
        # SAVEPOINT protects the surrounding transaction on Postgres: a failed
        # FTS5 MATCH query aborts the psycopg2 transaction, making all subsequent
        # SQL on the same connection fail.  Rolling back to the savepoint restores
        # the connection to a usable state.  SAVEPOINT is a no-op cost on
        # SQLite/libsql, which also support the syntax.
        conn.execute("SAVEPOINT _fts_search")
        rows = conn.execute(
            """
            SELECT ff.fact_id, bm25(facts_fts) AS rank
            FROM facts_fts ff
            JOIN facts f ON f.id = ff.fact_id
            WHERE facts_fts MATCH ?
              AND f.scope = ?
              AND f.tenant_id = ?
              AND f.confidence >= ?
              AND (f.valid_until IS NULL OR f.valid_until > ?)
            ORDER BY rank
            LIMIT ?
            """,
            (fts_q, scope, tenant_id, min_confidence, now, k),
        ).fetchall()
        conn.execute("RELEASE SAVEPOINT _fts_search")
    except Exception as exc:
        logger.warning("FTS5 lexical search failed: %s", exc)
        try:
            conn.execute("ROLLBACK TO SAVEPOINT _fts_search")
        except Exception as rollback_exc:
            logger.warning("FTS5 lexical search rollback failed: %s", rollback_exc)
        return _like_search(conn, query, scope, tenant_id, k, min_confidence, now)

    if not rows:
        return {}

    # bm25() returns negative values; less negative = more relevant.
    abs_scores = [(-row["rank"], row["fact_id"]) for row in rows]
    max_score = max(s for s, _ in abs_scores)
    if max_score <= 0:
        return {}
    return {fid: score / max_score for score, fid in abs_scores}
