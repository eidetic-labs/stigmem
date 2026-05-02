"""Tests for Tool protocol and @tool decorator."""

import pytest

from agent_platform.tools.base import Tool, ToolRegistry, tool


def test_tool_decorator_sync() -> None:
    @tool(description="Add two numbers")
    def add(x: int, y: int) -> int:
        return x + y

    assert isinstance(add, Tool)
    assert add.name == "add"
    assert add.description == "Add two numbers"


@pytest.mark.asyncio
async def test_tool_call_sync() -> None:
    @tool(description="Greet someone")
    def greet(name: str) -> str:
        """Greet someone."""
        return f"Hello, {name}!"

    result = await greet.call(name="World")
    assert result == "Hello, World!"


@pytest.mark.asyncio
async def test_tool_call_async() -> None:
    @tool(description="Async echo")
    async def echo(msg: str) -> str:
        return msg

    result = await echo.call(msg="ping")
    assert result == "ping"


def test_tool_registry() -> None:
    registry = ToolRegistry()

    @tool(description="Noop")
    def noop() -> None:
        pass

    registry.register(noop)
    assert registry.get("noop") is noop
    assert len(registry.all()) == 1


def test_tool_schema() -> None:
    @tool(name="my_tool", description="Does a thing")
    def my_func(value: str, count: int) -> str:
        return value * count

    schema = my_func.to_schema()
    assert schema.name == "my_tool"
    assert "value" in schema.parameters["properties"]
    assert "count" in schema.parameters["properties"]
    assert "value" in schema.parameters["required"]
