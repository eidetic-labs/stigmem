"""Audit-mapped OpenClaw adapter regression tests."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx

# conftest.py adds the adapter directory to sys.path
from adapter import (
    OpenClawBootError,
    OpenClawStigmemAdapter,
    OpenClawTargetError,
    OpenClawWriteError,
)

BASE = "http://test-stigmem"
SOURCE = "agent:openclaw"

_OPENCLAW_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT = _OPENCLAW_ROOT.parents[1]


def _fact(
    id: str = "fact-001",
    entity: str = "user:alice",
    relation: str = "preference:theme",
    source: str = SOURCE,
) -> dict:
    return {
        "id": id,
        "entity": entity,
        "relation": relation,
        "value": {"type": "string", "v": "dark"},
        "source": source,
        "timestamp": "2026-05-02T00:00:00Z",
        "confidence": 1.0,
        "scope": "company",
        "contradicted": False,
    }


def _page(facts: list[dict]) -> dict:
    return {"facts": facts, "total": len(facts), "cursor": None}


def _adapter() -> OpenClawStigmemAdapter:
    return OpenClawStigmemAdapter(
        url=BASE,
        api_key="sk-test",
        source_entity=SOURCE,
        allowed_handoff_targets=["agent:assistant", "agent:cto"],
    )


class TestC1H5StructuralChannelGap:
    """Audit findings C1/H5: presentation escaping is not the trust boundary."""

    def test_docs_keep_adapter_experimental_until_channel_separation_lands(self) -> None:
        docs = [
            _OPENCLAW_ROOT / "README.md",
            _OPENCLAW_ROOT / "skill" / "SKILL.md",
            _REPO_ROOT / "docs/docs/sdks/connectors/openclaw.md",
            _REPO_ROOT / "LIMITATIONS.md",
        ]

        for path in docs:
            text = path.read_text()
            assert "C1/H5" in text
            assert "github.com/Eidetic-Labs/stigmem/issues/357" in text

        limitations = (_REPO_ROOT / "LIMITATIONS.md").read_text()
        assert "outside\nthe supported production surface until #357 lands" in limitations


class TestC2BootFailure:
    """Audit finding C2: boot must fail closed on node/read errors."""

    @respx.mock
    def test_boot_raises_on_node_error(self) -> None:
        respx.get(f"{BASE}/v1/facts").mock(
            return_value=httpx.Response(503, json={"detail": "unavailable"})
        )

        with pytest.raises(OpenClawBootError, match="could not read Stigmem context"):
            _adapter().boot(user_entity="user:alice")


class TestC3AuthRequired:
    """Audit finding C3: environment construction requires an explicit API key."""

    def test_from_env_requires_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("STIGMEM_URL", BASE)
        monkeypatch.delenv("STIGMEM_API_KEY", raising=False)

        with pytest.raises(RuntimeError, match="STIGMEM_API_KEY is required"):
            OpenClawStigmemAdapter.from_env()


class TestC4HandoffTargetValidation:
    """Audit finding C4: handoff and escalation targets must be allowlisted."""

    @respx.mock
    def test_handoff_rejects_unallowlisted_target_before_writes(self) -> None:
        get_route = respx.get(f"{BASE}/v1/facts/fact-ok").mock(
            return_value=httpx.Response(200, json=_fact())
        )
        post_route = respx.post(f"{BASE}/v1/facts").mock(
            return_value=httpx.Response(201, json=_fact())
        )

        with pytest.raises(OpenClawTargetError, match="not in the configured allowlist"):
            _adapter().emit_handoff(
                from_entity=SOURCE,
                to_entity="agent:admin",
                summary="handoff",
                fact_refs=["fact-ok"],
            )

        assert get_route.call_count == 0
        assert post_route.call_count == 0


class TestH1OrphanHandoffs:
    """Audit finding H1: all-invalid handoff refs must not create orphan handoffs."""

    @respx.mock
    def test_handoff_refuses_all_invalid_non_empty_refs(self) -> None:
        respx.get(f"{BASE}/v1/facts/fact-missing").mock(
            return_value=httpx.Response(404, json={"detail": "not found"})
        )
        post_route = respx.post(f"{BASE}/v1/facts").mock(
            return_value=httpx.Response(201, json=_fact())
        )

        with pytest.raises(OpenClawWriteError, match="none of 1 fact_refs validated"):
            _adapter().emit_handoff(
                from_entity=SOURCE,
                to_entity="agent:assistant",
                summary="handoff",
                fact_refs=["fact-missing"],
            )

        assert post_route.call_count == 0


class TestH2PartialWrites:
    """Audit finding H2: partial multi-fact writes must be visible to callers."""

    @respx.mock
    def test_handoff_assert_failure_raises_typed_error(self) -> None:
        respx.get(f"{BASE}/v1/facts/fact-ok").mock(
            return_value=httpx.Response(200, json=_fact(id="fact-ok"))
        )
        responses = [
            httpx.Response(201, json=_fact()),
            httpx.Response(500, json={"detail": "boom"}),
        ]
        calls = {"n": 0}

        def next_response(request: httpx.Request) -> httpx.Response:
            response = responses[min(calls["n"], len(responses) - 1)]
            calls["n"] += 1
            return response

        respx.post(f"{BASE}/v1/facts").mock(side_effect=next_response)

        with pytest.raises(OpenClawWriteError, match="intent:handoff_summary") as exc:
            _adapter().emit_handoff(
                from_entity=SOURCE,
                to_entity="agent:assistant",
                summary="handoff",
                fact_refs=["fact-ok"],
            )

        assert exc.value.relation == "intent:handoff_summary"
        assert calls["n"] == 2


class TestH3DecisionDeduplication:
    """Audit finding H3: decisions are append-only, not broad-deduped."""

    @respx.mock
    def test_decision_write_does_not_query_or_skip_existing_decisions(self) -> None:
        query_route = respx.get(f"{BASE}/v1/facts").mock(
            return_value=httpx.Response(
                200, json=_page([_fact(id="decision-old", relation="roadmap:decision")])
            )
        )
        post_route = respx.post(f"{BASE}/v1/facts").mock(
            return_value=httpx.Response(201, json=_fact(relation="roadmap:decision"))
        )

        _adapter().emit_decision(
            entity="decision:architecture",
            summary="Record the new decision.",
        )

        assert query_route.call_count == 0
        assert post_route.call_count == 1


class TestH4Idempotency:
    """Audit finding H4: handoff retries can use deterministic idempotency keys."""

    @respx.mock
    def test_complete_handoff_retry_noops_by_idempotency_key(self) -> None:
        query_route = respx.get(f"{BASE}/v1/facts").mock(
            return_value=httpx.Response(
                200,
                json=_page(
                    [
                        _fact(entity="handoff:retry-1", relation="intent:handoff_to"),
                        _fact(entity="handoff:retry-1", relation="intent:handoff_summary"),
                    ]
                ),
            )
        )
        get_route = respx.get(f"{BASE}/v1/facts/fact-ok").mock(
            return_value=httpx.Response(200, json=_fact(id="fact-ok"))
        )
        post_route = respx.post(f"{BASE}/v1/facts").mock(
            return_value=httpx.Response(201, json=_fact())
        )

        result = _adapter().emit_handoff(
            from_entity=SOURCE,
            to_entity="agent:assistant",
            summary="handoff",
            fact_refs=["fact-ok"],
            idempotency_key="retry-1",
        )

        assert result.created is False
        assert query_route.call_count == 1
        assert get_route.call_count == 0
        assert post_route.call_count == 0
