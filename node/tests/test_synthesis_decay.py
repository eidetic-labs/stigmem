"""Conformance tests for synthesize_scope and decay sweeper (EG-63, Phase 6)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Shared test fact fixtures
# ---------------------------------------------------------------------------

FACT_A = {
    "entity": "stigmem://test/user/alice",
    "relation": "test:role",
    "value": {"type": "string", "v": "admin"},
    "source": "stigmem://test/source/hr",
    "confidence": 0.9,
    "scope": "local",
}

FACT_B = {
    "entity": "stigmem://test/user/bob",
    "relation": "test:role",
    "value": {"type": "string", "v": "viewer"},
    "source": "stigmem://test/source/hr",
    "confidence": 0.5,
    "scope": "local",
}

# Contradicts FACT_A (same entity + relation + scope, different value/source)
FACT_C = {
    "entity": "stigmem://test/user/alice",
    "relation": "test:role",
    "value": {"type": "string", "v": "viewer"},
    "source": "stigmem://test/source/ops",
    "confidence": 0.3,
    "scope": "local",
}


# ===========================================================================
# synthesize_scope
# ===========================================================================


class TestSynthesizeScope:
    def test_empty_scope_returns_zero_facts(self, client: TestClient) -> None:
        r = client.get("/v1/scopes/local/synthesize")
        assert r.status_code == 200
        data = r.json()
        assert data["scope"] == "local"
        assert data["fact_count"] == 0
        assert data["facts"] == []
        assert data["mean_confidence"] == 0.0
        assert data["contradiction_count"] == 0
        assert data["freshest_timestamp"] is None
        assert data["oldest_timestamp"] is None

    def test_facts_ordered_by_confidence_descending(self, client: TestClient) -> None:
        client.post("/v1/facts", json=FACT_B)  # 0.5 first to test reordering
        client.post("/v1/facts", json=FACT_A)  # 0.9
        r = client.get("/v1/scopes/local/synthesize")
        assert r.status_code == 200
        data = r.json()
        user_facts = [f for f in data["facts"] if f["entity"].startswith("stigmem://test/")]
        confs = [f["confidence"] for f in user_facts]
        assert confs == sorted(confs, reverse=True)

    def test_mean_confidence_computed_over_all_returned_facts(self, client: TestClient) -> None:
        client.post("/v1/facts", json=FACT_A)
        client.post("/v1/facts", json=FACT_B)
        r = client.get("/v1/scopes/local/synthesize")
        data = r.json()
        # mean should incorporate all facts returned (including any system meta-facts)
        returned_confs = [f["confidence"] for f in data["facts"]]
        expected_mean = sum(returned_confs) / len(returned_confs)
        assert data["mean_confidence"] == pytest.approx(expected_mean, rel=1e-5)

    def test_contradiction_flags_set_on_conflicting_facts(self, client: TestClient) -> None:
        client.post("/v1/facts", json=FACT_A)
        client.post("/v1/facts", json=FACT_C)  # contradicts FACT_A
        r = client.get("/v1/scopes/local/synthesize")
        assert r.status_code == 200
        data = r.json()

        alice_facts = [
            f for f in data["facts"] if f["entity"] == "stigmem://test/user/alice"
        ]
        assert len(alice_facts) == 2, "both alice facts must appear in synthesis"
        for f in alice_facts:
            assert f["contradicted"] is True, f"expected contradicted=True on {f}"

        assert data["contradiction_count"] >= 2

    def test_non_conflicting_facts_not_marked_contradicted(self, client: TestClient) -> None:
        client.post("/v1/facts", json=FACT_A)
        client.post("/v1/facts", json=FACT_B)  # different entity — no conflict
        r = client.get("/v1/scopes/local/synthesize")
        data = r.json()
        user_facts = [f for f in data["facts"] if f["entity"].startswith("stigmem://test/")]
        for f in user_facts:
            assert f["contradicted"] is False

    def test_freshness_metadata_present_and_non_negative(self, client: TestClient) -> None:
        client.post("/v1/facts", json=FACT_A)
        r = client.get("/v1/scopes/local/synthesize")
        data = r.json()
        user_facts = [f for f in data["facts"] if f["entity"].startswith("stigmem://test/")]
        assert len(user_facts) >= 1
        fact = user_facts[0]
        assert "timestamp" in fact
        assert "age_seconds" in fact
        assert fact["age_seconds"] >= 0
        assert fact["is_expired"] is False
        assert "synthesized_at" in data

    def test_invalid_scope_returns_400(self, client: TestClient) -> None:
        r = client.get("/v1/scopes/unknown_scope/synthesize")
        assert r.status_code == 400

    def test_expired_facts_excluded_by_default(self, client: TestClient) -> None:
        past = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        client.post("/v1/facts", json={**FACT_A, "valid_until": past})
        r = client.get("/v1/scopes/local/synthesize")
        data = r.json()
        user_facts = [f for f in data["facts"] if f["entity"].startswith("stigmem://test/")]
        assert len(user_facts) == 0

    def test_include_expired_returns_expired_facts(self, client: TestClient) -> None:
        past = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        client.post("/v1/facts", json={**FACT_A, "valid_until": past})
        r = client.get("/v1/scopes/local/synthesize?include_expired=true")
        data = r.json()
        user_facts = [f for f in data["facts"] if f["entity"].startswith("stigmem://test/")]
        assert len(user_facts) == 1
        assert user_facts[0]["is_expired"] is True
        assert data["expired_fact_count"] >= 1

    def test_system_facts_not_marked_contradicted(self, client: TestClient) -> None:
        # Asserting contradicting facts creates stigmem:conflict: system facts in the same scope
        client.post("/v1/facts", json=FACT_A)
        client.post("/v1/facts", json=FACT_C)
        r = client.get("/v1/scopes/local/synthesize")
        data = r.json()
        system_facts = [
            f for f in data["facts"]
            if f["entity"].startswith("stigmem:") and not f["entity"].startswith("stigmem://")
        ]
        for sf in system_facts:
            assert sf["contradicted"] is False, f"system fact {sf['entity']} must not be contradicted"

    def test_scope_isolation(self, client: TestClient) -> None:
        team_fact = {**FACT_A, "scope": "team"}
        client.post("/v1/facts", json=FACT_A)       # local
        client.post("/v1/facts", json=team_fact)    # team
        r_local = client.get("/v1/scopes/local/synthesize")
        r_team = client.get("/v1/scopes/team/synthesize")
        local_user = [f for f in r_local.json()["facts"] if f["entity"].startswith("stigmem://test/")]
        team_user = [f for f in r_team.json()["facts"] if f["entity"].startswith("stigmem://test/")]
        assert len(local_user) == 1
        assert len(team_user) == 1
        assert local_user[0]["entity"] == team_user[0]["entity"]  # same entity, different scopes


# ===========================================================================
# decay sweeper
# ===========================================================================


class TestDecaySweeper:
    def test_ttl_zero_decays_all_non_expiring_facts(self, client: TestClient) -> None:
        client.post("/v1/facts", json=FACT_A)
        client.post("/v1/facts", json=FACT_B)

        r = client.post("/v1/decay/sweep?ttl_seconds=0")
        assert r.status_code == 200
        data = r.json()
        assert data["decayed"] >= 2
        assert data["dry_run"] is False

        # Facts should now be expired and excluded from default query
        q = client.get("/v1/facts")
        user_facts = [f for f in q.json()["facts"] if f["entity"].startswith("stigmem://test/")]
        assert len(user_facts) == 0

    def test_min_confidence_decays_only_below_threshold(self, client: TestClient) -> None:
        client.post("/v1/facts", json=FACT_A)  # confidence=0.9
        client.post("/v1/facts", json=FACT_B)  # confidence=0.5

        r = client.post("/v1/decay/sweep?min_confidence=0.6")
        assert r.status_code == 200
        data = r.json()
        assert data["decayed"] == 1  # only FACT_B (0.5 < 0.6)

        q = client.get("/v1/facts")
        surviving = [f for f in q.json()["facts"] if f["entity"].startswith("stigmem://test/")]
        assert len(surviving) == 1
        assert surviving[0]["confidence"] == pytest.approx(0.9)

    def test_dry_run_reports_count_without_writing(self, client: TestClient) -> None:
        client.post("/v1/facts", json=FACT_A)

        r = client.post("/v1/decay/sweep?ttl_seconds=0&dry_run=true")
        assert r.status_code == 200
        data = r.json()
        assert data["dry_run"] is True
        assert data["decayed"] == 0
        assert data["scanned"] >= 1

        # Fact still alive after dry run
        q = client.get("/v1/facts")
        user_facts = [f for f in q.json()["facts"] if f["entity"].startswith("stigmem://test/")]
        assert len(user_facts) == 1

    def test_scope_filter_restricts_sweep(self, client: TestClient) -> None:
        team_fact = {**FACT_A, "scope": "team"}
        client.post("/v1/facts", json=FACT_A)   # local
        client.post("/v1/facts", json=team_fact)  # team

        r = client.post("/v1/decay/sweep?ttl_seconds=0&scope=local")
        assert r.status_code == 200

        q_local = client.get("/v1/facts?scope=local")
        q_team = client.get("/v1/facts?scope=team")
        local_user = [f for f in q_local.json()["facts"] if f["entity"].startswith("stigmem://test/")]
        team_user = [f for f in q_team.json()["facts"] if f["entity"].startswith("stigmem://test/")]
        assert len(local_user) == 0, "local fact should be expired"
        assert len(team_user) == 1, "team fact should be untouched"

    def test_system_facts_not_decayed(self, client: TestClient) -> None:
        # Contradiction creates stigmem:conflict: system facts in the same scope
        client.post("/v1/facts", json=FACT_A)
        client.post("/v1/facts", json=FACT_C)

        r = client.post("/v1/decay/sweep?ttl_seconds=0")
        assert r.status_code == 200

        # Include expired + contradicted to see all facts
        q = client.get("/v1/facts?include_expired=true&include_contradicted=true")
        all_facts = q.json()["facts"]
        system_facts = [
            f for f in all_facts
            if f["entity"].startswith("stigmem:") and not f["entity"].startswith("stigmem://")
        ]
        assert len(system_facts) > 0, "expect conflict meta-facts to exist"
        for sf in system_facts:
            assert sf["valid_until"] is None, f"system fact {sf['entity']} was wrongly decayed"

    def test_empty_db_sweep_returns_zero(self, client: TestClient) -> None:
        r = client.post("/v1/decay/sweep?ttl_seconds=60")
        assert r.status_code == 200
        data = r.json()
        assert data["scanned"] == 0
        assert data["decayed"] == 0

    def test_invalid_scope_returns_400(self, client: TestClient) -> None:
        r = client.post("/v1/decay/sweep?scope=invalid_scope&ttl_seconds=0")
        assert r.status_code == 400

    def test_already_expired_facts_not_double_counted(self, client: TestClient) -> None:
        past = (datetime.now(UTC) - timedelta(hours=2)).isoformat()
        client.post("/v1/facts", json={**FACT_A, "valid_until": past})

        # Should not touch already-expired facts
        r = client.post("/v1/decay/sweep?ttl_seconds=0")
        assert r.status_code == 200
        data = r.json()
        # FACT_A already has valid_until set, so it's excluded from TTL sweep
        assert data["scanned"] == 0

    def test_ttl_and_min_confidence_combined(self, client: TestClient) -> None:
        client.post("/v1/facts", json=FACT_A)  # conf=0.9, no valid_until
        client.post("/v1/facts", json=FACT_B)  # conf=0.5, no valid_until

        # ttl=0 catches both; min_confidence=0.6 also catches FACT_B — union, no double-count
        r = client.post("/v1/decay/sweep?ttl_seconds=0&min_confidence=0.6")
        assert r.status_code == 200
        data = r.json()
        assert data["decayed"] >= 2  # both decayed, FACT_B only counted once

    def test_all_scopes_no_scope_filter(self, client: TestClient) -> None:
        team_fact = {**FACT_B, "scope": "team"}
        client.post("/v1/facts", json=FACT_A)   # local
        client.post("/v1/facts", json=team_fact)  # team

        r = client.post("/v1/decay/sweep?ttl_seconds=0")
        assert r.status_code == 200
        data = r.json()
        assert data["decayed"] >= 2  # both scopes swept
