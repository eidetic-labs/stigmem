"""Loom single-node reference prototype — Phase 0.

Two operations: assert(fact) and query(pattern).
No federation, no auth, no UI. ~200 lines.
"""

from __future__ import annotations

import sqlite3
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any, Generator

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

DB_PATH = "loom.db"
app = FastAPI(title="Loom prototype", version="0.0.1")


# ---------------------------------------------------------------------------
# DB setup
# ---------------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS facts (
    id          TEXT PRIMARY KEY,
    entity      TEXT NOT NULL,
    relation    TEXT NOT NULL,
    value_type  TEXT NOT NULL,
    value_v     TEXT NOT NULL,
    source      TEXT NOT NULL,
    timestamp   TEXT NOT NULL,
    confidence  REAL NOT NULL CHECK(confidence >= 0.0 AND confidence <= 1.0),
    scope       TEXT NOT NULL CHECK(scope IN ('local','team','company','public'))
);
CREATE INDEX IF NOT EXISTS idx_entity_relation ON facts(entity, relation);
CREATE INDEX IF NOT EXISTS idx_scope ON facts(scope);
"""


@contextmanager
def db() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

VALID_SCOPES = {"local", "team", "company", "public"}
VALID_VALUE_TYPES = {"string", "number", "boolean", "datetime", "ref", "null"}


class FactValue(BaseModel):
    type: str
    v: Any = None

    @field_validator("type")
    @classmethod
    def check_type(cls, t: str) -> str:
        if t not in VALID_VALUE_TYPES:
            raise ValueError(f"type must be one of {VALID_VALUE_TYPES}")
        return t


class AssertRequest(BaseModel):
    entity: str = Field(..., min_length=1)
    relation: str = Field(..., min_length=1)
    value: FactValue
    source: str = Field(..., min_length=1)
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    scope: str = Field("local")

    @field_validator("scope")
    @classmethod
    def check_scope(cls, s: str) -> str:
        if s not in VALID_SCOPES:
            raise ValueError(f"scope must be one of {VALID_SCOPES}")
        return s


class FactRecord(BaseModel):
    id: str
    entity: str
    relation: str
    value: FactValue
    source: str
    timestamp: str
    confidence: float
    scope: str
    contradicted: bool = False
    decayed: bool = False


class QueryResponse(BaseModel):
    facts: list[FactRecord]
    total: int
    cursor: str | None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def row_to_record(row: sqlite3.Row, contradicted: bool = False, decayed: bool = False) -> FactRecord:
    return FactRecord(
        id=row["id"],
        entity=row["entity"],
        relation=row["relation"],
        value=FactValue(type=row["value_type"], v=_parse_v(row["value_type"], row["value_v"])),
        source=row["source"],
        timestamp=row["timestamp"],
        confidence=row["confidence"],
        scope=row["scope"],
        contradicted=contradicted,
        decayed=decayed,
    )


def _parse_v(vtype: str, raw: str) -> Any:
    if vtype == "number":
        return float(raw)
    if vtype == "boolean":
        return raw == "true"
    if vtype == "null":
        return None
    return raw


def _detect_contradictions(conn: sqlite3.Connection, entity: str, relation: str, scope: str) -> list[sqlite3.Row]:
    """Return all facts for (entity, relation, scope), sorted by confidence desc, timestamp desc."""
    rows = conn.execute(
        "SELECT * FROM facts WHERE entity=? AND relation=? AND scope=? ORDER BY confidence DESC, timestamp DESC",
        (entity, relation, scope),
    ).fetchall()
    return rows


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.post("/v1/facts", response_model=FactRecord, status_code=201)
def assert_fact(req: AssertRequest) -> FactRecord:
    """Assert a fact into the fabric."""
    fact_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()
    value_v = "null" if req.value.type == "null" else str(req.value.v)
    if req.value.type == "boolean":
        value_v = "true" if req.value.v else "false"

    with db() as conn:
        conn.execute(
            """INSERT INTO facts (id, entity, relation, value_type, value_v, source, timestamp, confidence, scope)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (fact_id, req.entity, req.relation, req.value.type, value_v,
             req.source, now, req.confidence, req.scope),
        )
        row = conn.execute("SELECT * FROM facts WHERE id=?", (fact_id,)).fetchone()
        existing = _detect_contradictions(conn, req.entity, req.relation, req.scope)

    contradicted = len(existing) > 1
    return row_to_record(row, contradicted=contradicted)


@app.get("/v1/facts", response_model=QueryResponse)
def query_facts(
    entity: str | None = Query(None),
    relation: str | None = Query(None),
    source: str | None = Query(None),
    scope: str | None = Query(None),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    include_contradicted: bool = Query(False),
    include_decayed: bool = Query(False),
    after: str | None = Query(None),
    cursor: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
) -> QueryResponse:
    """Query facts by pattern. Omitted fields are wildcards."""
    conditions: list[str] = ["confidence >= ?"]
    params: list[Any] = [min_confidence]

    if entity:
        conditions.append("entity = ?")
        params.append(entity)
    if relation:
        conditions.append("relation = ?")
        params.append(relation)
    if source:
        conditions.append("source = ?")
        params.append(source)
    if scope:
        if scope not in VALID_SCOPES:
            raise HTTPException(status_code=400, detail=f"scope must be one of {VALID_SCOPES}")
        conditions.append("scope = ?")
        params.append(scope)
    if after:
        conditions.append("timestamp > ?")
        params.append(after)
    if cursor:
        conditions.append("id > ?")
        params.append(cursor)

    where = " AND ".join(conditions)
    sql = f"SELECT * FROM facts WHERE {where} ORDER BY timestamp DESC, id DESC LIMIT ?"
    params.append(limit + 1)

    with db() as conn:
        rows = conn.execute(sql, params).fetchall()

    has_more = len(rows) > limit
    rows = rows[:limit]

    # detect contradictions per (entity, relation, scope) group
    seen: dict[tuple[str, str, str], int] = {}
    for r in rows:
        key = (r["entity"], r["relation"], r["scope"])
        seen[key] = seen.get(key, 0) + 1

    records = []
    for r in rows:
        key = (r["entity"], r["relation"], r["scope"])
        contradicted = seen[key] > 1
        decayed = not include_decayed and r["confidence"] == 0.0
        if decayed and not include_decayed:
            continue
        records.append(row_to_record(r, contradicted=contradicted, decayed=decayed))

    next_cursor = rows[-1]["id"] if has_more and rows else None
    return QueryResponse(facts=records, total=len(records), cursor=next_cursor)


@app.get("/healthz")
def health() -> dict[str, str]:
    return {"status": "ok"}
