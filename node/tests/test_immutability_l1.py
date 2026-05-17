"""ADR-016 L1 append-only journal and projection foundation tests."""

from __future__ import annotations

import importlib.util
import sqlite3
import sys
from pathlib import Path
from types import ModuleType

from fastapi.testclient import TestClient

from stigmem_node.db import apply_migrations
from stigmem_node.immutability import set_embedding_status
from stigmem_node.vector_search import store_embedding

FACT = {
    "entity": "user:immutability",
    "relation": "memory:note",
    "value": {"type": "string", "v": "journal me"},
    "source": "agent:test",
    "confidence": 1.0,
    "scope": "local",
}


def _load_inventory_guard() -> ModuleType:
    script_path = (
        Path(__file__).resolve().parents[2]
        / "scripts"
        / "check_facts_immutability_inventory.py"
    )
    spec = importlib.util.spec_from_file_location(
        "check_facts_immutability_inventory",
        script_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _table_names(conn) -> set[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return {row["name"] for row in rows}


def test_immutability_l1_tables_exist(tmp_path: Path) -> None:
    db_file = str(tmp_path / "immutability_l1.db")
    apply_migrations(db_path=db_file)

    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    try:
        tables = _table_names(conn)
    finally:
        conn.close()

    assert {
        "fact_journal",
        "fact_validity_overrides",
        "fact_embedding_status",
        "fact_recall_signals",
        "fact_cid_backfill",
        "fact_quarantine_status",
        "fact_garden_membership",
    } <= tables


def test_embedding_status_projection_replaces_fact_update(tmp_path: Path) -> None:
    db_file = str(tmp_path / "embedding_projection.db")
    apply_migrations(db_path=db_file)

    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("CREATE TABLE vec_facts (fact_id TEXT PRIMARY KEY, embedding BLOB)")
        conn.execute(
            "INSERT INTO facts "
            "(id, entity, relation, value_type, value_v, source, timestamp, "
            "confidence, scope, embedding_missing) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                "fact-1",
                "stigmem://example/entity/a",
                "memory:summary",
                "string",
                "hello",
                "stigmem://example/source/test",
                "2026-05-17T00:00:00+00:00",
                1.0,
                "local",
                1,
            ),
        )
        set_embedding_status(conn, fact_id="fact-1", embedding_missing=True)

        store_embedding(conn, "fact-1", [0.25, 0.5, 0.75])

        fact_row = conn.execute(
            "SELECT embedding_missing FROM facts WHERE id = ?",
            ("fact-1",),
        ).fetchone()
        projection_row = conn.execute(
            "SELECT embedding_missing FROM fact_embedding_status WHERE fact_id = ?",
            ("fact-1",),
        ).fetchone()
    finally:
        conn.close()

    assert fact_row is not None
    assert projection_row is not None
    assert fact_row["embedding_missing"] == 1
    assert projection_row["embedding_missing"] == 0


def test_local_assert_writes_append_only_fact_journal(
    client: TestClient,
    tmp_db: str,
) -> None:
    if tmp_db.startswith("pg:"):
        return

    response = client.post("/v1/facts", json=FACT)
    assert response.status_code == 201
    fact = response.json()

    conn = sqlite3.connect(tmp_db)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT fact_id, event_type, tenant_id, source, scope, cid, body_json "
            "FROM fact_journal WHERE fact_id = ?",
            (fact["id"],),
        ).fetchone()
    finally:
        conn.close()

    assert row is not None
    assert row["event_type"] == "fact_insert"
    assert row["tenant_id"] == "default"
    assert row["source"] == "agent:test"
    assert row["scope"] == "local"
    assert row["cid"] == fact["cid"]
    assert '"relation":"memory:note"' in row["body_json"]


def test_facts_mutation_inventory_guard_is_current() -> None:
    guard = _load_inventory_guard()

    assert guard.check() == 0
