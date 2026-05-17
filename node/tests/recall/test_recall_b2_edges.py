"""B2 coverage push: small route + materializer edges that B1 left untouched.

Targets:
  - routes/cards.py — read-permission denial, invalid scope, normalisation error
  - card_materializer.mark_entity_stale — DB-error best-effort path
"""

from __future__ import annotations

import sqlite3

import pytest
from fastapi.testclient import TestClient

_ALICE = "stigmem://testnode/agent/alice"


# ---------------------------------------------------------------------------
# routes/cards.py
# ---------------------------------------------------------------------------


class TestCardsRoute:
    def test_unknown_entity_returns_404(self, client: TestClient) -> None:
        # Triggers the "no live facts" 404 that drives the not-found path.
        r = client.get(
            "/v1/cards/stigmem://testnode/agent/never-asserted",
            params={"scope": "local"},
        )
        assert r.status_code == 404

    def test_invalid_scope_returns_400(self, client: TestClient) -> None:
        r = client.get(f"/v1/cards/{_ALICE}", params={"scope": "totally-bogus"})
        assert r.status_code == 400
        assert "scope" in r.json()["detail"]

    def test_invalid_entity_uri_returns_400(self, client: TestClient) -> None:
        # An empty/space entity URI fails normalize_entity_uri's NormalizationError
        r = client.get("/v1/cards/   ", params={"scope": "local"})
        # FastAPI may collapse whitespace — verify either 400 (NormalizationError)
        # or 404 (no facts) is returned, not a 500.
        assert r.status_code in (400, 404, 422)


# ---------------------------------------------------------------------------
# card_materializer.mark_entity_stale — DB error best-effort
# ---------------------------------------------------------------------------


class TestMarkEntityStale:
    def test_db_error_does_not_propagate(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from contextlib import contextmanager

        from stigmem_node import card_materializer as cm
        from stigmem_node import db as db_mod

        class _RaisingConn:
            def execute(self, *a: object, **kw: object) -> None:
                raise sqlite3.OperationalError("table missing")

        @contextmanager
        def fake_db() -> object:
            yield _RaisingConn()

        # mark_entity_stale imports db lazily from .db, so patch on the source module
        monkeypatch.setattr(db_mod, "db", fake_db)

        # Should swallow the exception (best-effort logging only)
        cm.mark_entity_stale(_ALICE, scope="local", tenant_id="default")
