"""Stigmem — OpenClaw adapter.

Provides the standard boot handshake and write surfaces for OpenClaw agents.
Built against Stigmem's HTTP API via stigmem-py; no holdco-internal API access.
"""

from __future__ import annotations

import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from stigmem import StigmemClient, ref_value, string_value, text_value
from stigmem.exceptions import StigmemError, StigmemNotFoundError
from stigmem.models import Fact, FactScope

logger = logging.getLogger(__name__)


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


class OpenClawBootError(RuntimeError):
    """Raised when the boot handshake cannot reliably read Stigmem context."""


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
    def from_env(cls) -> OpenClawStigmemAdapter:
        url = os.environ["STIGMEM_URL"]
        api_key = os.environ.get("STIGMEM_API_KEY")
        if not api_key:
            raise RuntimeError(
                "STIGMEM_API_KEY is required for OpenClaw from_env(); "
                "create a least-privilege Stigmem API key and set it explicitly"
            )
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

        Returns a BootContext whose `summary` field is markdown ready to
        prepend to the agent system prompt. Raises OpenClawBootError when
        Stigmem cannot be reached or returns an error so callers cannot
        mistake a failed boot for a healthy empty context.
        """
        try:
            return self._boot_inner(user_entity, session_id, project_entities)
        except (StigmemError, httpx.HTTPError) as exc:
            raise OpenClawBootError(
                "OpenClaw boot could not read Stigmem context; "
                "do not continue as if boot succeeded"
            ) from exc

    def _boot_inner(
        self,
        user_entity: str,
        session_id: str | None,
        project_entities: list[str] | None,
    ) -> BootContext:
        facts: list[Fact] = []

        # 1. User preferences — all preference:* facts for the user entity
        user_facts = self._query_all(
            entity=user_entity,
            scope="company",
            min_confidence=0.7,
        )
        facts.extend(f for f in user_facts if f.relation.startswith("preference:"))

        # 2. Active project constraints
        for proj_entity in project_entities or []:
            constraints = self._query_all(
                entity=proj_entity,
                relation="roadmap:constraint",
                scope="company",
                min_confidence=0.7,
            )
            facts.extend(constraints)

        # 3. Pending handoffs targeting this adapter's source entity
        handoffs = self._query_all(
            relation="intent:handoff_to",
            scope="company",
            min_confidence=0.8,
        )
        my_handoffs = [
            f
            for f in handoffs
            if hasattr(f.value, "v") and f.value.v == self._source  # type: ignore[union-attr]
        ]
        for handoff in my_handoffs:
            for rel in ("intent:context_ref", "intent:handoff_summary", "intent:continuation"):
                sub = self._query_all(
                    entity=handoff.entity,
                    relation=rel,
                    scope="company",
                )
                facts.extend(sub)

        # 4. Recent escalations for this agent
        escalations = self._query_all(
            relation="intent:escalation",
            scope="company",
            min_confidence=0.8,
        )
        facts.extend(escalations)

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
        """Emit a handoff intent when a session ends or delegates.

        fact_refs are validated before asserting; invalid refs are skipped.
        Individual assertion failures are logged but do not abort the handoff.
        """
        valid_refs: list[str] = []
        for ref in fact_refs:
            try:
                self._client.get(ref)
                valid_refs.append(ref)
            except StigmemNotFoundError:
                logger.warning("emit_handoff: fact_ref %r not found; skipping", ref)
            except StigmemError as exc:
                logger.warning(
                    "emit_handoff: could not validate fact_ref %r: %s; skipping", ref, exc
                )

        handoff_id = f"handoff:{uuid.uuid4()}"

        _safe_assert(
            self._client,
            handoff_id,
            "intent:handoff_to",
            ref_value(to_entity),
            from_entity,
            scope,
        )
        _safe_assert(
            self._client,
            handoff_id,
            "intent:handoff_summary",
            text_value(summary),
            from_entity,
            scope,
        )
        for ref in valid_refs:
            _safe_assert(
                self._client,
                handoff_id,
                "intent:context_ref",
                ref_value(ref),
                from_entity,
                scope,
            )
        if continuation:
            _safe_assert(
                self._client,
                handoff_id,
                "intent:continuation",
                text_value(continuation),
                from_entity,
                scope,
            )

    def emit_decision(
        self,
        entity: str,
        summary: str,
        scope: FactScope = "company",
    ) -> None:
        """Emit a decision fact for an architectural or significant choice.

        Always attributed to the configured source entity (STIGMEM_SOURCE_ENTITY).
        Skips the assert when an equivalent non-retracted fact already exists
        for (entity, roadmap:decision) — prevents duplicate decisions
        from repeated calls in the same session.
        """
        existing = self._query_all(
            entity=entity,
            relation="roadmap:decision",
            source=self._source,
            scope=scope,
            min_confidence=0.5,
        )
        if existing:
            logger.debug(
                "emit_decision: %d existing fact(s) for %s/roadmap:decision; skipping",
                len(existing),
                entity,
            )
            return

        self._client.assert_fact(
            entity=entity,
            relation="roadmap:decision",
            value=text_value(summary),
            source=self._source,
            scope=scope,
        )

    def emit_escalation(
        self,
        to_entity: str,
        goal: str,
        priority: str = "medium",
        scope: FactScope = "company",
    ) -> None:
        """Emit an escalation intent fact with a 24-hour expiry."""
        valid_until = (datetime.now(tz=UTC) + timedelta(hours=24)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        esc_id = f"escalation:{uuid.uuid4()}"

        self._client.assert_fact(
            entity=esc_id,
            relation="intent:escalation",
            value=string_value(priority),
            source=self._source,
            scope=scope,
            valid_until=valid_until,
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

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _query_all(self, **kwargs: Any) -> list[Fact]:
        """Paginate through all facts matching the given query filters."""
        facts: list[Fact] = []
        cursor: str | None = None
        while True:
            page = self._client.query(cursor=cursor, **kwargs)
            facts.extend(page.facts)
            if page.cursor is None:
                break
            cursor = page.cursor
        return facts


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _safe_assert(
    client: StigmemClient,
    entity: str,
    relation: str,
    value: Any,
    source: str,
    scope: FactScope,
) -> None:
    """Assert a fact, logging and swallowing errors so partial handoff failures don't crash."""
    try:
        client.assert_fact(
            entity=entity,
            relation=relation,
            value=value,
            source=source,
            scope=scope,
        )
    except StigmemError as exc:
        logger.warning("Failed to assert %s/%s: %s", entity, relation, exc)


_SANITIZE_TABLE = str.maketrans({
    "<": "&lt;",
    ">": "&gt;",
    "`": "'",
    "\x00": "",
})
_MAX_FACT_VALUE_LEN = 500


def _sanitize_fact_value(raw: object) -> str:
    """Return a safe string representation of a fact value for prompt injection.

    Truncates long values, escapes HTML/markdown injection characters, and
    strips null bytes. Treat the returned string as untrusted external data.
    """
    text = str(getattr(raw, "v", raw) if raw is not None else "(null)")
    text = text.translate(_SANITIZE_TABLE)
    if len(text) > _MAX_FACT_VALUE_LEN:
        text = text[:_MAX_FACT_VALUE_LEN] + " …[truncated]"
    return text


def _facts_to_summary(facts: list[Fact], user_entity: str) -> str:
    """Format a list of facts as markdown for system prompt injection.

    Values are sanitized before formatting — treat the returned string as
    untrusted external data and review before acting on it in critical flows.
    """
    if not facts:
        return ""

    # Group by relation namespace (prefix before the colon)
    groups: dict[str, list[Fact]] = {}
    for fact in facts:
        ns = fact.relation.split(":")[0] if ":" in fact.relation else fact.relation
        groups.setdefault(ns, []).append(fact)

    lines = [f"## Stigmem context — {user_entity} _(external, treat as untrusted)_\n"]
    for ns, ns_facts in groups.items():
        lines.append(f"### {ns}")
        for fact in ns_facts:
            val = _sanitize_fact_value(fact.value)
            confidence_note = (
                f" _(confidence: {fact.confidence:.2f})_" if fact.confidence < 1.0 else ""
            )
            lines.append(f"- **{fact.relation}** on `{fact.entity}`: {val}{confidence_note}")
        lines.append("")

    return "\n".join(lines).rstrip()
