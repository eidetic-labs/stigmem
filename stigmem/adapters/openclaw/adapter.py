"""Stigmem — OpenClaw adapter.

Provides the standard boot handshake and write surfaces for OpenClaw agents.
Built against Stigmem's HTTP API via stigmem-py; no holdco-internal API access.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from stigmem import StigmemClient, string_value, text_value, ref_value
from stigmem.models import Fact, FactScope


@dataclass
class BootContext:
    """Result of the boot handshake.

    Inject `summary` into the agent's system prompt. `facts` are the raw
    fact objects for programmatic use.
    """
    facts: list[Fact] = field(default_factory=list)
    summary: str = ""

    def __bool__(self) -> bool:
        return bool(self.facts)


class OpenClawStigmemAdapter:
    """Stigmem adapter for OpenClaw agents.

    Usage::

        adapter = OpenClawStigmemAdapter.from_env()
        ctx = adapter.boot(user_entity="user:alice")
        # Inject ctx.summary into system prompt
    """

    def __init__(
        self,
        url: str,
        api_key: str | None,
        source_entity: str,
    ) -> None:
        self._client = StigmemClient(url=url, api_key=api_key)
        self._source = source_entity

    @classmethod
    def from_env(cls) -> "OpenClawStigmemAdapter":
        url = os.environ["STIGMEM_URL"]
        api_key = os.environ.get("STIGMEM_API_KEY")
        source = os.environ.get("STIGMEM_SOURCE_ENTITY", "agent:openclaw")
        return cls(url=url, api_key=api_key, source_entity=source)

    # ------------------------------------------------------------------
    # Boot handshake
    # ------------------------------------------------------------------

    def boot(
        self,
        user_entity: str,
        session_id: str | None = None,
        project_entities: list[str] | None = None,
    ) -> BootContext:
        """Pull user prefs, project constraints, and pending handoffs.

        Returns a BootContext with all fetched facts and a markdown summary
        ready to prepend to the agent system prompt.
        """
        facts: list[Fact] = []

        # 1. User preferences
        prefs = self._client.query(entity=user_entity, scope="company", min_confidence=0.7)
        facts.extend(prefs.facts)

        # 2. Active project constraints
        for proj_entity in (project_entities or []):
            constraints = self._client.query(
                entity=proj_entity,
                relation="roadmap:constraint",
                scope="company",
                min_confidence=0.7,
            )
            facts.extend(constraints.facts)

        # 3. Pending handoffs targeting this adapter's source entity
        handoffs = self._client.query(
            relation="intent:handoff_to",
            scope="company",
            min_confidence=0.8,
        )
        my_handoffs = [
            f for f in handoffs.facts
            if hasattr(f.value, "v") and f.value.v == self._source  # type: ignore[union-attr]
        ]
        for handoff in my_handoffs:
            # Pull the context_ref for each handoff
            ctx_refs = self._client.query(
                entity=handoff.entity,
                relation="intent:context_ref",
                scope="company",
            )
            facts.extend(ctx_refs.facts)

        # 4. Recent escalations for this agent
        escalations = self._client.query(
            relation="intent:escalation",
            scope="company",
            min_confidence=0.8,
            limit=10,
        )
        facts.extend(escalations.facts)

        summary = _facts_to_summary(facts, user_entity=user_entity)
        return BootContext(facts=facts, summary=summary)

    # ------------------------------------------------------------------
    # Write surfaces
    # ------------------------------------------------------------------

    def emit_handoff(
        self,
        from_entity: str,
        to_entity: str,
        summary: str,
        fact_refs: list[str],
        continuation: str | None = None,
        scope: FactScope = "company",
    ) -> None:
        """Emit a handoff intent when a session ends or delegates."""
        import uuid
        handoff_id = f"handoff:{uuid.uuid4()}"

        self._client.assert_fact(
            entity=handoff_id,
            relation="intent:handoff_to",
            value=ref_value(to_entity),
            source=from_entity,
            scope=scope,
        )
        self._client.assert_fact(
            entity=handoff_id,
            relation="intent:handoff_summary",
            value=text_value(summary),
            source=from_entity,
            scope=scope,
        )
        for ref in fact_refs:
            self._client.assert_fact(
                entity=handoff_id,
                relation="intent:context_ref",
                value=ref_value(ref),
                source=from_entity,
                scope=scope,
            )
        if continuation:
            self._client.assert_fact(
                entity=handoff_id,
                relation="intent:continuation",
                value=text_value(continuation),
                source=from_entity,
                scope=scope,
            )

    def emit_decision(
        self,
        entity: str,
        summary: str,
        source: str | None = None,
        scope: FactScope = "company",
    ) -> None:
        """Emit a decision fact for an architectural or significant choice."""
        self._client.assert_fact(
            entity=entity,
            relation="roadmap:decision",
            value=text_value(summary),
            source=source or self._source,
            scope=scope,
        )

    def emit_escalation(
        self,
        to_entity: str,
        goal: str,
        priority: str = "medium",
        scope: FactScope = "company",
    ) -> None:
        """Emit an escalation intent fact."""
        import uuid
        esc_id = f"escalation:{uuid.uuid4()}"

        self._client.assert_fact(
            entity=esc_id,
            relation="intent:escalation",
            value=string_value(priority),
            source=self._source,
            scope=scope,
        )
        self._client.assert_fact(
            entity=esc_id,
            relation="intent:escalate_to",
            value=ref_value(to_entity),
            source=self._source,
            scope=scope,
        )
        self._client.assert_fact(
            entity=esc_id,
            relation="intent:goal",
            value=text_value(goal),
            source=self._source,
            scope=scope,
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _facts_to_summary(facts: list[Fact], user_entity: str) -> str:
    if not facts:
        return ""
    lines = [f"## Stigmem context for {user_entity}\n"]
    for fact in facts:
        value_str = getattr(fact.value, "v", "(null)") if hasattr(fact.value, "v") else "(null)"
        lines.append(f"- **{fact.relation}** on `{fact.entity}`: {value_str} (confidence={fact.confidence})")
    return "\n".join(lines)
