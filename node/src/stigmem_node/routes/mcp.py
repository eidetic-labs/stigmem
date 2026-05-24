"""MCP connector discovery routes."""

from __future__ import annotations

from fastapi import APIRouter

from ..cli.mcp import editor_catalog

router = APIRouter(prefix="/v1/mcp", tags=["mcp"])


@router.get("/connectors")
async def list_mcp_connectors() -> dict[str, object]:
    """List supported MCP editor connectors and validation tiers."""
    return {
        "version": "1",
        "connectors": editor_catalog(),
    }
