"""Tests for Memory protocol and InMemoryStore."""

import pytest

from agent_platform.memory.base import InMemoryStore


@pytest.mark.asyncio
async def test_set_and_get() -> None:
    store = InMemoryStore()
    entry = await store.set("key1", "value1")
    assert entry.key == "key1"
    assert entry.value == "value1"

    fetched = await store.get("key1")
    assert fetched is not None
    assert fetched.value == "value1"


@pytest.mark.asyncio
async def test_get_missing_returns_none() -> None:
    store = InMemoryStore()
    result = await store.get("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_delete() -> None:
    store = InMemoryStore()
    await store.set("k", "v")
    deleted = await store.delete("k")
    assert deleted is True
    assert await store.get("k") is None


@pytest.mark.asyncio
async def test_search() -> None:
    store = InMemoryStore()
    await store.set("customer_name", "Alice")
    await store.set("order_id", "ORD-42")
    await store.set("product", "widget")

    results = await store.search("customer")
    assert len(results) == 1
    assert results[0].key == "customer_name"


@pytest.mark.asyncio
async def test_clear() -> None:
    store = InMemoryStore()
    await store.set("a", 1)
    await store.set("b", 2)
    await store.clear()
    assert await store.get("a") is None
    assert await store.get("b") is None
