"""ADR-016 append-only journal, projection, and trigger-enforcement tests."""

from __future__ import annotations

import importlib.util
import sqlite3
import sys
from pathlib import Path
from types import ModuleType

from fastapi.testclient import TestClient

from stigmem_node.db import apply_migrations
from stigmem_node.immutability import (
    set_embedding_status,
    set_fact_garden_membership,
    set_fact_quarantine_status,
    set_fact_validity_override,
)
from stigmem_node.storage.libsql_backend import _split_sql
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
        Path(__file__).resolve().parents[3]
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


def test_fact_query_uses_validity_projection(
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
        row = conn.execute("SELECT valid_until FROM facts WHERE id = ?", (fact["id"],)).fetchone()
        set_fact_validity_override(
            conn,
            fact_id=fact["id"],
            valid_until="2026-01-01T00:00:00+00:00",
            reason="test",
            updated_by="agent:test",
        )
        conn.commit()
    finally:
        conn.close()

    query = client.get("/v1/facts", params={"entity": FACT["entity"]})
    assert query.status_code == 200
    assert query.json()["facts"] == []
    assert row is not None
    assert row["valid_until"] is None


def test_quarantine_and_garden_projections_do_not_mutate_fact_row(tmp_path: Path) -> None:
    db_file = str(tmp_path / "quarantine_projection.db")
    apply_migrations(db_path=db_file)

    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute(
            "INSERT INTO facts "
            "(id, entity, relation, value_type, value_v, source, timestamp, "
            "confidence, scope, garden_id, quarantine_garden_id, quarantine_status) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
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
                None,
                "garden-quarantine",
                "pending",
            ),
        )

        set_fact_garden_membership(
            conn,
            fact_id="fact-1",
            garden_id="garden-target",
            updated_by="agent:test",
        )
        set_fact_quarantine_status(
            conn,
            fact_id="fact-1",
            quarantine_garden_id="garden-quarantine",
            quarantine_status="promoted",
            quarantine_reason="test",
            quarantine_acted_by="agent:test",
            quarantine_acted_at="2026-05-17T00:00:01+00:00",
        )
        conn.commit()

        fact_row = conn.execute(
            "SELECT garden_id, quarantine_status FROM facts WHERE id = ?",
            ("fact-1",),
        ).fetchone()
        garden_projection = conn.execute(
            "SELECT garden_id FROM fact_garden_membership WHERE fact_id = ?",
            ("fact-1",),
        ).fetchone()
        quarantine_projection = conn.execute(
            "SELECT quarantine_status FROM fact_quarantine_status WHERE fact_id = ?",
            ("fact-1",),
        ).fetchone()
    finally:
        conn.close()

    assert fact_row is not None
    assert garden_projection is not None
    assert quarantine_projection is not None
    assert fact_row["garden_id"] is None
    assert fact_row["quarantine_status"] == "pending"
    assert garden_projection["garden_id"] == "garden-target"
    assert quarantine_projection["quarantine_status"] == "promoted"


def test_facts_table_update_delete_triggers_block_mutation_and_audit(tmp_path: Path) -> None:
    db_file = str(tmp_path / "immutability_l2_triggers.db")
    apply_migrations(db_path=db_file)

    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute(
            "INSERT INTO facts "
            "(id, entity, relation, value_type, value_v, source, timestamp, "
            "confidence, scope, tenant_id) "
            "VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                "fact-trigger-1",
                "stigmem://example/entity/a",
                "memory:summary",
                "string",
                "hello",
                "stigmem://example/source/test",
                "2026-05-17T00:00:00+00:00",
                1.0,
                "local",
                "default",
            ),
        )
        conn.commit()

        try:
            conn.execute("UPDATE facts SET confidence = ? WHERE id = ?", (0.25, "fact-trigger-1"))
        except sqlite3.IntegrityError as exc:
            assert "append-only" in str(exc)
        else:
            raise AssertionError("UPDATE facts should be blocked by facts_no_update")

        row = conn.execute(
            "SELECT confidence FROM facts WHERE id = ?",
            ("fact-trigger-1",),
        ).fetchone()
        update_audit = conn.execute(
            "SELECT event_type, source, detail FROM fact_audit_log "
            "WHERE fact_id = ? AND source = ?",
            ("fact-trigger-1", "sqlite-trigger:facts_no_update"),
        ).fetchone()

        try:
            conn.execute("DELETE FROM facts WHERE id = ?", ("fact-trigger-1",))
        except sqlite3.IntegrityError as exc:
            assert "append-only" in str(exc)
        else:
            raise AssertionError("DELETE FROM facts should be blocked by facts_no_delete")

        still_present = conn.execute(
            "SELECT COUNT(*) AS n FROM facts WHERE id = ?",
            ("fact-trigger-1",),
        ).fetchone()
        delete_audit = conn.execute(
            "SELECT event_type, source, detail FROM fact_audit_log "
            "WHERE fact_id = ? AND source = ?",
            ("fact-trigger-1", "sqlite-trigger:facts_no_delete"),
        ).fetchone()
    finally:
        conn.close()

    assert row is not None
    assert row["confidence"] == 1.0
    assert update_audit is not None
    assert update_audit["event_type"] == "fact_mutation_attempted"
    assert '"UPDATE"' in update_audit["detail"]
    assert still_present is not None
    assert still_present["n"] == 1
    assert delete_audit is not None
    assert delete_audit["event_type"] == "fact_mutation_attempted"
    assert '"DELETE"' in delete_audit["detail"]


def test_libsql_migration_splitter_keeps_trigger_bodies_intact() -> None:
    migration = Path("node/migrations/034_sqlite_facts_immutability_triggers.sql")
    stmts = _split_sql(migration.read_text())

    assert len(stmts) == 2
    assert all(stmt.startswith("CREATE TRIGGER") for stmt in stmts)
    assert all("RAISE(FAIL" in stmt for stmt in stmts)


def test_facts_mutation_inventory_guard_is_current() -> None:
    guard = _load_inventory_guard()

    assert guard.check() == 0
