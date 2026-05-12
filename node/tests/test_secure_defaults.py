"""Regression: STIGMEM_AUTH_REQUIRED must default to True (secure by default).

Guards against ACM-259 — a freshly deployed node should reject unauthenticated
requests without any explicit configuration.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

import stigmem_node.auth as auth_mod
import stigmem_node.db as db_mod
import stigmem_node.routes.wellknown as wk_mod
import stigmem_node.settings as settings_module
from stigmem_node.db import apply_migrations
from stigmem_node.main import create_app
from stigmem_node.settings import Settings

_FACT = {
    "entity": "user:alice",
    "relation": "memory:role",
    "value": {"type": "string", "v": "CEO"},
    "source": "agent:test",
    "scope": "company",
}


class TestSecureDefault:
    """auth_required must be True by default; unauthenticated requests must be rejected."""

    def test_auth_required_model_default_is_true(self) -> None:
        # Checks the pydantic field default, unaffected by env vars.
        assert Settings.model_fields["auth_required"].default is True

    def test_unauthenticated_requests_rejected_when_auth_enabled(self, tmp_path: object) -> None:
        db_file = str(tmp_path) + "/sec_default.db"  # type: ignore[operator]
        apply_migrations(db_path=db_file)
        # Explicitly enabled to isolate this test from any env-var override.
        test_settings = Settings(db_path=db_file, node_url="http://testnode", auth_required=True)

        original = settings_module.settings
        settings_module.settings = test_settings  # type: ignore[assignment]
        auth_mod.settings = test_settings  # type: ignore[assignment]
        db_mod.settings = test_settings  # type: ignore[assignment]
        wk_mod.settings = test_settings  # type: ignore[assignment]
        try:
            app = create_app()
            with TestClient(app, raise_server_exceptions=True) as c:
                assert c.get("/v1/facts?entity=user:alice&scope=company").status_code == 401
                assert c.post("/v1/facts", json=_FACT).status_code == 401
                # Health and well-known endpoints must remain open.
                assert c.get("/healthz").status_code == 200
        finally:
            settings_module.settings = original  # type: ignore[assignment]
            auth_mod.settings = original  # type: ignore[assignment]
            db_mod.settings = original  # type: ignore[assignment]
            wk_mod.settings = original  # type: ignore[assignment]
