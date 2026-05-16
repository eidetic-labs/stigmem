"""Plugin-owned route wrappers for lazy instruction discovery."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import PlainTextResponse
from stigmem_node.auth import Identity, resolve_identity
from stigmem_node.models.instruction import (
    AuditSubmitRequest,
    PublishManifestRequest,
    RecallInstructionRequest,
)
from stigmem_node.routes import instruction as core_instruction

from .config import load_config_from_env

router = APIRouter(tags=["instruction"])


def _require_enabled() -> None:
    if not load_config_from_env().enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="lazy_instruction_discovery_disabled",
        )


def _require_manifest_publish(req: PublishManifestRequest) -> None:
    config = load_config_from_env()
    if not config.enabled or not config.allow_manifest_publish:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="lazy_instruction_manifest_publish_disabled",
        )
    if not config.allow_file_path_entries and any(entry.path for entry in req.entries):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="lazy_instruction_file_path_entries_disabled",
        )


def _require_instruction_recall() -> None:
    config = load_config_from_env()
    if not config.enabled or not config.allow_instruction_recall:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="lazy_instruction_recall_disabled",
        )


@router.get("/v1/agents/{agent_id}/boot-stub", response_class=PlainTextResponse)
def get_boot_stub(
    agent_id: str,
    identity: Annotated[Identity, Depends(resolve_identity)],
    profile: str = "generic",
) -> PlainTextResponse:
    _require_enabled()
    return core_instruction.get_boot_stub(agent_id=agent_id, identity=identity, profile=profile)


@router.get("/v1/agents/{agent_id}/instruction-manifest")
def get_instruction_manifest(
    agent_id: str,
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> dict[str, Any]:
    _require_enabled()
    return core_instruction.get_instruction_manifest(agent_id=agent_id, identity=identity)


@router.put("/v1/agents/{agent_id}/instruction-manifest", status_code=200)
def publish_instruction_manifest(
    agent_id: str,
    req: PublishManifestRequest,
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> dict[str, Any]:
    _require_manifest_publish(req)
    return core_instruction.publish_instruction_manifest(
        agent_id=agent_id,
        req=req,
        identity=identity,
    )


@router.post("/v1/agents/{agent_id}/recall-instruction")
def recall_instruction(
    agent_id: str,
    req: RecallInstructionRequest,
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> dict[str, Any]:
    _require_instruction_recall()
    return core_instruction.recall_instruction(agent_id=agent_id, req=req, identity=identity)


@router.post("/v1/instruction/audit", status_code=status.HTTP_204_NO_CONTENT)
def submit_discovery_audit(
    req: AuditSubmitRequest,
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> Response:
    _require_instruction_recall()
    return core_instruction.submit_discovery_audit(req=req, identity=identity)


@router.get("/v1/agents/{agent_id}/instruction-manifest/coverage")
def get_manifest_coverage(
    agent_id: str,
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> dict[str, Any]:
    _require_enabled()
    return core_instruction.get_manifest_coverage(agent_id=agent_id, identity=identity)
