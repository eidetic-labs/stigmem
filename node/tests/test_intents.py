"""Tests for POST/GET /v1/intents (spec §5.14, §4)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FROM = "stigmem://company.example/agent/assistant"
_TO = "stigmem://company.example/agent/reviewer"
_GOAL = "Review the draft and return a scored rubric."


def _minimal_envelope(**overrides) -> dict:
    base = {
        "from": _FROM,
        "to": [_TO],
        "goal": _GOAL,
        "scope": "company",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# POST /v1/intents — happy paths
# ---------------------------------------------------------------------------


class TestSubmitIntentMinimal:
    def test_returns_201(self, client: TestClient):
        r = client.post("/v1/intents", json=_minimal_envelope())
        assert r.status_code == 201

    def test_response_has_id(self, client: TestClient):
        r = client.post("/v1/intents", json=_minimal_envelope())
        body = r.json()
        assert body["id"].startswith("intent:")

    def test_response_echo_fields(self, client: TestClient):
        r = client.post("/v1/intents", json=_minimal_envelope())
        body = r.json()
        assert body["from"] == _FROM
        assert body["to"] == [_TO]
        assert body["goal"] == _GOAL
        assert body["scope"] == "company"

    def test_response_has_fact_ids(self, client: TestClient):
        r = client.post("/v1/intents", json=_minimal_envelope())
        body = r.json()
        assert isinstance(body["fact_ids"], list)
        assert len(body["fact_ids"]) >= 3  # at minimum: intent:from, intent:goal, intent:to

    def test_client_supplied_id(self, client: TestClient):
        r = client.post("/v1/intents", json=_minimal_envelope(id="intent:my-stable-id"))
        assert r.status_code == 201
        assert r.json()["id"] == "intent:my-stable-id"


class TestSubmitIntentWithEscalation:
    def test_escalation_round_trips(self, client: TestClient):
        payload = _minimal_envelope(escalation={
            "escalate_to": "stigmem://company.example/agent/cto",
            "channel": "stigmem",
            "priority": "high",
            "include_context": True,
        })
        r = client.post("/v1/intents", json=payload)
        assert r.status_code == 201
        esc = r.json()["escalation"]
        assert esc["escalate_to"] == "stigmem://company.example/agent/cto"
        assert esc["priority"] == "high"

    def test_escalation_facts_written(self, client: TestClient):
        payload = _minimal_envelope(escalation={
            "escalate_to": "stigmem://company.example/agent/cto",
            "channel": "stigmem",
            "priority": "critical",
            "include_context": False,
        })
        r = client.post("/v1/intents", json=payload)
        assert r.status_code == 201
        # 4 escalation facts + 3 base facts = at least 7
        assert len(r.json()["fact_ids"]) >= 7


class TestSubmitIntentWithHandoff:
    def test_handoff_round_trips(self, client: TestClient):
        # First assert a fact to use as fact_ref
        fr = client.post("/v1/facts", json={
            "entity": "stigmem://company.example/doc/draft-v1",
            "relation": "memory:status",
            "value": {"type": "string", "v": "reviewed"},
            "source": _FROM,
            "scope": "company",
        })
        fact_id = fr.json()["id"]

        payload = _minimal_envelope(handoff={
            "summary": "Draft reviewed through section 3.",
            "fact_refs": [fact_id],
            "continuation": "Continue from section 4.",
            "artifacts": [{"name": "draft.md", "ref": fact_id}],
        })
        r = client.post("/v1/intents", json=payload)
        assert r.status_code == 201
        h = r.json()["handoff"]
        assert h["summary"] == "Draft reviewed through section 3."
        assert h["continuation"] == "Continue from section 4."
        assert len(h["artifacts"]) == 1


class TestSubmitIntentWithConstraintsAndPreferences:
    def test_constraint_round_trips(self, client: TestClient):
        payload = _minimal_envelope(
            constraint=[{"kind": "budget", "limit": {"type": "number", "v": 500}, "unit": "USD"}],
            preference=[{"kind": "format", "value": {"type": "string", "v": "markdown"}, "weight": 0.8}],
        )
        r = client.post("/v1/intents", json=payload)
        assert r.status_code == 201
        body = r.json()
        assert body["constraint"][0]["kind"] == "budget"
        assert body["preference"][0]["kind"] == "format"
        assert body["preference"][0]["weight"] == pytest.approx(0.8)

    def test_deference_round_trips(self, client: TestClient):
        payload = _minimal_envelope(
            deference=[{
                "condition": "cost > $100",
                "defer_to": "stigmem://company.example/agent/cfo",
                "timeout_s": 300,
            }],
        )
        r = client.post("/v1/intents", json=payload)
        assert r.status_code == 201
        d = r.json()["deference"][0]
        assert d["condition"] == "cost > $100"
        assert d["defer_to"] == "stigmem://company.example/agent/cfo"
        assert d["timeout_s"] == 300


# ---------------------------------------------------------------------------
# POST /v1/intents — validation failures
# ---------------------------------------------------------------------------


class TestSubmitIntentValidation:
    def test_missing_from_returns_422(self, client: TestClient):
        r = client.post("/v1/intents", json={"to": [_TO], "goal": _GOAL})
        assert r.status_code == 422

    def test_missing_to_returns_422(self, client: TestClient):
        r = client.post("/v1/intents", json={"from": _FROM, "goal": _GOAL})
        assert r.status_code == 422

    def test_empty_to_returns_422(self, client: TestClient):
        r = client.post("/v1/intents", json={"from": _FROM, "to": [], "goal": _GOAL})
        assert r.status_code == 422

    def test_missing_goal_returns_422(self, client: TestClient):
        r = client.post("/v1/intents", json={"from": _FROM, "to": [_TO]})
        assert r.status_code == 422

    def test_invalid_scope_returns_422(self, client: TestClient):
        r = client.post("/v1/intents", json=_minimal_envelope(scope="invalid-scope"))
        assert r.status_code == 422

    def test_invalid_escalation_priority_returns_422(self, client: TestClient):
        r = client.post("/v1/intents", json=_minimal_envelope(
            escalation={
                "escalate_to": "stigmem://company.example/agent/cto",
                "channel": "stigmem",
                "priority": "URGENT",  # not a valid priority
                "include_context": True,
            }
        ))
        assert r.status_code == 422

    def test_invalid_escalation_channel_returns_422(self, client: TestClient):
        r = client.post("/v1/intents", json=_minimal_envelope(
            escalation={
                "escalate_to": "stigmem://company.example/agent/cto",
                "channel": "carrier-pigeon",  # not valid
                "priority": "high",
                "include_context": True,
            }
        ))
        assert r.status_code == 422

    def test_duplicate_id_returns_409(self, client: TestClient):
        payload = _minimal_envelope(id="intent:idempotent-id")
        r1 = client.post("/v1/intents", json=payload)
        assert r1.status_code == 201
        r2 = client.post("/v1/intents", json=payload)
        assert r2.status_code == 409


# ---------------------------------------------------------------------------
# GET /v1/intents/:intent_id
# ---------------------------------------------------------------------------


class TestGetIntent:
    def test_get_returns_200_after_post(self, client: TestClient):
        r = client.post("/v1/intents", json=_minimal_envelope())
        intent_id = r.json()["id"]

        r2 = client.get(f"/v1/intents/{intent_id}")
        assert r2.status_code == 200
        body = r2.json()
        assert body["id"] == intent_id
        assert body["goal"] == _GOAL

    def test_get_reconstructs_escalation(self, client: TestClient):
        payload = _minimal_envelope(escalation={
            "escalate_to": "stigmem://company.example/agent/cto",
            "channel": "stigmem",
            "priority": "high",
            "include_context": True,
        })
        r = client.post("/v1/intents", json=payload)
        intent_id = r.json()["id"]

        r2 = client.get(f"/v1/intents/{intent_id}")
        assert r2.status_code == 200
        esc = r2.json()["escalation"]
        assert esc["priority"] == "high"

    def test_get_nonexistent_returns_404(self, client: TestClient):
        r = client.get("/v1/intents/intent:does-not-exist")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Auth tests
# ---------------------------------------------------------------------------


class TestIntentAuth:
    def test_write_required_for_post(self, authed_client: tuple):
        c, key = authed_client
        r = c.post(
            "/v1/intents",
            json=_minimal_envelope(),
            headers={"Authorization": f"Bearer {key}"},
        )
        assert r.status_code == 201

    def test_post_without_key_returns_401_when_auth_required(self, authed_client: tuple):
        c, _ = authed_client
        r = c.post("/v1/intents", json=_minimal_envelope())
        assert r.status_code == 401

    def test_read_only_key_forbidden_on_post(self, tmp_db: str):
        from stigmem_node.auth import create_api_key
        from stigmem_node.main import create_app
        import stigmem_node.settings as sm
        original = sm.settings
        test_settings = sm.Settings(db_path=tmp_db, auth_required=True, node_url="http://t")
        sm.settings = test_settings  # type: ignore
        import stigmem_node.auth as am
        import stigmem_node.db as dm
        am.settings = test_settings  # type: ignore
        dm.settings = test_settings  # type: ignore
        read_key = create_api_key("agent:readonly", ["read"])
        app = create_app()
        with TestClient(app) as c:
            r = c.post(
                "/v1/intents",
                json=_minimal_envelope(),
                headers={"Authorization": f"Bearer {read_key}"},
            )
        sm.settings = original  # type: ignore
        am.settings = original  # type: ignore
        dm.settings = original  # type: ignore
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# Fact-layer idempotency: adapter compat
# ---------------------------------------------------------------------------


class TestAdapterCompat:
    """Verify that facts written via adapter (intent:handoff_to etc.) still work
    alongside facts written via the new POST /v1/intents endpoint."""

    def test_direct_fact_and_envelope_coexist(self, client: TestClient):
        # Old adapter-style write
        client.post("/v1/facts", json={
            "entity": "handoff:legacy-1",
            "relation": "intent:handoff_to",
            "value": {"type": "ref", "v": _TO},
            "source": _FROM,
            "scope": "company",
        })
        # New envelope write
        r = client.post("/v1/intents", json=_minimal_envelope())
        assert r.status_code == 201

        # Both accessible via facts query
        facts_r = client.get("/v1/facts", params={"relation": "intent:handoff_to", "scope": "company"})
        assert facts_r.status_code == 200
        # The envelope also wrote an intent:handoff_to fact (since handoff=None but to is set
        # with the handoff field; in this minimal case no handoff_to fact is written — that's OK)
        # The legacy fact is still there
        legacy_ids = [f["entity"] for f in facts_r.json()["facts"]]
        assert "handoff:legacy-1" in legacy_ids
