"""Tool protocol and @tool decorator."""

from __future__ import annotations

import functools
import inspect
from collections.abc import Awaitable, Callable
from typing import Any, ParamSpec, TypeVar, get_type_hints

from pydantic import BaseModel

P = ParamSpec("P")
R = TypeVar("R")


class ToolSchema(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any]


class Tool(BaseModel):
    """A callable tool that an agent can invoke."""

    name: str
    description: str
    parameters_schema: dict[str, Any]
    fn: Any  # Callable stored outside Pydantic validation

    model_config = {"arbitrary_types_allowed": True}

    async def call(self, **kwargs: Any) -> Any:
        result = self.fn(**kwargs)
        if inspect.isawaitable(result):
            return await result
        return result

    def to_schema(self) -> ToolSchema:
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters=self.parameters_schema,
        )


class ToolRegistry:
    """Registry for tools available to an agent."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def all(self) -> list[Tool]:
        return list(self._tools.values())

    def schemas(self) -> list[dict[str, Any]]:
        return [t.to_schema().model_dump() for t in self._tools.values()]


def _build_parameters_schema(fn: Callable[..., Any]) -> dict[str, Any]:
    hints = get_type_hints(fn)
    sig = inspect.signature(fn)
    properties: dict[str, Any] = {}
    required: list[str] = []

    for param_name, param in sig.parameters.items():
        if param_name == "self":
            continue
        annotation = hints.get(param_name, Any)
        prop: dict[str, Any] = {"type": "string"}  # simplified; extend as needed
        if annotation is int:
            prop = {"type": "integer"}
        elif annotation is float:
            prop = {"type": "number"}
        elif annotation is bool:
            prop = {"type": "boolean"}
        elif annotation is list:
            prop = {"type": "array"}
        properties[param_name] = prop
        if param.default is inspect.Parameter.empty:
            required.append(param_name)

    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


def tool(
    name: str | None = None,
    description: str = "",
) -> Callable[[Callable[P, R | Awaitable[R]]], Tool]:
    """Decorator that registers a function as a Tool."""

    def decorator(fn: Callable[P, R | Awaitable[R]]) -> Tool:
        tool_name = name or fn.__name__
        tool_description = description or (fn.__doc__ or "").strip()
        schema = _build_parameters_schema(fn)

        @functools.wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R | Awaitable[R]:
            return fn(*args, **kwargs)

        t = Tool(
            name=tool_name,
            description=tool_description,
            parameters_schema=schema,
            fn=wrapper,
        )
        return t

    return decorator
