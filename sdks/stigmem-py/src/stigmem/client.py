"""Stigmem Python client SDK — spec v0.4/v0.5."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator, Callable
from typing import Any

import httpx

from .exceptions import (
    StigmemAuthError,
    StigmemConflictError,
    StigmemHTTPError,
    StigmemNotFoundError,
)
from .models import (
    AssertRequest,
    ConflictPage,
    ConflictResolution,
    Fact,
    FactPage,
    FactScope,
    FactValue,
    MemoryCard,
    NodeInfo,
    Peer,
    PeerPage,
    RecallRequest,
    RecallResponse,
    RecallWeights,
    ResolveRequest,
)

logger = logging.getLogger("stigmem")
SESSION_HEADER = "Stigmem-Session"
VERIFY_HEADER = "Stigmem-Verify"


def _recall_headers(session_id: str | None, verify_full: bool = False) -> dict[str, str] | None:
    headers = _session_headers(session_id) or {}
    if verify_full:
        headers[VERIFY_HEADER] = "full"
    return headers or None


def _session_headers(session_id: str | None) -> dict[str, str] | None:
    if session_id is None:
        return None
    normalized = session_id.strip()
    if not normalized:
        return None
    return {SESSION_HEADER: normalized}


def _raise_for_status(resp: httpx.Response) -> None:
    if resp.is_success:
        return
    try:
        detail = resp.json().get("detail", resp.text)
    except ValueError:
        detail = resp.text
    if resp.status_code in (401, 403):
        raise StigmemAuthError(resp.status_code, detail)
    if resp.status_code == 404:
        raise StigmemNotFoundError(resp.status_code, detail)
    if resp.status_code == 409:
        raise StigmemConflictError(resp.status_code, detail)
    raise StigmemHTTPError(resp.status_code, detail)


class StigmemClient:
    """Synchronous Stigmem client.

    Usage::

        client = StigmemClient(url="http://localhost:8765", api_key="sk-...")
        fact = client.assert_fact(
            entity="user:alice",
            relation="memory:role",
            value=string_value("CEO"),
            source="agent:cto",
        )
    """

    def __init__(
        self,
        url: str,
        api_key: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._url = url.rstrip("/")
        headers: dict[str, str] = {"Accept": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        self._http = httpx.Client(base_url=self._url, headers=headers, timeout=timeout)

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> StigmemClient:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Node / metadata
    # ------------------------------------------------------------------

    def node_info(self) -> NodeInfo:
        resp = self._http.get("/.well-known/stigmem")
        _raise_for_status(resp)
        return NodeInfo.model_validate(resp.json())

    # ------------------------------------------------------------------
    # Facts
    # ------------------------------------------------------------------

    def assert_fact(
        self,
        entity: str,
        relation: str,
        value: FactValue,
        source: str,
        *,
        confidence: float = 1.0,
        scope: FactScope = "company",
        valid_until: str | None = None,
        write_mode: str = "assert",
        derived_from: list[dict[str, Any]] | None = None,
        session_id: str | None = None,
    ) -> Fact:
        req = AssertRequest(
            entity=entity,
            relation=relation,
            value=value,
            source=source,
            confidence=confidence,
            scope=scope,
            valid_until=valid_until,
            write_mode=write_mode,
            derived_from=derived_from or [],
        )
        body = req.model_dump(exclude_none=True)
        body["value"] = value.model_dump()
        resp = self._http.post("/v1/facts", json=body, headers=_session_headers(session_id))
        _raise_for_status(resp)
        return Fact.model_validate(resp.json())

    def retract(
        self,
        entity: str,
        relation: str,
        scope: FactScope,
        source: str,
        *,
        value: FactValue | None = None,
    ) -> Fact:
        """Assert a retraction (confidence=0.0) for the given triple."""
        from .models import string_value as _sv

        retract_value = value if value is not None else _sv("retracted")
        return self.assert_fact(
            entity=entity,
            relation=relation,
            value=retract_value,
            source=source,
            confidence=0.0,
            scope=scope,
        )

    def get(self, fact_id: str, *, session_id: str | None = None) -> Fact:
        resp = self._http.get(f"/v1/facts/{fact_id}", headers=_session_headers(session_id))
        _raise_for_status(resp)
        return Fact.model_validate(resp.json())

    def query(
        self,
        *,
        entity: str | None = None,
        relation: str | None = None,
        source: str | None = None,
        scope: FactScope | None = None,
        min_confidence: float | None = None,
        include_contradicted: bool = False,
        include_expired: bool = False,
        cursor: str | None = None,
        limit: int = 50,
        after: str | None = None,
        session_id: str | None = None,
    ) -> FactPage:
        params: dict[str, Any] = {"limit": limit}
        if entity:
            params["entity"] = entity
        if relation:
            params["relation"] = relation
        if source:
            params["source"] = source
        if scope:
            params["scope"] = scope
        if min_confidence is not None:
            params["min_confidence"] = min_confidence
        if include_contradicted:
            params["include_contradicted"] = "true"
        if include_expired:
            params["include_expired"] = "true"
        if cursor:
            params["cursor"] = cursor
        if after:
            params["after"] = after
        resp = self._http.get("/v1/facts", params=params, headers=_session_headers(session_id))
        _raise_for_status(resp)
        return FactPage.model_validate(resp.json())

    # ------------------------------------------------------------------
    # Conflicts
    # ------------------------------------------------------------------

    def list_conflicts(
        self,
        *,
        status: str | None = "unresolved",
        cursor: str | None = None,
        limit: int = 50,
    ) -> ConflictPage:
        params: dict[str, Any] = {"limit": limit}
        if status:
            params["status"] = status
        if cursor:
            params["cursor"] = cursor
        resp = self._http.get("/v1/conflicts", params=params)
        _raise_for_status(resp)
        return ConflictPage.model_validate(resp.json())

    def resolve_conflict(
        self,
        conflict_id: str,
        *,
        winning_fact_id: str | None = None,
        resolution_note: str = "",
        new_value: FactValue | None = None,
    ) -> ConflictResolution:
        req = ResolveRequest(
            winning_fact_id=winning_fact_id,
            resolution_note=resolution_note,
            new_value=new_value,
        )
        resp = self._http.post(f"/v1/conflicts/{conflict_id}/resolve", json=req.model_dump_api())
        _raise_for_status(resp)
        return ConflictResolution.model_validate(resp.json())

    # ------------------------------------------------------------------
    # Federation
    # ------------------------------------------------------------------

    def federation_status(self) -> list[Peer]:
        resp = self._http.get("/v1/federation/peers")
        _raise_for_status(resp)
        return PeerPage.model_validate(resp.json()).peers

    # ------------------------------------------------------------------
    # Subscribe (polling)
    # ------------------------------------------------------------------

    def subscribe_scope(
        self,
        scope: FactScope,
        callback: Callable[[list[Fact]], None],
        *,
        interval_s: float = 30.0,
        stop_event: asyncio.Event | None = None,
    ) -> None:
        """Poll for new facts in *scope* and call *callback* with each batch.

        Blocking — runs until *stop_event* is set or KeyboardInterrupt.
        For async use, see AsyncStigmemClient.subscribe_scope().
        """
        import time

        cursor: str | None = None
        while True:
            if stop_event and stop_event.is_set():
                break
            page = self.query(scope=scope, cursor=cursor, limit=100)
            if page.facts:
                callback(page.facts)
            cursor = page.cursor
            time.sleep(interval_s)

    # ------------------------------------------------------------------
    # Recall (Phase 9 — spec §20)
    # ------------------------------------------------------------------

    def recall(
        self,
        query: str,
        *,
        scope: FactScope = "local",
        token_budget: int = 4000,
        depth: int = 2,
        weights: RecallWeights | None = None,
        min_confidence: float = 0.1,
        include_neighbors: bool = True,
        limit: int = 100,
        legacy_format: bool = False,
        session_id: str | None = None,
        verify_full: bool = False,
    ) -> RecallResponse:
        """Hybrid recall — return the most salient facts for *query* within *token_budget*.

        Combines lexical (BM25/FTS5), dense-vector, and graph-traversal signals.

        Args:
            query: Natural-language or keyword query.
            scope: Fact scope to search within.
            token_budget: Maximum token budget for the response.
            depth: Graph traversal depth (1–3).
            weights: Signal weights; defaults applied server-side when None.
            min_confidence: Minimum fact confidence to include.
            include_neighbors: Whether to expand via graph traversal.
            limit: Maximum candidate facts before token-budget packing.
            legacy_format: Request the temporary pre-channel response shape.
            verify_full: Request full server-side integrity proof metadata.

        Returns:
            RecallResponse with scored + packed facts and score breakdowns.
        """
        req = RecallRequest(
            query=query,
            scope=scope,
            token_budget=token_budget,
            depth=depth,
            weights=weights or RecallWeights(),
            min_confidence=min_confidence,
            include_neighbors=include_neighbors,
            limit=limit,
        )
        params = {"legacy_format": "true"} if legacy_format else None
        resp = self._http.post(
            "/v1/recall",
            json=req.model_dump(),
            params=params,
            headers=_recall_headers(session_id, verify_full),
        )
        _raise_for_status(resp)
        return RecallResponse.model_validate(resp.json())

    # ------------------------------------------------------------------
    # Memory cards (Phase 9 — spec §20)
    # ------------------------------------------------------------------

    def get_card(
        self,
        entity_uri: str,
        *,
        scope: FactScope = "local",
        refresh: bool = False,
    ) -> MemoryCard:
        """Fetch the synthesized memory card for *entity_uri*.

        Args:
            entity_uri: The entity to fetch the card for.
            scope: Fact scope the card was materialised from.
            refresh: Force a server-side refresh even if the card is fresh.

        Returns:
            MemoryCard with summary, contributing fact hashes, and confidence.

        Raises:
            StigmemNotFoundError: When the entity has no live facts.
        """
        params: dict[str, Any] = {"scope": scope}
        if refresh:
            params["refresh"] = "true"
        resp = self._http.get(f"/v1/cards/{entity_uri}", params=params)
        _raise_for_status(resp)
        return MemoryCard.model_validate(resp.json())


class AsyncStigmemClient:
    """Async Stigmem client (httpx.AsyncClient)."""

    def __init__(
        self,
        url: str,
        api_key: str | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._url = url.rstrip("/")
        headers: dict[str, str] = {"Accept": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        self._http = httpx.AsyncClient(base_url=self._url, headers=headers, timeout=timeout)

    async def aclose(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> AsyncStigmemClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.aclose()

    async def node_info(self) -> NodeInfo:
        resp = await self._http.get("/.well-known/stigmem")
        _raise_for_status(resp)
        return NodeInfo.model_validate(resp.json())

    async def assert_fact(
        self,
        entity: str,
        relation: str,
        value: FactValue,
        source: str,
        *,
        confidence: float = 1.0,
        scope: FactScope = "company",
        valid_until: str | None = None,
        write_mode: str = "assert",
        derived_from: list[dict[str, Any]] | None = None,
        session_id: str | None = None,
    ) -> Fact:
        req = AssertRequest(
            entity=entity,
            relation=relation,
            value=value,
            source=source,
            confidence=confidence,
            scope=scope,
            valid_until=valid_until,
            write_mode=write_mode,
            derived_from=derived_from or [],
        )
        body = req.model_dump(exclude_none=True)
        body["value"] = value.model_dump()
        resp = await self._http.post(
            "/v1/facts", json=body, headers=_session_headers(session_id)
        )
        _raise_for_status(resp)
        return Fact.model_validate(resp.json())

    async def retract(
        self,
        entity: str,
        relation: str,
        scope: FactScope,
        source: str,
        *,
        value: FactValue | None = None,
    ) -> Fact:
        from .models import string_value as _sv

        retract_value = value if value is not None else _sv("retracted")
        return await self.assert_fact(
            entity=entity,
            relation=relation,
            value=retract_value,
            source=source,
            confidence=0.0,
            scope=scope,
        )

    async def get(self, fact_id: str, *, session_id: str | None = None) -> Fact:
        resp = await self._http.get(
            f"/v1/facts/{fact_id}", headers=_session_headers(session_id)
        )
        _raise_for_status(resp)
        return Fact.model_validate(resp.json())

    async def query(
        self,
        *,
        entity: str | None = None,
        relation: str | None = None,
        source: str | None = None,
        scope: FactScope | None = None,
        min_confidence: float | None = None,
        include_contradicted: bool = False,
        include_expired: bool = False,
        cursor: str | None = None,
        limit: int = 50,
        after: str | None = None,
        session_id: str | None = None,
    ) -> FactPage:
        params: dict[str, Any] = {"limit": limit}
        if entity:
            params["entity"] = entity
        if relation:
            params["relation"] = relation
        if source:
            params["source"] = source
        if scope:
            params["scope"] = scope
        if min_confidence is not None:
            params["min_confidence"] = min_confidence
        if include_contradicted:
            params["include_contradicted"] = "true"
        if include_expired:
            params["include_expired"] = "true"
        if cursor:
            params["cursor"] = cursor
        if after:
            params["after"] = after
        resp = await self._http.get(
            "/v1/facts", params=params, headers=_session_headers(session_id)
        )
        _raise_for_status(resp)
        return FactPage.model_validate(resp.json())

    async def list_conflicts(
        self,
        *,
        status: str | None = "unresolved",
        cursor: str | None = None,
        limit: int = 50,
    ) -> ConflictPage:
        params: dict[str, Any] = {"limit": limit}
        if status:
            params["status"] = status
        if cursor:
            params["cursor"] = cursor
        resp = await self._http.get("/v1/conflicts", params=params)
        _raise_for_status(resp)
        return ConflictPage.model_validate(resp.json())

    async def resolve_conflict(
        self,
        conflict_id: str,
        *,
        winning_fact_id: str | None = None,
        resolution_note: str = "",
        new_value: FactValue | None = None,
    ) -> ConflictResolution:
        req = ResolveRequest(
            winning_fact_id=winning_fact_id,
            resolution_note=resolution_note,
            new_value=new_value,
        )
        resp = await self._http.post(
            f"/v1/conflicts/{conflict_id}/resolve",
            json=req.model_dump_api(),
        )
        _raise_for_status(resp)
        return ConflictResolution.model_validate(resp.json())

    async def federation_status(self) -> list[Peer]:
        resp = await self._http.get("/v1/federation/peers")
        _raise_for_status(resp)
        return PeerPage.model_validate(resp.json()).peers

    async def subscribe_scope(
        self,
        scope: FactScope,
        callback: Callable[[list[Fact]], None],
        *,
        interval_s: float = 30.0,
        stop_event: asyncio.Event | None = None,
    ) -> AsyncGenerator[list[Fact], None]:
        """Async generator that yields batches of new facts in *scope*."""
        cursor: str | None = None
        while True:
            if stop_event and stop_event.is_set():
                return
            page = await self.query(scope=scope, cursor=cursor, limit=100)
            if page.facts:
                callback(page.facts)
                yield page.facts
            cursor = page.cursor
            await asyncio.sleep(interval_s)

    # ------------------------------------------------------------------
    # Recall (Phase 9 — spec §20)
    # ------------------------------------------------------------------

    async def recall(
        self,
        query: str,
        *,
        scope: FactScope = "local",
        token_budget: int = 4000,
        depth: int = 2,
        weights: RecallWeights | None = None,
        min_confidence: float = 0.1,
        include_neighbors: bool = True,
        limit: int = 100,
        legacy_format: bool = False,
        session_id: str | None = None,
        verify_full: bool = False,
    ) -> RecallResponse:
        """Async hybrid recall — return the most salient facts for *query* within *token_budget*."""
        req = RecallRequest(
            query=query,
            scope=scope,
            token_budget=token_budget,
            depth=depth,
            weights=weights or RecallWeights(),
            min_confidence=min_confidence,
            include_neighbors=include_neighbors,
            limit=limit,
        )
        params = {"legacy_format": "true"} if legacy_format else None
        resp = await self._http.post(
            "/v1/recall",
            json=req.model_dump(),
            params=params,
            headers=_recall_headers(session_id, verify_full),
        )
        _raise_for_status(resp)
        return RecallResponse.model_validate(resp.json())

    # ------------------------------------------------------------------
    # Memory cards (Phase 9 — spec §20)
    # ------------------------------------------------------------------

    async def get_card(
        self,
        entity_uri: str,
        *,
        scope: FactScope = "local",
        refresh: bool = False,
    ) -> MemoryCard:
        """Async fetch of the synthesized memory card for *entity_uri*.

        Raises StigmemNotFoundError when the entity has no live facts.
        """
        params: dict[str, Any] = {"scope": scope}
        if refresh:
            params["refresh"] = "true"
        resp = await self._http.get(f"/v1/cards/{entity_uri}", params=params)
        _raise_for_status(resp)
        return MemoryCard.model_validate(resp.json())
