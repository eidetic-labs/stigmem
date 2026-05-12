"""Track C / C1 — per-agent Ed25519 keypair registration.

Agents register their public key; the node can then verify attestation tokens
on fact assertions to prove the caller owns the source identity.

POST   /v1/auth/agent-keys           register a public key for the calling entity
GET    /v1/auth/agent-keys           list my registered agent keys
DELETE /v1/auth/agent-keys/{key_id}  revoke a key (sets status=revoked)
"""

from __future__ import annotations

import base64
import logging
import uuid
from datetime import UTC, datetime
from typing import Annotated

from cryptography.exceptions import InvalidKey
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from fastapi import APIRouter, Depends, HTTPException, status

from ..auth import Identity, resolve_identity
from ..db import db
from ..models import AgentKeyRecord, AgentKeyRegisterRequest

logger = logging.getLogger("stigmem.agent_keys")
router = APIRouter(prefix="/v1/auth/agent-keys", tags=["auth"])


def _decode_pubkey(b64: str) -> Ed25519PublicKey:
    """Decode a base64url Ed25519 public key; raise ValueError on bad input."""
    try:
        raw = base64.urlsafe_b64decode(b64 + "=" * (-len(b64) % 4))
        return Ed25519PublicKey.from_public_bytes(raw)
    except Exception as exc:
        raise ValueError(f"invalid Ed25519 public key: {exc}") from exc


@router.post("", response_model=AgentKeyRecord, status_code=status.HTTP_201_CREATED)
def register_agent_key(
    req: AgentKeyRegisterRequest,
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> AgentKeyRecord:
    """Register an Ed25519 public key for source-attestation on fact assertions."""
    if not identity.can_write():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="write permission required"
        )

    try:
        _decode_pubkey(req.public_key)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    key_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()

    # Normalise key: strip padding to store canonical base64url
    canonical_key = req.public_key.rstrip("=")

    with db() as conn:
        conn.execute(
            """INSERT INTO agent_keys
               (id, entity_uri, public_key, description, registered_at, status)
               VALUES (?,?,?,?,?,?)""",
            (key_id, identity.entity_uri, canonical_key, req.description, now, "active"),
        )

    logger.info("Agent key registered: id=%s entity=%s", key_id, identity.entity_uri)
    return AgentKeyRecord(
        id=key_id,
        entity_uri=identity.entity_uri,
        public_key=canonical_key,
        description=req.description,
        registered_at=now,
        status="active",
    )


@router.get("", response_model=list[AgentKeyRecord])
def list_agent_keys(
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> list[AgentKeyRecord]:
    """List all agent keys (active and revoked) for the caller's entity."""
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM agent_keys WHERE entity_uri = ? ORDER BY registered_at DESC",
            (identity.entity_uri,),
        ).fetchall()
    return [
        AgentKeyRecord(
            id=r["id"],
            entity_uri=r["entity_uri"],
            public_key=r["public_key"],
            description=r["description"],
            registered_at=r["registered_at"],
            status=r["status"],
        )
        for r in rows
    ]


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_agent_key(
    key_id: str,
    identity: Annotated[Identity, Depends(resolve_identity)],
) -> None:
    """Revoke an agent key. Callers may only revoke their own keys."""
    with db() as conn:
        row = conn.execute(
            "SELECT entity_uri, status FROM agent_keys WHERE id = ?", (key_id,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="agent key not found")
        if row["entity_uri"] != identity.entity_uri:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="cannot revoke another entity's key",
            )
        if row["status"] == "revoked":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="key is already revoked",
            )
        conn.execute("UPDATE agent_keys SET status = 'revoked' WHERE id = ?", (key_id,))

    logger.info("Agent key revoked: id=%s by entity=%s", key_id, identity.entity_uri)


# ---------------------------------------------------------------------------
# Internal helper — used by routes/facts.py for attestation verification
# ---------------------------------------------------------------------------


def verify_attestation(
    key_id: str,
    signature_b64: str,
    canonical_message: bytes,
    caller_entity_uri: str,
) -> str:
    """Verify an Ed25519 attestation token. Returns key_id on success.

    Raises HTTPException on any verification failure.
    """
    with db() as conn:
        row = conn.execute(
            "SELECT entity_uri, public_key, status FROM agent_keys WHERE id = ?", (key_id,)
        ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"attestation.key_id {key_id!r} not found",
        )
    if row["status"] == "revoked":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"attestation.key_id {key_id!r} has been revoked",
        )
    if row["entity_uri"] != caller_entity_uri:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="attestation key belongs to a different entity",
        )

    try:
        pubkey = _decode_pubkey(row["public_key"])
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="stored public key is corrupt",
        ) from exc

    try:
        raw_sig = base64.urlsafe_b64decode(signature_b64 + "=" * (-len(signature_b64) % 4))
        pubkey.verify(raw_sig, canonical_message)
    except (InvalidKey, Exception) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="attestation signature verification failed",
        ) from exc

    return key_id
