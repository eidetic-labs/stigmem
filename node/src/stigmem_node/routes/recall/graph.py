"""Graph expansion recall stage."""

from __future__ import annotations

from typing import Any

from ...auth import Identity
from ...recall.graph import bfs_neighbors

_MAX_SEED_ENTITIES = 5
_MAX_GRAPH_ENTITIES = 50


def _graph_expand(
    conn: Any,
    seed_fact_ids: list[str],
    depth: int,
    scope: str,
    tenant_id: str,
    identity: Identity,
    k: int,
    min_confidence: float,
    now: str,
) -> dict[str, int]:
    """BFS-expand from top-seed entities; return {fact_id: min_hops}."""
    if not seed_fact_ids:
        return {}

    placeholders = ",".join("?" * len(seed_fact_ids))
    seed_rows = conn.execute(
        f"SELECT DISTINCT entity FROM facts WHERE id IN ({placeholders})",  # noqa: S608  # nosec B608
        seed_fact_ids,
    ).fetchall()

    seed_entities = [row["entity"] for row in seed_rows][:_MAX_SEED_ENTITIES]
    if not seed_entities:
        return {}

    entity_min_hops: dict[str, int] = {}
    for seed in seed_entities:
        neighbors = bfs_neighbors(
            conn,
            seed_entity=seed,
            max_depth=depth,
            scope=scope,
            tenant_id=tenant_id,
            identity=identity,
        )
        for n in neighbors:
            prev = entity_min_hops.get(n.entity)
            if prev is None or n.hops < prev:
                entity_min_hops[n.entity] = n.hops

    if not entity_min_hops:
        return {}

    entities = list(entity_min_hops.keys())[:_MAX_GRAPH_ENTITIES]
    placeholders = ",".join("?" * len(entities))
    sql = f"""
        SELECT f.id, f.entity
        FROM facts f
        LEFT JOIN fact_validity_overrides fvo ON fvo.fact_id = f.id
        WHERE f.entity IN ({placeholders})  -- nosec B608
          AND f.scope = ?
          AND f.tenant_id = ?
          AND COALESCE(fvo.confidence, f.confidence) >= ?
          AND (
            COALESCE(fvo.valid_until, f.valid_until) IS NULL
            OR COALESCE(fvo.valid_until, f.valid_until) > ?
          )
        LIMIT ?
        """  # noqa: S608  # nosec B608
    fact_rows = conn.execute(
        sql,
        [*entities, scope, tenant_id, min_confidence, now, k],
    ).fetchall()

    return {row["id"]: entity_min_hops.get(row["entity"], depth) for row in fact_rows}
