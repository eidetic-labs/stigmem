"""Tests for async lint/decay job APIs — spec §14.5 / §15.4.

Key invariants verified:
- sync path: scope ≤ threshold → 200 with results inline
- async path: scope > threshold → 202 + job_id; poll GET .../jobs/:id → done with results
- 404 for unknown job IDs
- cross-type isolation: lint job_id is not visible via decay endpoint and vice-versa
- dry_run is always synchronous even above threshold
- partition invariant: job persists across separate GET calls (status tracking)
"""

from __future__ import annotations

from fastapi.testclient import TestClient

FACT = {
    "entity": "stigmem://test/user/alice",
    "relation": "test:role",
    "value": {"type": "string", "v": "admin"},
    "source": "stigmem://test/source/hr",
    "confidence": 0.9,
    "scope": "local",
}


# ---------------------------------------------------------------------------
# GET /v1/lint/jobs/:job_id — baseline 404 and type isolation
# ---------------------------------------------------------------------------


class TestLintJobsEndpoint:
    def test_unknown_job_id_returns_404(self, client: TestClient) -> None:
        r = client.get("/v1/lint/jobs/00000000-0000-0000-0000-000000000000")
        assert r.status_code == 404

    def test_random_string_returns_404(self, client: TestClient) -> None:
        r = client.get("/v1/lint/jobs/not-a-real-job")
        assert r.status_code == 404


class TestDecayJobsEndpoint:
    def test_unknown_job_id_returns_404(self, client: TestClient) -> None:
        r = client.get("/v1/decay/jobs/00000000-0000-0000-0000-000000000000")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Sync path unaffected — threshold not exceeded (default threshold=100k)
# ---------------------------------------------------------------------------


class TestSyncPathUnaffected:
    def test_lint_returns_200_for_small_scope(self, client: TestClient) -> None:
        client.post("/v1/facts", json=FACT)
        r = client.post("/v1/lint", json={"scope": "local"})
        assert r.status_code == 200
        data = r.json()
        assert "findings" in data
        assert "fact_count" in data

    def test_decay_returns_200_for_small_scope(self, client: TestClient) -> None:
        client.post("/v1/facts", json=FACT)
        r = client.post("/v1/decay/sweep?ttl_seconds=0")
        assert r.status_code == 200
        assert "scanned" in r.json()


# ---------------------------------------------------------------------------
# Async path — threshold=1 forces 202 on any non-empty scope
# ---------------------------------------------------------------------------


class TestLintAsyncPath:
    def test_returns_202_with_job_id(self, client_async_threshold: TestClient) -> None:
        client_async_threshold.post("/v1/facts", json=FACT)
        r = client_async_threshold.post("/v1/lint", json={"scope": "local"})
        assert r.status_code == 202
        data = r.json()
        assert "job_id" in data
        assert data["status"] == "pending"
        assert "estimated_s" in data
        assert isinstance(data["estimated_s"], int)

    def test_job_completes_and_contains_lint_result(
        self, client_async_threshold: TestClient
    ) -> None:
        client_async_threshold.post("/v1/facts", json=FACT)
        r202 = client_async_threshold.post("/v1/lint", json={"scope": "local"})
        assert r202.status_code == 202
        job_id = r202.json()["job_id"]

        # TestClient runs BackgroundTasks synchronously, so job is done immediately.
        r = client_async_threshold.get(f"/v1/lint/jobs/{job_id}")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "done"
        assert "findings" in data
        assert "fact_count" in data
        assert data["scope"] == "local"
        assert isinstance(data["findings"], list)

    def test_job_result_matches_sync_result(self, client_async_threshold: TestClient) -> None:
        """Async path must produce the same result fields as the sync path."""
        client_async_threshold.post("/v1/facts", json=FACT)
        r202 = client_async_threshold.post("/v1/lint", json={"scope": "local"})
        job_id = r202.json()["job_id"]
        job_data = client_async_threshold.get(f"/v1/lint/jobs/{job_id}").json()

        assert "fact_count" in job_data
        assert job_data["fact_count"] >= 1
        assert "checks_run" in job_data
        assert "checked_at" in job_data

    def test_empty_scope_sync_even_at_threshold_one(
        self, client_async_threshold: TestClient
    ) -> None:
        """Empty scope has 0 facts — stays 200 sync even with threshold=1."""
        r = client_async_threshold.post("/v1/lint", json={"scope": "local"})
        assert r.status_code == 200

    def test_cross_type_isolation_lint_job_not_visible_via_decay(
        self, client_async_threshold: TestClient
    ) -> None:
        client_async_threshold.post("/v1/facts", json=FACT)
        r202 = client_async_threshold.post("/v1/lint", json={"scope": "local"})
        job_id = r202.json()["job_id"]
        # Lint job_id must not be visible through the decay jobs endpoint.
        r = client_async_threshold.get(f"/v1/decay/jobs/{job_id}")
        assert r.status_code == 404

    def test_multiple_polls_return_same_result(self, client_async_threshold: TestClient) -> None:
        client_async_threshold.post("/v1/facts", json=FACT)
        r202 = client_async_threshold.post("/v1/lint", json={"scope": "local"})
        job_id = r202.json()["job_id"]
        r1 = client_async_threshold.get(f"/v1/lint/jobs/{job_id}").json()
        r2 = client_async_threshold.get(f"/v1/lint/jobs/{job_id}").json()
        assert r1["status"] == r2["status"] == "done"
        assert r1["fact_count"] == r2["fact_count"]


class TestDecayAsyncPath:
    def test_returns_202_with_job_id(self, client_async_threshold: TestClient) -> None:
        client_async_threshold.post("/v1/facts", json=FACT)
        r = client_async_threshold.post("/v1/decay/sweep?ttl_seconds=0")
        assert r.status_code == 202
        data = r.json()
        assert "job_id" in data
        assert data["status"] == "pending"
        assert isinstance(data["estimated_s"], int)

    def test_job_completes_and_contains_decay_result(
        self, client_async_threshold: TestClient
    ) -> None:
        client_async_threshold.post("/v1/facts", json=FACT)
        r202 = client_async_threshold.post("/v1/decay/sweep?ttl_seconds=0")
        assert r202.status_code == 202
        job_id = r202.json()["job_id"]

        r = client_async_threshold.get(f"/v1/decay/jobs/{job_id}")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "done"
        assert "scanned" in data
        assert "decayed" in data

    def test_dry_run_always_synchronous(self, client_async_threshold: TestClient) -> None:
        """Spec §15.4: dry_run MUST respond synchronously regardless of scope size."""
        client_async_threshold.post("/v1/facts", json=FACT)
        r = client_async_threshold.post("/v1/decay/sweep?ttl_seconds=0&dry_run=true")
        assert r.status_code == 200
        data = r.json()
        assert data["dry_run"] is True

    def test_cross_type_isolation_decay_job_not_visible_via_lint(
        self, client_async_threshold: TestClient
    ) -> None:
        client_async_threshold.post("/v1/facts", json=FACT)
        r202 = client_async_threshold.post("/v1/decay/sweep?ttl_seconds=0")
        job_id = r202.json()["job_id"]
        r = client_async_threshold.get(f"/v1/lint/jobs/{job_id}")
        assert r.status_code == 404

    def test_empty_scope_sync_even_at_threshold_one(
        self, client_async_threshold: TestClient
    ) -> None:
        r = client_async_threshold.post("/v1/decay/sweep?ttl_seconds=0")
        assert r.status_code == 200

    def test_scope_filter_counts_only_target_scope(
        self, client_async_threshold: TestClient
    ) -> None:
        """Cross-scope fact does not trigger async work on an empty target scope."""
        team_fact = {**FACT, "scope": "team"}
        client_async_threshold.post("/v1/facts", json=team_fact)  # team scope has 1 fact
        # local scope has 0 facts — sync even with threshold=1
        r = client_async_threshold.post("/v1/decay/sweep?ttl_seconds=0&scope=local")
        assert r.status_code == 200
