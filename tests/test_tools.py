"""Tests for the @tool decorator and FunctionTool."""
import pytest
from agent_platform.tools import FunctionTool, tool
from agent_platform.types import ToolResult


@tool(description="Add two numbers")
async def add(a: int, b: int) -> int:
    return a + b


def test_tool_decorator_creates_function_tool() -> None:
    assert isinstance(add, FunctionTool)
    assert add.name == "add"
    assert add.description == "Add two numbers"
    assert "a" in add.parameters["properties"]
    assert "b" in add.parameters["properties"]
    assert add.parameters["required"] == ["a", "b"]


@pytest.mark.asyncio
async def test_tool_execute_success() -> None:
    result = await add.execute(a=2, b=3)
    assert result == ToolResult(success=True, data=5)


@pytest.mark.asyncio
async def test_tool_execute_error() -> None:
    @tool(description="Always fails")
    async def bad_tool() -> None:
        raise ValueError("oops")

    result = await bad_tool.execute()
    assert not result.success
    assert "oops" in (result.error or "")
