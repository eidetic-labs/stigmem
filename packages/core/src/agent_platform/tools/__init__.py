"""Tool protocol, @tool decorator, and tool registry."""
from __future__ import annotations

import asyncio
import inspect
from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable

from agent_platform.types import JsonSchema, ToolResult
from pydantic import TypeAdapter


@runtime_checkable
class Tool(Protocol):
    """Structural protocol — implement this to create a custom tool."""

    name: str
    description: str
    parameters: JsonSchema

    async def execute(self, **kwargs: Any) -> ToolResult: ...


class FunctionTool:
    """Wraps a plain async function as a Tool."""

    def __init__(
        self,
        fn: Callable[..., Any],
        description: str,
        name: str | None = None,
    ) -> None:
        self._fn = fn
        self.name = name or fn.__name__
        self.description = description
        self.parameters = _build_schema(fn)

    async def execute(self, **kwargs: Any) -> ToolResult:
        try:
            result = self._fn(**kwargs)
            if asyncio.iscoroutine(result):
                result = await result
            return ToolResult(success=True, data=result)
        except Exception as exc:
            return ToolResult(success=False, data=None, error=str(exc))

    def to_api_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.parameters,
        }


def tool(
    description: str,
    name: str | None = None,
) -> Callable[[Callable[..., Any]], FunctionTool]:
    """Decorator that turns an async function into a Tool."""

    def decorator(fn: Callable[..., Any]) -> FunctionTool:
        return FunctionTool(fn, description=description, name=name)

    return decorator


def _build_schema(fn: Callable[..., Any]) -> JsonSchema:
    sig = inspect.signature(fn)
    hints = {
        k: v
        for k, v in fn.__annotations__.items()
        if k != "return"
    }
    properties: dict[str, Any] = {}
    required: list[str] = []

    for param_name, param in sig.parameters.items():
        if param_name == "self":
            continue
        annotation = hints.get(param_name, Any)
        try:
            adapter = TypeAdapter(annotation)
            prop_schema = adapter.json_schema()
        except Exception:
            prop_schema = {"type": "string"}
        properties[param_name] = prop_schema
        if param.default is inspect.Parameter.empty:
            required.append(param_name)

    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }
