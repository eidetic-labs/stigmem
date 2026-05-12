"""Tests for the normalize-entities alias sweep — spec §2.6.6."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

import pytest

from stigmem_node.migrate import normalize_entities_sweep


def _insert_fact(
    db_path: str,
    fact_id: str,
    entity: str,
    source: str,
    relation: str = "roadmap:status",
    value: str = "done",
) -> None:
    conn = sqlite3.connect(db_path)
    now = datetime.now(UTC).isoformat()
    conn.execute(
        """INSERT INTO facts
           (id, entity, relation, value_type, value_v, source,
            timestamp, valid_until, confidence, scope, hlc, received_from)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (fact_id, entity, relation, "string", value, source, now, None, 1.0, "company", "0", None),
    )
    conn.commit()
    conn.close()


def _alias_rows(db_path: str) -> list[tuple[str, str]]:
    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT raw_uri, canonical_uri FROM entity_aliases ORDER BY raw_uri"
    ).fetchall()
    conn.close()
    return [(r[0], r[1]) for r in rows]


class TestNormalizeEntitiesSweep:
    def test_non_canonical_entity_inserted(self, tmp_db: str) -> None:
        _insert_fact(
            tmp_db,
            "f1",
            entity="stigmem://Company.EXAMPLE/Issue/EG-18",
            source="stigmem://company.example/agent/cto",
        )
        registered, already_present = normalize_entities_sweep(tmp_db)
        assert registered == 1
        assert already_present == 0
        aliases = _alias_rows(tmp_db)
        assert aliases == [
            ("stigmem://Company.EXAMPLE/Issue/EG-18", "stigmem://company.example/issue/eg-18")
        ]

    def test_non_canonical_source_inserted(self, tmp_db: str) -> None:
        _insert_fact(
            tmp_db,
            "f1",
            entity="stigmem://company.example/issue/eg-18",
            source="stigmem://Agent.ACME/Bot/ASSISTANT",
        )
        registered, _ = normalize_entities_sweep(tmp_db)
        assert registered == 1
        aliases = _alias_rows(tmp_db)
        assert aliases == [
            ("stigmem://Agent.ACME/Bot/ASSISTANT", "stigmem://agent.acme/bot/assistant")
        ]

    def test_canonical_uris_skipped(self, tmp_db: str) -> None:
        _insert_fact(
            tmp_db,
            "f1",
            entity="stigmem://company.example/issue/eg-18",
            source="stigmem://company.example/agent/cto",
        )
        registered, already_present = normalize_entities_sweep(tmp_db)
        assert registered == 0
        assert already_present == 0
        assert _alias_rows(tmp_db) == []

    def test_idempotent_second_run(self, tmp_db: str) -> None:
        _insert_fact(
            tmp_db,
            "f1",
            entity="stigmem://Company.EXAMPLE/Issue/EG-18",
            source="stigmem://company.example/agent/cto",
        )
        r1, _ = normalize_entities_sweep(tmp_db)
        assert r1 == 1

        r2, already = normalize_entities_sweep(tmp_db)
        assert r2 == 0
        assert already == 1
        assert len(_alias_rows(tmp_db)) == 1  # no duplicate

    def test_dry_run_prints_but_does_not_insert(
        self, tmp_db: str, capsys: pytest.CaptureFixture
    ) -> None:
        _insert_fact(
            tmp_db,
            "f1",
            entity="stigmem://Company.EXAMPLE/Issue/EG-18",
            source="stigmem://company.example/agent/cto",
        )
        would_register, _ = normalize_entities_sweep(tmp_db, dry_run=True)
        assert would_register == 1

        out = capsys.readouterr().out
        assert "stigmem://Company.EXAMPLE/Issue/EG-18" in out
        assert "stigmem://company.example/issue/eg-18" in out

        assert _alias_rows(tmp_db) == []  # nothing inserted

    def test_multiple_facts_same_non_canonical_deduped(self, tmp_db: str) -> None:
        _insert_fact(
            tmp_db, "f1", entity="stigmem://Company.EXAMPLE/Issue/EG-18", source="agent:cto"
        )
        _insert_fact(
            tmp_db,
            "f2",
            entity="stigmem://Company.EXAMPLE/Issue/EG-18",
            source="agent:bot",
            relation="roadmap:owner",
        )
        registered, _ = normalize_entities_sweep(tmp_db)
        assert registered == 1  # same raw_uri only inserted once
        assert len(_alias_rows(tmp_db)) == 1

    def test_empty_facts_table(self, tmp_db: str) -> None:
        registered, already_present = normalize_entities_sweep(tmp_db)
        assert registered == 0
        assert already_present == 0

    def test_informal_uri_alias_registered(self, tmp_db: str) -> None:
        _insert_fact(
            tmp_db,
            "f1",
            entity="issue:EG-42",
            source="agent:assistant",
        )
        registered, _ = normalize_entities_sweep(tmp_db)
        assert registered == 1
        aliases = _alias_rows(tmp_db)
        assert ("issue:EG-42", "issue:eg-42") in aliases
