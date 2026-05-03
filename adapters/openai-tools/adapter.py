"""Stigmem — OpenAI-compatible tool-use adapter.

Exposes Stigmem's tools in OpenAI's function-calling / tool-use format, which
is compatible with **LiteLLM**, **Ollama** (``/api/chat`` tool fields), and the
OpenAI Python SDK.  This lets OSS models served locally via Ollama/LiteLLM call
Stigmem tools without going through MCP.

Typical usage::

    from adapter import StigmemOpenAIToolsAdapter

    adapter = StigmemOpenAIToolsAdapter.from_env()

    # 1. Get the tools array to pass in the API call
    tools = adapter.tools()   # list[dict] in OpenAI tools format

    # 2. Dispatch a tool call returned by the model
    result_msg = adapter.dispatch(tool_call)   # → {"role": "tool", ...}

    # 3. Run a convenience agentic loop via LiteLLM (OSS or hosted models)
    response = adapter.run_litellm("ollama/mistral", system_prompt="...", user_message="...")
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

logger = logging.getLogger(__name__)

_VALUE_ADAPTER: TypeAdapter[FactValue] = TypeAdapter(FactValue)


def _coerce_value(v: Any) -> FactValue:
    """Coerce a plain dict to the appropriate FactValue typed model."""
    if isinstance(v, dict):
        return _VALUE_ADAPTER.validate_python(v)
    return v  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# OpenAI / LiteLLM tool schemas (JSON Schema, lower-case types)
# ---------------------------------------------------------------------------

#: ``list[dict]`` — OpenAI-format ``tools`` array.
#: Pass directly to any OpenAI-compatible ``chat.completions.create(tools=...)`` call.
STIGMEM_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "assert_fact",
            "description": (
                "Write a typed fact to the Stigmem knowledge node. "
                "Facts are immutable; to update assert a new fact for the same "
                "(entity, relation, scope). To retract, set confidence=0.0."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "entity": {
                        "type": "string",
                        "description": "Entity URI or opaque ID, e.g. 'user:alice'",
                    },
                    "relation": {
                        "type": "string",
                        "description": "Namespaced predicate, e.g. 'memory:role'",
                    },
                    "value": {
                        "type": "object",
                        "description": (
                            "Typed fact value. Must have a 'type' key "
                            "('string','text','number','boolean','datetime','ref','null') "
                            "and a 'v' key for non-null types."
                        ),
                        "properties": {
                            "type": {"type": "string"},
                            "v": {},
                        },
                        "required": ["type"],
                    },
                    "source": {
                        "type": "string",
                        "description": "Asserting agent/user URI, e.g. 'agent:cto'",
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Confidence in [0.0, 1.0]. Default 1.0.",
                    },
                    "scope": {
                        "type": "string",
                        "enum": ["local", "team", "company", "public"],
                        "description": "Visibility scope. Default company.",
                    },
                    "valid_until": {
                        "type": "string",
                        "description": "ISO 8601 expiry datetime. Omit for no expiry.",
                    },
                },
                "required": ["entity", "relation", "value", "source"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_facts",
            "description": (
                "Query facts from the Stigmem node. All parameters are optional filters. "
                "Returns a page of matching facts plus a cursor for pagination."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "entity": {"type": "string", "description": "Filter by entity URI."},
                    "relation": {"type": "string", "description": "Filter by relation predicate."},
                    "scope": {
                        "type": "string",
                        "enum": ["local", "team", "company", "public"],
                        "description": "Filter by scope.",
                    },
                    "source": {"type": "string", "description": "Filter by asserting agent URI."},
                    "min_confidence": {
                        "type": "number",
                        "description": "Minimum confidence threshold (0.0–1.0).",
                    },
                    "include_contradicted": {
                        "type": "boolean",
                        "description": "Include contradicted facts. Default false.",
                    },
                    "include_expired": {
                        "type": "boolean",
                        "description": "Include expired facts. Default false.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max results per page. Default 50.",
                    },
                    "cursor": {
                        "type": "string",
                        "description": "Pagination cursor from a previous response.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "resolve_contradiction",
            "description": (
                "Resolve a contradiction between two conflicting facts. "
                "Provide the conflict_id and either a winning_fact_id or a new_value."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "conflict_id": {
                        "type": "string",
                        "description": "The conflict ID returned by a previous query.",
                    },
                    "winning_fact_id": {
                        "type": "string",
                        "description": "ID of the fact to keep. Mutually exclusive with new_value.",
                    },
                    "resolution_note": {
                        "type": "string",
                        "description": "Human-readable explanation for the resolution.",
                    },
                    "new_value": {
                        "type": "object",
                        "description": "Assert a fresh value instead of picking a winner.",
                        "properties": {
                            "type": {"type": "string"},
                            "v": {},
                        },
                        "required": ["type"],
                    },
                },
                "required": ["conflict_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "subscribe_scope",
            "description": (
                "Poll for recently asserted facts in a scope (single-shot cursor advance). "
                "Returns facts and the next cursor for incremental consumption."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "scope": {
                        "type": "string",
                        "enum": ["local", "team", "company", "public"],
                        "description": "Scope to subscribe to.",
                    },
                    "cursor": {
                        "type": "string",
                        "description": "Opaque cursor from the previous call. Omit to start from now.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Max facts to return. Default 50.",
                    },
                },
                "required": ["scope"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "lint_scope",
            "description": (
                "Run read-only health checks on a scope: detect contradictions, "
                "stale facts, orphaned refs, and broken entity links. Makes no writes."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "scope": {
                        "type": "string",
                        "enum": ["local", "team", "company", "public"],
                        "description": "Scope to lint.",
                    },
                    "checks": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": (
                            "Subset of checks to run. Omit to run all. "
                            "Valid values: contradictions, stale, orphans, broken_refs."
                        ),
                    },
                    "entity": {
                        "type": "string",
                        "description": "Narrow lint to a specific entity URI.",
                    },
                    "relation": {
                        "type": "string",
                        "description": "Narrow lint to a specific relation predicate.",
                    },
                    "stale_lookahead_s": {
                        "type": "integer",
                        "description": "Seconds ahead to consider a fact soon-to-expire. Default 86400.",
                    },
                },
                "required": ["scope"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class StigmemOpenAIToolsAdapter:
    """Stigmem adapter for OpenAI-compatible tool-use (Ollama / LiteLLM / OpenAI).

    Provides four surfaces:

    1. **``tools()``** — returns ``STIGMEM_TOOLS``, a ``list[dict]`` ready to
       pass to any ``chat.completions.create(tools=...)`` endpoint.

    2. **``dispatch(tool_call)``** — executes a single tool call (as returned
       by the model) and returns an OpenAI-format tool-result message dict.

    3. **``run_litellm(model, system_prompt, user_message)``** — thin agentic
       loop via LiteLLM.  Requires ``litellm`` installed.  Works with any
       LiteLLM-supported model string, e.g. ``"ollama/mistral"``,
       ``"openai/gpt-4o-mini"``, ``"anthropic/claude-3-5-haiku-20241022"``.

    4. **``run_openai(model, system_prompt, user_message, base_url, api_key)``**
       — loop via the OpenAI Python SDK directly.  Use ``base_url`` to point at
       an Ollama server (``http://localhost:11434/v1``).
    """

    def __init__(
        self,
        url: str,
        api_key: str | None = None,
        source_entity: str = "agent:openai-tools",
    ) -> None:
        self._client = StigmemClient(url=url, api_key=api_key)
        self._source = source_entity

    @classmethod
    def from_env(cls) -> "StigmemOpenAIToolsAdapter":
        return cls(
            url=os.environ["STIGMEM_URL"],
            api_key=os.environ.get("STIGMEM_API_KEY"),
            source_entity=os.environ.get("STIGMEM_SOURCE_ENTITY", "agent:openai-tools"),
        )

    # ------------------------------------------------------------------
    # Tool declarations
    # ------------------------------------------------------------------

    def tools(self) -> list[dict[str, Any]]:
        """Return the OpenAI-format tools array."""
        return STIGMEM_TOOLS

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def dispatch(self, tool_call: Any) -> dict[str, Any]:
        """Execute a tool call and return an OpenAI tool-result message dict.

        ``tool_call`` is the object returned by the model — either an
        ``openai.types.chat.ChatCompletionMessageToolCall`` or any object /
        dict with ``id``, ``function.name``, and ``function.arguments``
        fields::

            for tc in response.choices[0].message.tool_calls or []:
                tool_msg = adapter.dispatch(tc)
                messages.append(tool_msg)
        """
        # Support both SDK objects and plain dicts
        if isinstance(tool_call, dict):
            call_id = tool_call.get("id", "")
            fn_name = tool_call.get("function", {}).get("name", "")
            fn_args_raw = tool_call.get("function", {}).get("arguments", "{}")
        else:
            call_id = tool_call.id
            fn = tool_call.function
            fn_name = fn.name
            fn_args_raw = fn.arguments

        fn_args = json.loads(fn_args_raw) if isinstance(fn_args_raw, str) else fn_args_raw

        try:
            result = self._dispatch_inner(fn_name, fn_args)
        except StigmemError as exc:
            result = {"error": str(exc)}
        except Exception as exc:
            logger.warning("Unexpected error dispatching %s: %s", fn_name, exc)
            result = {"error": str(exc)}

        return {
            "role": "tool",
            "tool_call_id": call_id,
            "content": json.dumps(result),
        }

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
    # LiteLLM agentic loop
    # ------------------------------------------------------------------

    def run_litellm(
        self,
        model: str,
        system_prompt: str,
        user_message: str,
        *,
        max_rounds: int = 10,
        **kwargs: Any,
    ) -> str:
        """Run an agentic loop via LiteLLM.

        Requires ``litellm`` installed::

            pip install litellm

        ``model`` is any LiteLLM model string, e.g.:

        - ``"ollama/mistral"`` — local Ollama server
        - ``"openai/gpt-4o-mini"`` — OpenAI
        - ``"anthropic/claude-3-5-haiku-20241022"`` — Anthropic

        Returns the final text response from the model.
        """
        try:
            import litellm  # type: ignore[import]
        except ImportError as exc:
            raise ImportError(
                "litellm is required for StigmemOpenAIToolsAdapter.run_litellm(); "
                "install it with: pip install litellm"
            ) from exc

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        for _ in range(max_rounds):
            response = litellm.completion(
                model=model,
                messages=messages,
                tools=self.tools(),
                **kwargs,
            )
            msg = response.choices[0].message
            messages.append(msg.model_dump() if hasattr(msg, "model_dump") else dict(msg))

            tool_calls = getattr(msg, "tool_calls", None) or []
            if not tool_calls:
                return msg.content or ""

            for tc in tool_calls:
                messages.append(self.dispatch(tc))

        return ""

    # ------------------------------------------------------------------
    # OpenAI SDK agentic loop
    # ------------------------------------------------------------------

    def run_openai(
        self,
        model: str,
        system_prompt: str,
        user_message: str,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
        max_rounds: int = 10,
        **kwargs: Any,
    ) -> str:
        """Run an agentic loop via the OpenAI Python SDK.

        To target a local Ollama server, set::

            base_url="http://localhost:11434/v1"
            api_key="ollama"   # Ollama ignores this but the SDK requires a value

        Requires ``openai`` installed::

            pip install openai

        Returns the final text response from the model.
        """
        try:
            from openai import OpenAI  # type: ignore[import]
        except ImportError as exc:
            raise ImportError(
                "openai is required for StigmemOpenAIToolsAdapter.run_openai(); "
                "install it with: pip install openai"
            ) from exc

        client_kwargs: dict[str, Any] = {}
        if base_url:
            client_kwargs["base_url"] = base_url
        if api_key:
            client_kwargs["api_key"] = api_key

        openai = OpenAI(**client_kwargs)
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]

        for _ in range(max_rounds):
            response = openai.chat.completions.create(
                model=model,
                messages=messages,
                tools=self.tools(),
                **kwargs,
            )
            msg = response.choices[0].message
            messages.append(msg.model_dump())

            tool_calls = msg.tool_calls or []
            if not tool_calls:
                return msg.content or ""

            for tc in tool_calls:
                messages.append(self.dispatch(tc))

        return ""
