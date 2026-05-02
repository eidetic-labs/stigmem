"""Tests for InMemoryMemory."""
import pytest
from agent_platform.memory import InMemoryMemory
from agent_platform.types import Message, Role


@pytest.mark.asyncio
async def test_add_and_search() -> None:
    mem = InMemoryMemory()
    await mem.add("The customer's order was shipped today", session_id="s1")
    await mem.add("Refund was processed yesterday", session_id="s1")

    results = await mem.search("order", session_id="s1")
    assert len(results) == 1
    assert "order" in results[0].content.lower()


@pytest.mark.asyncio
async def test_messages_round_trip() -> None:
    mem = InMemoryMemory()
    msg = Message(role=Role.USER, content="Hello")
    await mem.append_message("s1", msg)

    msgs = await mem.get_messages("s1")
    assert len(msgs) == 1
    assert msgs[0].content == "Hello"


@pytest.mark.asyncio
async def test_clear() -> None:
    mem = InMemoryMemory()
    await mem.add("something", session_id="s1")
    await mem.clear("s1")
    results = await mem.search("something", session_id="s1")
    assert results == []
