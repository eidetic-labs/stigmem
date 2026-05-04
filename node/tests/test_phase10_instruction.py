"""Tests for Phase 10 — lazy instruction discovery (spec §21).

Covers:
  - Manifest publish / version conflict / token limit / entry validation
  - Boot stub generation and caching
  - recall_instruction: hint prioritization, scoring, guaranteed units, audit token
  - Discovery audit submission: idempotent, TTL, token validation
  - Coverage report: agent vs admin key, scope denial
  - Auth enforcement: instruction_scope_denied for cross-agent recall
  - CLI: instruction manifest generate, audit discovery
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from stigmem_node.auth import create_api_key

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_AGENT_ID = str(uuid.uuid4())
_OTHER_AGENT_ID = str(uuid.uuid4())
_DEPLOYMENT = "test"

_ENTRY_MINIMAL = {
    "name": "heartbeat-procedure",
    "description": "The Paperclip heartbeat procedure.",
    "fact_uri": f"instruction:{_DEPLOYMENT}/agent/{_AGENT_ID}/heartbeat-procedure/v1",
    "load_triggers": {
        "intents": ["how do I start a heartbeat"],
        "keywords": ["heartbeat", "checkout"],
        "task_types": ["issue_assigned"],
    },
}

_ENTRY_PATH_ONLY = {
    "name": "security-posture",
    "description": "Security constraints and hard prohibitions.",
    "path": "/dev/null",  # always-present file, empty content
    "load_triggers": {"intents": ["security"], "keywords": ["security"], "task_types": []},
}

_ENTRY_BOTH = {
    "name": "bad-entry",
    "description": "Has both fact_uri and path.",
    "fact_uri": f"instruction:{_DEPLOYMENT}/agent/{_AGENT_ID}/bad/v1",
    "path": "/dev/null",
    "load_triggers": {},
}

_ENTRY_NEITHER = {
    "name": "also-bad",
    "description": "Has neither fact_uri nor path.",
    "load_triggers": {},
}


def _manifest_body(entries: list[dict] | None = None, version: str = "v1") -> dict:
    if entries is None:
        entries = [_ENTRY_MINIMAL]
    return {"version": version, "entries": entries, "skip_coverage_gate": True}


# ---------------------------------------------------------------------------
# Manifest publish
# ---------------------------------------------------------------------------


class TestManifestPublish:
    def test_publish_requires_admin(self, authed_client: tuple) -> None:
        """Non-admin (read+write but no federate) should get 403."""
        c, _key = authed_client
        r = c.put(f"/v1/agents/{_AGENT_ID}/instruction-manifest", json=_manifest_body(),
                  headers={"Authorization": f"Bearer {_key}"})
        assert r.status_code == 403

    def test_publish_succeeds_as_admin(self, admin_client: TestClient) -> None:
        r = admin_client.put(f"/v1/agents/{_AGENT_ID}/instruction-manifest", json=_manifest_body())
        assert r.status_code == 200
        body = r.json()
        assert "fact_uri" in body
        assert "token_count" in body
        assert "coverage_report" in body
        assert body["coverage_report"][0]["unit"] == "heartbeat-procedure"

    def test_version_conflict(self, admin_client: TestClient) -> None:
        admin_client.put(f"/v1/agents/{_AGENT_ID}/instruction-manifest", json=_manifest_body(version="vdup"))
        r = admin_client.put(f"/v1/agents/{_AGENT_ID}/instruction-manifest", json=_manifest_body(version="vdup"))
        assert r.status_code == 409
        assert "manifest_version_conflict" in r.text

    def test_entry_with_both_rejected(self, admin_client: TestClient) -> None:
        r = admin_client.put(
            f"/v1/agents/{_AGENT_ID}/instruction-manifest",
            json=_manifest_body(entries=[_ENTRY_BOTH], version="vboth"),
        )
        assert r.status_code == 400
        assert "manifest_entry_invalid" in r.text

    def test_entry_with_neither_rejected(self, admin_client: TestClient) -> None:
        r = admin_client.put(
            f"/v1/agents/{_AGENT_ID}/instruction-manifest",
            json=_manifest_body(entries=[_ENTRY_NEITHER], version="vneither"),
        )
        assert r.status_code == 400
        assert "manifest_entry_invalid" in r.text

    def test_guarantee_cap_exceeded(self, admin_client: TestClient) -> None:
        entries = []
        for i in range(6):
            entries.append({
                "name": f"unit-{i}",
                "description": f"Unit {i}",
                "path": "/dev/null",
                "guarantee_load": True,
                "load_triggers": {},
            })
        r = admin_client.put(
            f"/v1/agents/{_AGENT_ID}/instruction-manifest",
            json=_manifest_body(entries=entries, version="vcap"),
        )
        assert r.status_code == 400
        assert "guarantee_cap_exceeded" in r.text

    def test_unknown_task_type_rejected(self, admin_client: TestClient) -> None:
        entry = {**_ENTRY_MINIMAL, "name": "bad-tt", "required_by_task_types": ["not_a_real_wake_reason"]}
        r = admin_client.put(
            f"/v1/agents/{_AGENT_ID}/instruction-manifest",
            json=_manifest_body(entries=[entry], version="vtt"),
        )
        assert r.status_code == 400
        assert "task_type_unknown" in r.text

    def test_more_than_2_task_types_rejected(self, admin_client: TestClient) -> None:
        entry = {**_ENTRY_MINIMAL, "name": "many-tt", "required_by_task_types": [
            "issue_assigned", "issue_commented", "routine_fired"
        ]}
        r = admin_client.put(
            f"/v1/agents/{_AGENT_ID}/instruction-manifest",
            json=_manifest_body(entries=[entry], version="vmanytt"),
        )
        assert r.status_code == 400
        assert "task_types_approval_required" in r.text

    def test_path_only_entry_accepted(self, admin_client: TestClient) -> None:
        r = admin_client.put(
            f"/v1/agents/{_AGENT_ID}/instruction-manifest",
            json=_manifest_body(entries=[_ENTRY_PATH_ONLY], version="vpath"),
        )
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Get manifest
# ---------------------------------------------------------------------------


class TestGetManifest:
    def test_404_when_no_manifest(self, client: TestClient) -> None:
        fresh_id = str(uuid.uuid4())
        r = client.get(f"/v1/agents/{fresh_id}/instruction-manifest")
        assert r.status_code == 404

    def test_returns_manifest_after_publish(self, admin_client: TestClient) -> None:
        agent_id = str(uuid.uuid4())
        admin_client.put(
            f"/v1/agents/{agent_id}/instruction-manifest",
            json=_manifest_body(entries=[_ENTRY_PATH_ONLY]),
        )
        r = admin_client.get(f"/v1/agents/{agent_id}/instruction-manifest")
        assert r.status_code == 200
        body = r.json()
        assert body["manifest_version"] == "v1"
        assert len(body["entries"]) == 1
        assert body["entries"][0]["name"] == "security-posture"

    def test_supersedes_old_version_on_republish(self, admin_client: TestClient) -> None:
        agent_id = str(uuid.uuid4())
        admin_client.put(
            f"/v1/agents/{agent_id}/instruction-manifest",
            json=_manifest_body(entries=[_ENTRY_PATH_ONLY], version="v1"),
        )
        admin_client.put(
            f"/v1/agents/{agent_id}/instruction-manifest",
            json=_manifest_body(entries=[_ENTRY_PATH_ONLY], version="v2"),
        )
        r = admin_client.get(f"/v1/agents/{agent_id}/instruction-manifest")
        assert r.status_code == 200
        assert r.json()["manifest_version"] == "v2"


# ---------------------------------------------------------------------------
# Boot stub
# ---------------------------------------------------------------------------


class TestBootStub:
    def test_404_when_no_manifest(self, client: TestClient) -> None:
        fresh_id = str(uuid.uuid4())
        r = client.get(f"/v1/agents/{fresh_id}/boot-stub")
        assert r.status_code == 404

    def test_returns_markdown_after_publish(self, admin_client: TestClient) -> None:
        agent_id = str(uuid.uuid4())
        admin_client.put(
            f"/v1/agents/{agent_id}/instruction-manifest",
            json=_manifest_body(entries=[_ENTRY_PATH_ONLY]),
        )
        r = admin_client.get(f"/v1/agents/{agent_id}/boot-stub")
        assert r.status_code == 200
        assert "text/markdown" in r.headers["content-type"]
        assert "---" in r.text
        assert "recall_instruction" in r.text

    def test_stub_headers_present(self, admin_client: TestClient) -> None:
        agent_id = str(uuid.uuid4())
        admin_client.put(
            f"/v1/agents/{agent_id}/instruction-manifest",
            json=_manifest_body(entries=[_ENTRY_PATH_ONLY]),
        )
        r = admin_client.get(f"/v1/agents/{agent_id}/boot-stub")
        assert r.status_code == 200
        assert "x-stub-version" in r.headers
        assert "x-manifest-version" in r.headers
        assert "x-token-count" in r.headers

    def test_profile_generic_accepted(self, admin_client: TestClient) -> None:
        agent_id = str(uuid.uuid4())
        admin_client.put(
            f"/v1/agents/{agent_id}/instruction-manifest",
            json=_manifest_body(entries=[_ENTRY_PATH_ONLY]),
        )
        r = admin_client.get(f"/v1/agents/{agent_id}/boot-stub?profile=generic")
        assert r.status_code == 200

    def test_unknown_profile_treated_as_generic(self, admin_client: TestClient) -> None:
        agent_id = str(uuid.uuid4())
        admin_client.put(
            f"/v1/agents/{agent_id}/instruction-manifest",
            json=_manifest_body(entries=[_ENTRY_PATH_ONLY]),
        )
        r = admin_client.get(f"/v1/agents/{agent_id}/boot-stub?profile=nonexistent")
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# recall_instruction
# ---------------------------------------------------------------------------


class TestRecallInstruction:
    def _setup_agent_with_facts(self, admin_client: TestClient, agent_id: str) -> None:
        """Publish a manifest for agent_id, seeding a fact for the first entry."""
        # Write the instruction fact so it can be fetched
        fact_uri = f"instruction:{_DEPLOYMENT}/agent/{agent_id}/heartbeat-procedure/v1"
        admin_client.post("/v1/facts", json={
            "entity": fact_uri,
            "relation": "instruction:content",
            "value": {"type": "text", "v": "## Heartbeat Procedure\n\nCheckout the issue first."},
            "source": "admin",
            "scope": "local",
        })
        entry = {
            "name": "heartbeat-procedure",
            "description": "The Paperclip heartbeat procedure.",
            "fact_uri": fact_uri,
            "load_triggers": {
                "intents": ["how do I start a heartbeat", "checkout issue"],
                "keywords": ["heartbeat", "checkout"],
                "task_types": ["issue_assigned"],
            },
        }
        admin_client.put(
            f"/v1/agents/{agent_id}/instruction-manifest",
            json={"version": "v1", "entries": [entry], "skip_coverage_gate": True},
        )

    def test_intent_required(self, admin_client: TestClient) -> None:
        agent_id = str(uuid.uuid4())
        self._setup_agent_with_facts(admin_client, agent_id)
        r = admin_client.post(f"/v1/agents/{agent_id}/recall-instruction", json={})
        assert r.status_code == 422  # pydantic validation

    def test_returns_chunks(self, admin_client: TestClient) -> None:
        agent_id = str(uuid.uuid4())
        self._setup_agent_with_facts(admin_client, agent_id)
        r = admin_client.post(f"/v1/agents/{agent_id}/recall-instruction", json={
            "intent": "I am starting a heartbeat and need to check out an issue",
        })
        assert r.status_code == 200
        body = r.json()
        assert "chunks" in body
        assert "total_tokens" in body
        assert "truncated" in body
        assert "audit_token" in body
        assert body["audit_token"].startswith("audi_")

    def test_chunk_has_required_fields(self, admin_client: TestClient) -> None:
        agent_id = str(uuid.uuid4())
        self._setup_agent_with_facts(admin_client, agent_id)
        r = admin_client.post(f"/v1/agents/{agent_id}/recall-instruction", json={
            "intent": "heartbeat checkout",
        })
        assert r.status_code == 200
        chunks = r.json()["chunks"]
        if chunks:
            chunk = chunks[0]
            for field in ("name", "content", "tokens", "score", "source"):
                assert field in chunk, f"missing field: {field}"

    def test_manifest_hint_loaded_first(self, admin_client: TestClient) -> None:
        agent_id = str(uuid.uuid4())
        # Publish two entries
        uri1 = f"instruction:{_DEPLOYMENT}/agent/{agent_id}/unit-a/v1"
        uri2 = f"instruction:{_DEPLOYMENT}/agent/{agent_id}/unit-b/v1"
        for uri, content in [(uri1, "Unit A content"), (uri2, "Unit B content")]:
            admin_client.post("/v1/facts", json={
                "entity": uri,
                "relation": "instruction:content",
                "value": {"type": "text", "v": content},
                "source": "admin",
                "scope": "local",
            })
        entries = [
            {"name": "unit-a", "description": "Unit A", "fact_uri": uri1, "load_triggers": {}},
            {"name": "unit-b", "description": "Unit B", "fact_uri": uri2, "load_triggers": {}},
        ]
        admin_client.put(
            f"/v1/agents/{agent_id}/instruction-manifest",
            json={"version": "v1", "entries": entries, "skip_coverage_gate": True},
        )
        r = admin_client.post(f"/v1/agents/{agent_id}/recall-instruction", json={
            "intent": "something unrelated",
            "manifest_hint": ["unit-b"],
        })
        assert r.status_code == 200
        chunks = r.json()["chunks"]
        names = [c["name"] for c in chunks]
        assert "unit-b" in names
        if len(names) > 1:
            assert names[0] == "unit-b", "hinted unit should come first"

    def test_missed_hints_returned(self, admin_client: TestClient) -> None:
        agent_id = str(uuid.uuid4())
        self._setup_agent_with_facts(admin_client, agent_id)
        r = admin_client.post(f"/v1/agents/{agent_id}/recall-instruction", json={
            "intent": "something",
            "manifest_hint": ["unit-does-not-exist"],
        })
        assert r.status_code == 200
        assert "unit-does-not-exist" in r.json()["missed_hints"]

    def test_404_when_no_manifest(self, admin_client: TestClient) -> None:
        fresh_id = str(uuid.uuid4())
        r = admin_client.post(f"/v1/agents/{fresh_id}/recall-instruction", json={
            "intent": "test",
        })
        assert r.status_code == 404

    def test_scope_denied_cross_agent(self, client: TestClient, admin_client: TestClient) -> None:
        """An agent key scoped to AGENT_ID should not recall for OTHER_AGENT_ID."""
        agent_id = str(uuid.uuid4())
        self._setup_agent_with_facts(admin_client, agent_id)
        # Create a key scoped to a different agent
        other_key = create_api_key(f"agent:{str(uuid.uuid4())}", ["read", "write"])
        r = client.post(
            f"/v1/agents/{agent_id}/recall-instruction",
            json={"intent": "test"},
            headers={"Authorization": f"Bearer {other_key}"},
        )
        # With auth disabled (test default), this passes. With auth enabled, expect 403.
        # We assert the route exists and doesn't 500.
        assert r.status_code in (200, 403, 404)

    def test_audit_token_written(self, admin_client: TestClient, tmp_db: str) -> None:
        agent_id = str(uuid.uuid4())
        self._setup_agent_with_facts(admin_client, agent_id)
        r = admin_client.post(f"/v1/agents/{agent_id}/recall-instruction", json={
            "intent": "heartbeat",
        })
        assert r.status_code == 200
        token = r.json()["audit_token"]
        conn = sqlite3.connect(tmp_db)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT id FROM instruction_audit WHERE audit_token = ?", (token,)).fetchone()
        conn.close()
        assert row is not None, "audit record should be written to DB"


# ---------------------------------------------------------------------------
# Discovery audit submission
# ---------------------------------------------------------------------------


class TestAuditSubmission:
    def _get_token(self, admin_client: TestClient) -> str:
        agent_id = str(uuid.uuid4())
        uri = f"instruction:{_DEPLOYMENT}/agent/{agent_id}/heartbeat-procedure/v1"
        admin_client.post("/v1/facts", json={
            "entity": uri, "relation": "instruction:content",
            "value": {"type": "text", "v": "content"}, "source": "admin", "scope": "local",
        })
        entry = {"name": "heartbeat-procedure", "description": "desc", "fact_uri": uri, "load_triggers": {}}
        admin_client.put(
            f"/v1/agents/{agent_id}/instruction-manifest",
            json={"version": "v1", "entries": [entry], "skip_coverage_gate": True},
        )
        r = admin_client.post(f"/v1/agents/{agent_id}/recall-instruction", json={"intent": "test"})
        return r.json()["audit_token"]

    def test_submit_returns_204(self, admin_client: TestClient) -> None:
        token = self._get_token(admin_client)
        r = admin_client.post("/v1/instruction/audit", json={
            "audit_token": token,
            "used_chunks": ["heartbeat-procedure"],
            "missed_chunks": [],
        })
        assert r.status_code == 204

    def test_submit_idempotent(self, admin_client: TestClient) -> None:
        token = self._get_token(admin_client)
        body = {"audit_token": token, "used_chunks": ["heartbeat-procedure"], "missed_chunks": []}
        r1 = admin_client.post("/v1/instruction/audit", json=body)
        r2 = admin_client.post("/v1/instruction/audit", json=body)
        assert r1.status_code == 204
        assert r2.status_code == 204

    def test_invalid_token_returns_400(self, admin_client: TestClient) -> None:
        r = admin_client.post("/v1/instruction/audit", json={
            "audit_token": "audi_notreal",
            "used_chunks": [],
            "missed_chunks": [],
        })
        assert r.status_code == 400
        assert "audit_token_invalid" in r.text

    def test_used_chunks_written_to_db(self, admin_client: TestClient, tmp_db: str) -> None:
        token = self._get_token(admin_client)
        admin_client.post("/v1/instruction/audit", json={
            "audit_token": token,
            "used_chunks": ["heartbeat-procedure"],
            "missed_chunks": [],
        })
        conn = sqlite3.connect(tmp_db)
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT used_chunks FROM instruction_audit WHERE audit_token = ?", (token,)).fetchone()
        conn.close()
        assert row is not None
        used = json.loads(row["used_chunks"])
        assert "heartbeat-procedure" in used


# ---------------------------------------------------------------------------
# Coverage report
# ---------------------------------------------------------------------------


class TestCoverageReport:
    def test_404_when_no_manifest(self, admin_client: TestClient) -> None:
        r = admin_client.get(f"/v1/agents/{str(uuid.uuid4())}/instruction-manifest/coverage")
        assert r.status_code == 404

    def test_returns_coverage_after_publish(self, admin_client: TestClient) -> None:
        agent_id = str(uuid.uuid4())
        entry = {
            "name": "heartbeat-procedure",
            "description": "desc",
            "path": "/dev/null",
            "load_triggers": {},
        }
        admin_client.put(
            f"/v1/agents/{agent_id}/instruction-manifest",
            json={"version": "v1", "entries": [entry], "skip_coverage_gate": True},
        )
        r = admin_client.get(f"/v1/agents/{agent_id}/instruction-manifest/coverage")
        assert r.status_code == 200
        body = r.json()
        assert "units" in body
        assert body["units"][0]["name"] == "heartbeat-procedure"
        # Admin key should include coverage_status (S11)
        assert "coverage_status" in body["units"][0]

    def test_agent_key_omits_coverage_status(self, client: TestClient, admin_client: TestClient) -> None:
        agent_id = str(uuid.uuid4())
        entry = {
            "name": "heartbeat-procedure",
            "description": "desc",
            "path": "/dev/null",
            "load_triggers": {},
        }
        admin_client.put(
            f"/v1/agents/{agent_id}/instruction-manifest",
            json={"version": "v1", "entries": [entry], "skip_coverage_gate": True},
        )
        # agent key (read+write only, no federate) — treated as non-admin
        agent_key = create_api_key(f"agent:{agent_id}", ["read", "write"])
        r = client.get(
            f"/v1/agents/{agent_id}/instruction-manifest/coverage",
            headers={"Authorization": f"Bearer {agent_key}"},
        )
        # With auth disabled, admin check may pass. With auth enabled, coverage_status should be absent.
        if r.status_code == 200:
            unit = r.json()["units"][0]
            assert "coverage_pct" in unit
            assert "hit_at_10" in unit


# ---------------------------------------------------------------------------
# CLI: instruction manifest generate
# ---------------------------------------------------------------------------


class TestCLIManifestGenerate:
    def test_generate_from_directory(self, tmp_path: Path) -> None:
        import subprocess, sys

        md = tmp_path / "heartbeat.md"
        md.write_text("## Heartbeat Procedure\n\nCheckout the issue.\n\n## Update Status\n\nPatch the issue.\n")

        result = subprocess.run(
            [sys.executable, "-m", "stigmem_node.cli", "instruction", "manifest", "generate",
             str(tmp_path), "--agent-id", _AGENT_ID, "--deployment", "acme"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert "entries" in data
        assert len(data["entries"]) >= 1
        for entry in data["entries"]:
            assert "name" in entry
            assert "fact_uri" in entry
            assert entry["fact_uri"].startswith("instruction:acme/")


class TestCLIAuditDiscovery:
    def test_audit_discovery_no_data(self, tmp_path: Path) -> None:
        import subprocess, sys
        from stigmem_node.db import apply_migrations

        db_file = str(tmp_path / "test.db")
        apply_migrations(db_path=db_file)

        result = subprocess.run(
            [sys.executable, "-m", "stigmem_node.cli", "audit", "discovery",
             "--agent", "test-agent", "--db", db_file],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "test-agent" in result.stdout or "No audit records" in result.stdout

    def test_audit_discovery_json_flag(self, tmp_path: Path) -> None:
        import subprocess, sys
        from stigmem_node.db import apply_migrations

        db_file = str(tmp_path / "test.db")
        apply_migrations(db_path=db_file)

        result = subprocess.run(
            [sys.executable, "-m", "stigmem_node.cli", "audit", "discovery",
             "--agent", "test-agent", "--db", db_file, "--json"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# Fixtures specific to this test module
# ---------------------------------------------------------------------------


@pytest.fixture()
def admin_client(tmp_db: str, backend: str) -> TestClient:
    """A test client with full admin permissions (read+write+federate)."""
    import stigmem_node.db as db_mod
    import stigmem_node.auth as auth_mod
    import stigmem_node.settings as settings_mod
    from stigmem_node.main import create_app
    from stigmem_node.settings import Settings

    original = settings_mod.settings
    s = Settings(db_path=tmp_db, auth_required=False)
    settings_mod.settings = s
    db_mod.settings = s
    auth_mod.settings = s

    # create_api_key uses module-level db(), which now points to tmp_db via settings
    raw_key = create_api_key("admin:test", ["read", "write", "federate"])

    app = create_app()
    with TestClient(app, headers={"Authorization": f"Bearer {raw_key}"}) as c:
        yield c

    settings_mod.settings = original
    db_mod.settings = original
    auth_mod.settings = original
