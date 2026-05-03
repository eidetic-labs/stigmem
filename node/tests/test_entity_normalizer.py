"""Tests for the strict entity URI normalizer — spec §2.6."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from stigmem_node.entity_normalizer import (
    NormalizationError,
    is_informal,
    normalize_entity_uri,
)


class TestNormalizeEntityUri:
    # Formal URIs — canonical already
    def test_formal_lowercase_passthrough(self) -> None:
        assert normalize_entity_uri("stigmem://company.acme/user/alice") == "stigmem://company.acme/user/alice"

    def test_formal_uppercase_id(self) -> None:
        assert normalize_entity_uri("stigmem://company.acme/issue/ISSUE-18") == "stigmem://company.acme/issue/issue-18"

    def test_formal_uppercase_authority(self) -> None:
        assert normalize_entity_uri("stigmem://Company.ACME/user/alice") == "stigmem://company.acme/user/alice"

    def test_formal_uppercase_type(self) -> None:
        assert normalize_entity_uri("stigmem://company.acme/User/alice") == "stigmem://company.acme/user/alice"

    def test_formal_all_uppercase(self) -> None:
        assert (
            normalize_entity_uri("stigmem://COMPANY.ACME/PROJECT/ISSUE-18")
            == "stigmem://company.acme/project/issue-18"
        )

    def test_formal_whitespace_in_id(self) -> None:
        assert (
            normalize_entity_uri("stigmem://company.acme/entity/my project")
            == "stigmem://company.acme/entity/my-project"
        )

    def test_formal_multiple_whitespace_in_id(self) -> None:
        assert (
            normalize_entity_uri("stigmem://company.acme/entity/foo  bar  baz")
            == "stigmem://company.acme/entity/foo-bar-baz"
        )

    # Informal URIs — lowercased in place, format preserved
    def test_informal_colon_lowercase(self) -> None:
        assert normalize_entity_uri("user:alice") == "user:alice"

    def test_informal_colon_uppercase(self) -> None:
        assert normalize_entity_uri("user:Alice") == "user:alice"

    def test_informal_issue_uppercase(self) -> None:
        assert normalize_entity_uri("issue:ISSUE-18") == "issue:issue-18"

    def test_informal_slash_uppercase(self) -> None:
        assert normalize_entity_uri("project/ISSUE-18") == "project/issue-18"

    def test_informal_slash_mixed(self) -> None:
        assert normalize_entity_uri("Project/MIXED-phase4") == "project/mixed-phase4"

    def test_informal_does_not_expand_to_formal(self) -> None:
        result = normalize_entity_uri("user:alice")
        assert not result.startswith("stigmem://")

    # Idempotency (required by spec)
    def test_idempotent_formal(self) -> None:
        uri = "stigmem://company.acme/issue/issue-42"
        assert normalize_entity_uri(normalize_entity_uri(uri)) == normalize_entity_uri(uri)

    def test_idempotent_informal(self) -> None:
        uri = "user:alice"
        assert normalize_entity_uri(normalize_entity_uri(uri)) == normalize_entity_uri(uri)

    def test_idempotent_uppercase_formal(self) -> None:
        uri = "stigmem://Company.ACME/Issue/ISSUE-42"
        assert normalize_entity_uri(normalize_entity_uri(uri)) == normalize_entity_uri(uri)

    # Error cases
    def test_empty_string_raises(self) -> None:
        with pytest.raises(NormalizationError):
            normalize_entity_uri("")

    def test_whitespace_only_raises(self) -> None:
        with pytest.raises(NormalizationError):
            normalize_entity_uri("   ")

    # Surrounding whitespace trimmed
    def test_leading_trailing_whitespace_trimmed(self) -> None:
        assert normalize_entity_uri("  user:alice  ") == "user:alice"

    def test_formal_leading_whitespace_trimmed(self) -> None:
        assert (
            normalize_entity_uri("  stigmem://company.acme/user/alice  ")
            == "stigmem://company.acme/user/alice"
        )


class TestIsInformal:
    def test_formal_is_not_informal(self) -> None:
        assert not is_informal("stigmem://company.acme/user/alice")

    def test_informal_colon(self) -> None:
        assert is_informal("user:alice")

    def test_informal_slash(self) -> None:
        assert is_informal("project/issue-18")


class TestNormalizationOnIngest:
    """Integration tests: normalizer applied on POST /v1/facts."""

    def test_uppercase_entity_normalized_on_store(self, client: TestClient) -> None:
        r = client.post(
            "/v1/facts",
            json={
                "entity": "stigmem://company.acme/issue/ISSUE-18",
                "relation": "roadmap:status",
                "value": {"type": "string", "v": "done"},
                "source": "stigmem://company.acme/agent/cto",
                "confidence": 1.0,
                "scope": "company",
            },
        )
        assert r.status_code == 201
        assert r.json()["entity"] == "stigmem://company.acme/issue/issue-18"

    def test_informal_entity_lowercased_on_store(self, client: TestClient) -> None:
        r = client.post(
            "/v1/facts",
            json={
                "entity": "issue:ISSUE-42",
                "relation": "roadmap:status",
                "value": {"type": "string", "v": "in_progress"},
                "source": "agent:assistant",
                "confidence": 1.0,
                "scope": "company",
            },
        )
        assert r.status_code == 201
        assert r.json()["entity"] == "issue:issue-42"

    def test_case_variants_detect_contradiction(self, client: TestClient) -> None:
        """ISSUE-18 and issue-18 normalize to the same entity — should trigger contradiction."""
        fact = {
            "entity": "stigmem://company.acme/issue/ISSUE-99",
            "relation": "roadmap:status",
            "value": {"type": "string", "v": "todo"},
            "source": "stigmem://company.acme/agent/cto",
            "confidence": 1.0,
            "scope": "company",
        }
        r1 = client.post("/v1/facts", json=fact)
        assert r1.status_code == 201

        fact2 = {**fact, "entity": "stigmem://company.acme/issue/issue-99", "value": {"type": "string", "v": "done"}}
        r2 = client.post("/v1/facts", json=fact2)
        assert r2.status_code == 201
        assert r2.json()["contradicted"] is True

    def test_query_normalizes_entity_param(self, client: TestClient) -> None:
        """Querying with uppercase entity finds the lowercase-normalized stored fact."""
        client.post(
            "/v1/facts",
            json={
                "entity": "stigmem://company.acme/user/alice",
                "relation": "memory:role",
                "value": {"type": "string", "v": "CEO"},
                "source": "stigmem://company.acme/agent/cto",
                "confidence": 1.0,
                "scope": "company",
            },
        )
        r = client.get(
            "/v1/facts",
            params={"entity": "stigmem://company.acme/user/ALICE"},
        )
        assert r.status_code == 200
        facts = r.json()["facts"]
        assert any(f["entity"] == "stigmem://company.acme/user/alice" for f in facts)

    def test_empty_entity_returns_400(self, client: TestClient) -> None:
        r = client.post(
            "/v1/facts",
            json={
                "entity": "   ",
                "relation": "memory:role",
                "value": {"type": "string", "v": "CEO"},
                "source": "agent:assistant",
                "confidence": 1.0,
                "scope": "company",
            },
        )
        assert r.status_code == 400
        assert "invalid_entity_uri" in r.json()["detail"]
