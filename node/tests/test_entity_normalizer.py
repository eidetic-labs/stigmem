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
        assert normalize_entity_uri("stigmem://company.example/user/alice") == "stigmem://company.example/user/alice"

    def test_formal_uppercase_id(self) -> None:
        assert normalize_entity_uri("stigmem://company.example/issue/EG-18") == "stigmem://company.example/issue/eg-18"

    def test_formal_uppercase_authority(self) -> None:
        assert normalize_entity_uri("stigmem://Company.EXAMPLE/user/alice") == "stigmem://company.example/user/alice"

    def test_formal_uppercase_type(self) -> None:
        assert normalize_entity_uri("stigmem://company.example/User/alice") == "stigmem://company.example/user/alice"

    def test_formal_all_uppercase(self) -> None:
        assert (
            normalize_entity_uri("stigmem://COMPANY.EXAMPLE/PROJECT/EG-18")
            == "stigmem://company.example/project/eg-18"
        )

    def test_formal_whitespace_in_id(self) -> None:
        assert (
            normalize_entity_uri("stigmem://company.example/entity/my project")
            == "stigmem://company.example/entity/my-project"
        )

    def test_formal_multiple_whitespace_in_id(self) -> None:
        assert (
            normalize_entity_uri("stigmem://company.example/entity/foo  bar  baz")
            == "stigmem://company.example/entity/foo-bar-baz"
        )

    # Informal URIs — lowercased in place, format preserved
    def test_informal_colon_lowercase(self) -> None:
        assert normalize_entity_uri("user:alice") == "user:alice"

    def test_informal_colon_uppercase(self) -> None:
        assert normalize_entity_uri("user:Alice") == "user:alice"

    def test_informal_issue_uppercase(self) -> None:
        assert normalize_entity_uri("issue:EG-18") == "issue:eg-18"

    def test_informal_slash_uppercase(self) -> None:
        assert normalize_entity_uri("project/EG-18") == "project/eg-18"

    def test_informal_slash_mixed(self) -> None:
        assert normalize_entity_uri("Project/MIXED-phase4") == "project/mixed-phase4"

    def test_informal_does_not_expand_to_formal(self) -> None:
        result = normalize_entity_uri("user:alice")
        assert not result.startswith("stigmem://")

    # Idempotency (required by spec)
    def test_idempotent_formal(self) -> None:
        uri = "stigmem://company.example/issue/eg-42"
        assert normalize_entity_uri(normalize_entity_uri(uri)) == normalize_entity_uri(uri)

    def test_idempotent_informal(self) -> None:
        uri = "user:alice"
        assert normalize_entity_uri(normalize_entity_uri(uri)) == normalize_entity_uri(uri)

    def test_idempotent_uppercase_formal(self) -> None:
        uri = "stigmem://Company.EXAMPLE/Issue/EG-42"
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
            normalize_entity_uri("  stigmem://company.example/user/alice  ")
            == "stigmem://company.example/user/alice"
        )


class TestIsInformal:
    def test_formal_is_not_informal(self) -> None:
        assert not is_informal("stigmem://company.example/user/alice")

    def test_informal_colon(self) -> None:
        assert is_informal("user:alice")

    def test_informal_slash(self) -> None:
        assert is_informal("project/eg-18")


class TestNormalizationOnIngest:
    """Integration tests: normalizer applied on POST /v1/facts."""

    def test_uppercase_entity_normalized_on_store(self, client: TestClient) -> None:
        r = client.post(
            "/v1/facts",
            json={
                "entity": "stigmem://company.example/issue/EG-18",
                "relation": "roadmap:status",
                "value": {"type": "string", "v": "done"},
                "source": "stigmem://company.example/agent/cto",
                "confidence": 1.0,
                "scope": "company",
            },
        )
        assert r.status_code == 201
        assert r.json()["entity"] == "stigmem://company.example/issue/eg-18"

    def test_informal_entity_lowercased_on_store(self, client: TestClient) -> None:
        r = client.post(
            "/v1/facts",
            json={
                "entity": "issue:EG-42",
                "relation": "roadmap:status",
                "value": {"type": "string", "v": "in_progress"},
                "source": "agent:assistant",
                "confidence": 1.0,
                "scope": "company",
            },
        )
        assert r.status_code == 201
        assert r.json()["entity"] == "issue:eg-42"

    def test_case_variants_detect_contradiction(self, client: TestClient) -> None:
        """EG-18 and eg-18 normalize to the same entity — should trigger contradiction."""
        fact = {
            "entity": "stigmem://company.example/issue/EG-99",
            "relation": "roadmap:status",
            "value": {"type": "string", "v": "todo"},
            "source": "stigmem://company.example/agent/cto",
            "confidence": 1.0,
            "scope": "company",
        }
        r1 = client.post("/v1/facts", json=fact)
        assert r1.status_code == 201

        fact2 = {**fact, "entity": "stigmem://company.example/issue/eg-99", "value": {"type": "string", "v": "done"}}
        r2 = client.post("/v1/facts", json=fact2)
        assert r2.status_code == 201
        assert r2.json()["contradicted"] is True

    def test_query_normalizes_entity_param(self, client: TestClient) -> None:
        """Querying with uppercase entity finds the lowercase-normalized stored fact."""
        client.post(
            "/v1/facts",
            json={
                "entity": "stigmem://company.example/user/alice",
                "relation": "memory:role",
                "value": {"type": "string", "v": "CEO"},
                "source": "stigmem://company.example/agent/cto",
                "confidence": 1.0,
                "scope": "company",
            },
        )
        r = client.get(
            "/v1/facts",
            params={"entity": "stigmem://company.example/user/ALICE"},
        )
        assert r.status_code == 200
        facts = r.json()["facts"]
        assert any(f["entity"] == "stigmem://company.example/user/alice" for f in facts)

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
