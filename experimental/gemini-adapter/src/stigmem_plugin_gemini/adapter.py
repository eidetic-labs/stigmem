"""Stigmem — Gemini-native adapter.

Provides Stigmem's tools in Google's ``FunctionDeclaration`` schema format so
they can be passed directly to the Gemini SDK.  The adapter is intentionally
dependency-light: it uses only ``stigmem-py`` and the standard library for the
dispatch logic.  Import ``google.generativeai`` only in host code that needs to
build a ``genai.Tool`` object.

Typical usage::

    from stigmem_plugin_gemini import StigmemGeminiAdapter

    adapter = StigmemGeminiAdapter.from_env()

    # 1. Get tool declarations to pass to the model
    tools = adapter.gemini_tools()   # list[dict] — Google FunctionDeclaration JSON

    # 2. Build a genai.Tool (optional — requires google-generativeai installed)
    import google.generativeai as genai
    genai_tool = genai.protos.Tool(
        function_declarations=[genai.protos.FunctionDeclaration(**t) for t in tools]
    )

    # 3. Run an agent loop
    history = adapter.run(system_prompt="You are a helpful agent.", user_message="...")
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from pydantic import TypeAdapter
from stigmem import StigmemClient
from stigmem.exceptions import StigmemError
from stigmem.models import FactValue

_VALUE_ADAPTER: TypeAdapter[FactValue] = TypeAdapter(FactValue)


def _coerce_value(v: Any) -> FactValue:
    """Coerce a plain dict to the appropriate FactValue typed model."""
    if isinstance(v, dict):
        return _VALUE_ADAPTER.validate_python(v)
    return v  # type: ignore[return-value]

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Google FunctionDeclaration schemas for all five Stigmem tools
# ---------------------------------------------------------------------------

#: ``list[dict]`` — serialisable Google ``FunctionDeclaration`` dicts.
#: Pass these directly to ``genai.protos.FunctionDeclaration(**t)`` or to
#: any Gemini-compatible API that accepts function declarations as plain JSON.
#:
#: Note: Gemini requires UPPER-CASE type strings (``"STRING"`` not ``"string"``).
STIGMEM_FUNCTION_DECLARATIONS: list[dict[str, Any]] = [
    {
        "name": "assert_fact",
        "description": (
            "Write a typed fact to the Stigmem knowledge node. "
            "Facts are immutable; to update assert a new fact for the same "
            "(entity, relation, scope). To retract, set confidence=0.0."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "entity": {
                    "type": "STRING",
                    "description": "Entity URI or opaque ID, e.g. 'user:alice'",
                },
                "relation": {
                    "type": "STRING",
                    "description": "Namespaced predicate, e.g. 'memory:role'",
                },
                "value": {
                    "type": "OBJECT",
                    "description": (
                        "Typed fact value. Must have a 'type' key "
                        "('string','text','number','boolean','datetime','ref','null') "
                        "and a 'v' key for non-null types."
                    ),
                    "properties": {
                        "type": {"type": "STRING"},
                        "v": {"type": "STRING"},
                    },
                    "required": ["type"],
                },
                "source": {
                    "type": "STRING",
                    "description": "Asserting agent/user URI, e.g. 'agent:cto'",
                },
                "confidence": {
                    "type": "NUMBER",
                    "description": "Confidence in [0.0, 1.0]. Default 1.0.",
                },
                "scope": {
                    "type": "STRING",
                    "description": (
                        "Visibility scope: local, team, company, public. Default company."
                    ),
                },
                "valid_until": {
                    "type": "STRING",
                    "description": "ISO 8601 expiry datetime. Omit for no expiry.",
                },
            },
            "required": ["entity", "relation", "value", "source"],
        },
    },
    {
        "name": "query_facts",
        "description": (
            "Query facts from the Stigmem node. All parameters are optional filters. "
            "Returns a page of matching facts plus a cursor for pagination."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "entity": {
                    "type": "STRING",
                    "description": "Filter by entity URI.",
                },
                "relation": {
                    "type": "STRING",
                    "description": "Filter by relation predicate.",
                },
                "scope": {
                    "type": "STRING",
                    "description": "Filter by scope: local, team, company, public.",
                },
                "source": {
                    "type": "STRING",
                    "description": "Filter by asserting agent/user URI.",
                },
                "min_confidence": {
                    "type": "NUMBER",
                    "description": "Minimum confidence threshold (0.0–1.0).",
                },
                "include_contradicted": {
                    "type": "BOOLEAN",
                    "description": "Include contradicted facts. Default false.",
                },
                "include_expired": {
                    "type": "BOOLEAN",
                    "description": "Include expired facts. Default false.",
                },
                "limit": {
                    "type": "INTEGER",
                    "description": "Max results per page. Default 50.",
                },
                "cursor": {
                    "type": "STRING",
                    "description": "Pagination cursor from a previous response.",
                },
            },
            "required": [],
        },
    },
    {
        "name": "resolve_contradiction",
        "description": (
            "Resolve a contradiction between two conflicting facts. "
            "Provide the conflict_id and either a winning_fact_id or a new_value."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "conflict_id": {
                    "type": "STRING",
                    "description": "The conflict ID returned by a previous query.",
                },
                "winning_fact_id": {
                    "type": "STRING",
                    "description": "ID of the fact to keep. Mutually exclusive with new_value.",
                },
                "resolution_note": {
                    "type": "STRING",
                    "description": "Human-readable explanation for the resolution.",
                },
                "new_value": {
                    "type": "OBJECT",
                    "description": "Assert a fresh value instead of picking a winner.",
                    "properties": {
                        "type": {"type": "STRING"},
                        "v": {"type": "STRING"},
                    },
                    "required": ["type"],
                },
            },
            "required": ["conflict_id"],
        },
    },
    {
        "name": "subscribe_scope",
        "description": (
            "Poll for recently asserted facts in a scope (single-shot cursor advance). "
            "Useful for feed-style consumption of new facts. Returns facts and next cursor."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "scope": {
                    "type": "STRING",
                    "description": "Scope to subscribe to: local, team, company, public.",
                },
                "cursor": {
                    "type": "STRING",
                    "description": "Opaque cursor from the previous call. Omit to start from now.",
                },
                "limit": {
                    "type": "INTEGER",
                    "description": "Max facts to return. Default 50.",
                },
            },
            "required": ["scope"],
        },
    },
    {
        "name": "lint_scope",
        "description": (
            "Run read-only health checks on a scope: detect contradictions, "
            "stale facts, orphaned refs, and broken entity links. "
            "Safe to call at any time — makes no writes."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "scope": {
                    "type": "STRING",
                    "description": "Scope to lint: local, team, company, public.",
                },
                "checks": {
                    "type": "ARRAY",
                    "description": (
                        "Subset of checks to run. Omit to run all. "
                        "Valid values: contradictions, stale, orphans, broken_refs."
                    ),
                    "items": {"type": "STRING"},
                },
                "entity": {
                    "type": "STRING",
                    "description": "Narrow lint to a specific entity URI.",
                },
                "relation": {
                    "type": "STRING",
                    "description": "Narrow lint to a specific relation predicate.",
                },
                "stale_lookahead_s": {
                    "type": "INTEGER",
                    "description": (
                        "Seconds ahead to consider a fact 'soon-to-expire'. Default 86400."
                    ),
                },
            },
            "required": ["scope"],
        },
    },
]


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class StigmemGeminiAdapter:
    """Stigmem adapter for Gemini agents.

    Provides two surfaces:

    1. ``gemini_tools()`` — returns the ``STIGMEM_FUNCTION_DECLARATIONS`` list.
       Pass these to the Gemini SDK when constructing a tool-enabled model call.

    2. ``dispatch(fn_name, fn_args)`` — executes a single Stigmem tool call
       (triggered by a Gemini ``FunctionCall`` part) and returns a JSON string
       to wrap in a ``FunctionResponse`` part.

    3. ``run(system_prompt, user_message)`` — thin agentic loop: sends one
       user message, executes any tool calls the model requests, and returns
       the final text response.  Requires ``google-generativeai`` installed.
    """

    def __init__(
        self,
        url: str,
        api_key: str | None = None,
        source_entity: str = "agent:gemini",
        model: str = "gemini-2.0-flash",
    ) -> None:
        self._client = StigmemClient(url=url, api_key=api_key)
        self._source = source_entity
        self._model = model

    @classmethod
    def from_env(cls) -> StigmemGeminiAdapter:
        return cls(
            url=os.environ["STIGMEM_URL"],
            api_key=os.environ.get("STIGMEM_API_KEY"),
            source_entity=os.environ.get("STIGMEM_SOURCE_ENTITY", "agent:gemini"),
            model=os.environ.get("STIGMEM_GEMINI_MODEL", "gemini-2.0-flash"),
        )

    # ------------------------------------------------------------------
    # Tool declarations
    # ------------------------------------------------------------------

    def gemini_tools(self) -> list[dict[str, Any]]:
        """Return the list of Google FunctionDeclaration dicts."""
        return STIGMEM_FUNCTION_DECLARATIONS

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def dispatch(self, fn_name: str, fn_args: dict[str, Any]) -> str:
        """Execute a Stigmem tool call and return the JSON result string.

        Call this from inside a Gemini agentic loop when the model returns
        a ``FunctionCall`` part::

            for part in response.candidates[0].content.parts:
                if part.function_call:
                    result_json = adapter.dispatch(
                        part.function_call.name,
                        dict(part.function_call.args),
                    )
                    # wrap result_json in a FunctionResponse part and continue
        """
        try:
            result = self._dispatch_inner(fn_name, fn_args)
        except StigmemError as exc:
            result = {"error": str(exc)}
        except Exception as exc:
            logger.warning("Unexpected error dispatching %s: %s", fn_name, exc)
            result = {"error": str(exc)}
        return json.dumps(result)

    def _dispatch_inner(self, fn_name: str, fn_args: dict[str, Any]) -> Any:
        if fn_name == "assert_fact":
            return self._client.assert_fact(
                entity=fn_args["entity"],
                relation=fn_args["relation"],
                value=_coerce_value(fn_args["value"]),
                source=fn_args.get("source", self._source),
                confidence=fn_args.get("confidence", 1.0),
                scope=fn_args.get("scope", "company"),
                valid_until=fn_args.get("valid_until"),
            ).model_dump()

        if fn_name == "query_facts":
            page = self._client.query(
                entity=fn_args.get("entity"),
                relation=fn_args.get("relation"),
                source=fn_args.get("source"),
                scope=fn_args.get("scope"),
                min_confidence=fn_args.get("min_confidence"),
                include_contradicted=fn_args.get("include_contradicted", False),
                include_expired=fn_args.get("include_expired", False),
                limit=fn_args.get("limit", 50),
                cursor=fn_args.get("cursor"),
            )
            return page.model_dump()

        if fn_name == "resolve_contradiction":
            raw_new_value = fn_args.get("new_value")
            result = self._client.resolve_conflict(
                conflict_id=fn_args["conflict_id"],
                winning_fact_id=fn_args.get("winning_fact_id"),
                resolution_note=fn_args.get("resolution_note", ""),
                new_value=_coerce_value(raw_new_value) if raw_new_value else None,
            )
            return result.model_dump()

        if fn_name == "subscribe_scope":
            page = self._client.query(
                scope=fn_args["scope"],
                cursor=fn_args.get("cursor"),
                limit=fn_args.get("limit", 50),
            )
            return {
                "facts": [f.model_dump() for f in page.facts],
                "cursor": page.cursor,
                "has_more": page.cursor is not None,
            }

        if fn_name == "lint_scope":
            result = self._client.lint(
                scope=fn_args["scope"],
                checks=fn_args.get("checks"),
                entity=fn_args.get("entity"),
                relation=fn_args.get("relation"),
                stale_lookahead_s=fn_args.get("stale_lookahead_s"),
            )
            return result.model_dump() if hasattr(result, "model_dump") else result

        raise ValueError(f"Unknown Stigmem tool: {fn_name}")

    # ------------------------------------------------------------------
    # Agentic loop (requires google-generativeai)
    # ------------------------------------------------------------------

    def run(
        self,
        system_prompt: str,
        user_message: str,
        *,
        max_rounds: int = 10,
    ) -> str:
        """Run a single-turn agentic loop with tool use.

        Requires ``google-generativeai`` installed::

            pip install google-generativeai

        Returns the final text response from the model.
        """
        try:
            import google.generativeai as genai  # type: ignore[import]
        except ImportError as exc:
            raise ImportError(
                "google-generativeai is required for StigmemGeminiAdapter.run(); "
                "install it with: pip install google-generativeai"
            ) from exc

        tool_obj = genai.protos.Tool(
            function_declarations=[
                genai.protos.FunctionDeclaration(**t)
                for t in self.gemini_tools()
            ]
        )
        model = genai.GenerativeModel(
            model_name=self._model,
            system_instruction=system_prompt,
            tools=[tool_obj],
        )
        chat = model.start_chat()
        response = chat.send_message(user_message)

        for _ in range(max_rounds):
            fn_calls = [
                p.function_call
                for p in response.candidates[0].content.parts
                if hasattr(p, "function_call") and p.function_call.name
            ]
            if not fn_calls:
                break

            fn_responses = []
            for fc in fn_calls:
                result_json = self.dispatch(fc.name, dict(fc.args))
                fn_responses.append(
                    genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=fc.name,
                            response={"result": json.loads(result_json)},
                        )
                    )
                )
            response = chat.send_message(fn_responses)

        # Extract final text from last response
        for part in response.candidates[0].content.parts:
            if hasattr(part, "text") and part.text:
                return part.text
        return ""
