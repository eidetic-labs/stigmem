"""Pull replication background task (spec §6.3).

The pull loop runs as an asyncio task in the app lifespan.
It is also callable directly for testing.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
from datetime import UTC, datetime
from typing import Any

import httpx

from .db import db
from .federation_ingest import ingest_fact
from .peer_token import create_peer_token
from .settings import settings

logger = logging.getLogger("stigmem.federation.pull")

_MAX_BACKOFF_S = 300.0   # 5 minutes
_BASE_BACKOFF_S = 1.0


def _jitter(base: float) -> float:
    return base * (1 + random.uniform(-0.2, 0.2))  # nosec B311 — retry jitter, not cryptographic


def load_cursor(peer_id: str) -> str | None:
    with db() as conn:
        row = conn.execute(
            "SELECT cursor FROM replication_cursors WHERE peer_id = ? AND direction = 'inbound'",
            (peer_id,),
        ).fetchone()
    return row["cursor"] if row else None


def save_cursor(peer_id: str, cursor: str | None) -> None:
    with db() as conn:
        conn.execute(
            """INSERT INTO replication_cursors (peer_id, direction, cursor, updated_at)
               VALUES (?,?,?,?)
               ON CONFLICT(peer_id, direction)
               DO UPDATE SET cursor = excluded.cursor, updated_at = excluded.updated_at""",
            (peer_id, "inbound", cursor, datetime.now(UTC).isoformat()),
        )


async def pull_from_peer_once(
    peer: dict[str, Any],
    client: httpx.AsyncClient,
    cursor: str | None,
) -> str | None:
    """Pull one page of facts from the peer. Returns the new cursor (or same if no more)."""
    allowed_scopes: list[str] = json.loads(peer["allowed_scopes"])
    token = create_peer_token(peer["node_id"], allowed_scopes)

    params: dict[str, Any] = {"limit": 100}
    if cursor:
        params["cursor"] = cursor

    backoff = _BASE_BACKOFF_S
    while True:
        try:
            resp = await client.get(
                f"{peer['node_url']}/v1/federation/facts",
                params=params,
                headers={"Authorization": f"Bearer {token}"},
                timeout=30.0,
            )
        except httpx.RequestError as exc:
            logger.warning("Pull network error from %s: %s", peer["node_id"], exc)
            return cursor  # retain old cursor; will retry next cycle

        if resp.status_code == 429:
            backoff = min(backoff * 2, _MAX_BACKOFF_S)
            delay = _jitter(backoff)
            logger.info("429 from %s — backing off %.1fs", peer["node_id"], delay)
            await asyncio.sleep(delay)
            token = create_peer_token(peer["node_id"], allowed_scopes)  # refresh token after sleep
            continue

        if resp.status_code != 200:
            logger.warning("Pull from %s returned %s", peer["node_id"], resp.status_code)
            return cursor

        data = resp.json()
        # origin_allowed_scopes = peer's registered declaration scope (spec §6.8.1).
        # These fields are internal and MUST NOT be re-replicated (§3.1), so we
        # derive them from the peer registry rather than reading from the fact payload.
        for fact in data.get("facts", []):
            ingest_fact(
                fact,
                peer["node_id"],
                origin_allowed_scopes=allowed_scopes,
            )

        new_cursor: str | None = data.get("cursor")
        return new_cursor


async def pull_all_peers_once() -> None:
    """Pull one batch from every active peer. Called by the loop and by tests."""
    with db() as conn:
        peers = conn.execute(
            "SELECT id, node_id, node_url, allowed_scopes FROM peers WHERE status = 'active'"
        ).fetchall()

    if not peers:
        return

    async with httpx.AsyncClient() as client:
        for peer in peers:
            peer_dict = dict(peer)
            cursor = load_cursor(peer_dict["id"])
            new_cursor = await pull_from_peer_once(peer_dict, client, cursor)
            if new_cursor != cursor:
                save_cursor(peer_dict["id"], new_cursor)


async def pull_loop_task() -> None:
    """Background asyncio task: pull from all active peers every pull_interval_s."""
    while True:
        await asyncio.sleep(settings.federation_pull_interval_s)
        try:
            await pull_all_peers_once()
        except Exception:
            logger.exception("Unexpected error in pull loop")
