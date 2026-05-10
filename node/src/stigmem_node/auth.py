"""API-key authentication for the Stigmem reference node.

Auth model (spec §3.5):
  - Callers present `Authorization: Bearer <raw-key>` on every request.
  - Raw keys are never stored; only their SHA-256 hex digest is persisted.
  - Each key maps to an entity_uri and a JSON-array of permissions:
    ["read"], ["read","write"], or ["read","write","federate"].
  - `STIGMEM_AUTH_REQUIRED` defaults to **True** — every request must
    present a valid Bearer token. Set `STIGMEM_AUTH_REQUIRED=false` to
    opt into anonymous-mode for single-operator development; this is
    NOT appropriate for any deployment that accepts requests from
    agents you don't fully control. See LIMITATIONS.md §"LLM agents
    holding admin-scope API keys" for context.

Bootstrapping the first key (single-operator install):
  $ KEY=$(openssl rand -hex 32)
  $ stigmem auth bootstrap-key --key "$KEY"
  # then use $KEY as `Authorization: Bearer $KEY` for subsequent requests.

  The system NEVER generates the key — the caller provides the value and
  retains full custody. We hash and store it. This is by design:
  removing the system as the credential-generation surface eliminates
  the "reveal channel" risk entirely. The command refuses to run when
  api_keys is non-empty (bootstrap is one-shot); after bootstrap,
  additional keys go through `POST /v1/auth/keys`.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .db import db
from .settings import settings as settings


def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


BEARER = HTTPBearer(auto_error=False)


class Identity:
    """Resolved caller identity (spec §3.5)."""

    def __init__(
        self,
        entity_uri: str,
        permissions: list[str],
        oidc_sub: str | None = None,
        tenant_id: str = "default",
    ) -> None:
        self.entity_uri = entity_uri
        self.permissions = set(permissions)
        self.oidc_sub = oidc_sub
        self.tenant_id = tenant_id

    def can_read(self) -> bool:
        return "read" in self.permissions

    def can_write(self) -> bool:
        return "write" in self.permissions

    def can_federate(self) -> bool:
        return "federate" in self.permissions

    def can_audit(self) -> bool:
        """True when the principal holds the audit.read capability (spec §22.3)."""
        return "audit.read" in self.permissions

    def is_admin(self) -> bool:
        """True when the principal holds the admin capability (spec §24.3.2)."""
        return "admin" in self.permissions


_ANON = Identity("anon:trusted", ["read", "write", "federate"], tenant_id="default")


def resolve_identity(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(BEARER)],
) -> Identity:
    """Dependency: resolve caller identity from Bearer token.

    If auth is disabled, returns a fully-trusted anonymous identity.
    If auth is enabled, the token must match a non-expired api_keys row.
    """
    if not settings.auth_required:
        if creds is not None:
            # Still try to resolve a real identity even in non-required mode
            identity = _lookup(creds.credentials)
            if identity:
                return identity
        return _ANON

    if creds is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    identity = _lookup(creds.credentials)
    if identity is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return identity


def _lookup(raw_key: str) -> Identity | None:
    key_hash = _hash_key(raw_key)
    now = datetime.now(UTC).isoformat()
    with db() as conn:
        row = conn.execute(
            "SELECT entity_uri, permissions, expires_at, oidc_sub, tenant_id"
            " FROM api_keys WHERE key_hash = ?",
            (key_hash,),
        ).fetchone()
    if row is None:
        return None
    if row["expires_at"] and row["expires_at"] < now:
        return None
    perms: list[str] = json.loads(row["permissions"])
    return Identity(
        entity_uri=row["entity_uri"],
        permissions=perms,
        oidc_sub=row["oidc_sub"],
        tenant_id=row["tenant_id"] or "default",
    )


def register_api_key(
    raw_key: str,
    entity_uri: str,
    permissions: list[str] | None = None,
    description: str | None = None,
    expires_at: str | None = None,
    oidc_sub: str | None = None,
    tenant_id: str = "default",
) -> str:
    """Persist the hash of a caller-provided raw API key. Returns the key_id.

    The caller is responsible for generating `raw_key` (e.g., from
    `secrets.token_hex(32)` or `openssl rand -hex 32`) and for storing it
    securely. This function never touches the key after hashing.
    """
    if permissions is None:
        permissions = ["read", "write"]
    key_id = str(uuid.uuid4())
    with db() as conn:
        conn.execute(
            """INSERT INTO api_keys
               (id, key_hash, entity_uri, permissions, description,
                created_at, expires_at, oidc_sub, tenant_id)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                key_id,
                _hash_key(raw_key),
                entity_uri,
                json.dumps(permissions),
                description,
                datetime.now(UTC).isoformat(),
                expires_at,
                oidc_sub,
                tenant_id,
            ),
        )
    return key_id


def create_api_key(
    entity_uri: str,
    permissions: list[str] | None = None,
    description: str | None = None,
    expires_at: str | None = None,
    oidc_sub: str | None = None,
    tenant_id: str = "default",
) -> str:
    """Mint a new raw API key, persist its hash, and return the raw key.

    Internal/test-only convenience over `register_api_key`. Adopter-facing
    flows should require the caller to provide the key material (see
    `stigmem auth bootstrap-key`) so the system is never the credential
    generation surface.
    """
    raw = str(uuid.uuid4()).replace("-", "")  # 32-char hex
    register_api_key(
        raw_key=raw,
        entity_uri=entity_uri,
        permissions=permissions,
        description=description,
        expires_at=expires_at,
        oidc_sub=oidc_sub,
        tenant_id=tenant_id,
    )
    return raw
