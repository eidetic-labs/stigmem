"""Federation route implementations extracted from routes/federation.py.

These functions are the original route handler bodies; they are imported back
into ``routes.federation`` and invoked from thin ``@router``-decorated wrappers.
No behavioural changes — code was moved verbatim from federation.py.

Tests monkey-patch attributes on the ``routes.federation`` module
(``settings``, ``httpx``, ``write_audit_log``).  To honour those patches,
this module looks those names up via ``routes.federation`` lazily inside the
function bodies rather than binding them at import time.
"""

from __future__ import annotations

import contextlib
import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import BackgroundTasks, HTTPException, Request, status

from ..auth import Identity
from ..db import db
from ..identity.capability import CapabilityTokenError, verify_token
from ..identity.manifest import ManifestError, manifest_from_dict, verify_manifest
from ..identity.transparency_log import LogEntry, TransparencyLogUnavailable, make_transparency_log
from ..identity.trust_store import get_peer_manifest, store_peer_manifest
from ..models import (
    PeerRegisterRequest,
    PeerRegisterResponse,
    TombstoneRecord,
    TombstoneRevocationRecord,
)
from ..net_util import assert_safe_url
from ..peer_token import verify_declaration_sig
from ..tls import check_peer_san

logger = logging.getLogger("stigmem.federation")


async def register_peer_impl(
    req: PeerRegisterRequest,
    background_tasks: BackgroundTasks,
    identity: Identity,
) -> PeerRegisterResponse:
    """Register a peer. Fetches its well-known doc and verifies declaration_sig (§5.6)."""
    # Lazy module reference so tests that patch ``federation.httpx`` /
    # ``federation.settings`` continue to take effect.  Cast to ``Any`` because
    # ``httpx`` and ``settings`` are not in the stub-friendly ``__all__``.
    from typing import cast as _cast

    from . import federation as _fed_mod
    _fed = _cast(Any, _fed_mod)

    if not identity.can_federate():
        raise HTTPException(status_code=403, detail="federate permission required")

    peer_id = str(uuid.uuid4())
    allowed_scopes_json = json.dumps(sorted(req.allowed_scopes))

    with db() as conn:
        existing = conn.execute(
            "SELECT id, status FROM peers WHERE node_id = ?", (req.node_id,)
        ).fetchone()
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"peer already registered (status={existing['status']})",
            )
        conn.execute(
            """INSERT INTO peers
               (id, node_id, node_url, federation_pubkey, allowed_scopes,
                status, established_at, declaration_sig, signed_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                peer_id,
                req.node_id,
                req.node_url,
                req.federation_pubkey,
                allowed_scopes_json,
                "pending_verification",
                None,
                req.declaration_sig,
                req.signed_at,
            ),
        )

    # Fetch peer's /.well-known/stigmem to retrieve their published pubkey (§5.6 step 1–3)
    fetched_pubkey: str | None = None
    try:
        async with _fed.httpx.AsyncClient(timeout=10.0) as client:
            wk_resp = await client.get(f"{req.node_url}/.well-known/stigmem")
        if wk_resp.status_code == 200:
            fetched_pubkey = wk_resp.json().get("federation_pubkey")
    except Exception as exc:  # nosec B110 — fetched_pubkey stays None → rejected below
        logger.debug("peer .well-known fetch failed: %s", exc)

    final_status = "rejected"
    verified_at: str | None = None

    if fetched_pubkey and fetched_pubkey == req.federation_pubkey:
        # Signed fields = everything except declaration_sig (spec §6.1 struct "above fields")
        signed_fields: dict[str, Any] = {
            "allowed_scopes": req.allowed_scopes,
            "federation_pubkey": req.federation_pubkey,
            "node_id": req.node_id,
            "node_url": req.node_url,
            "signed_at": req.signed_at,
        }
        if verify_declaration_sig(signed_fields, req.declaration_sig, fetched_pubkey):
            final_status = "active"
            verified_at = datetime.now(UTC).isoformat()

    with db() as conn:
        conn.execute(
            "UPDATE peers SET status = ?, established_at = ? WHERE id = ?",
            (final_status, verified_at, peer_id),
        )

    # §19.2.3 — TL inclusion proof check runs after response to avoid blocking registration
    if final_status == "active":
        background_tasks.add_task(_check_tl_inclusion_for_peer, req.node_id, req.node_url, peer_id)

    return PeerRegisterResponse(peer_id=peer_id, status=final_status, verified_at=verified_at)


async def _check_tl_inclusion_for_peer(node_id: str, node_url: str, peer_id: str) -> None:
    """Check TL inclusion proof for a newly registered peer (§19.2.3).

    trust_mode=strict  (enforce): no proof → downgrade peer to pending_tl_proof
    trust_mode=relaxed (warn):    no proof → accept + audit warning
    trust_mode=off:               skip entirely
    """
    # Lazy lookup: tests monkey-patch ``federation.httpx`` and
    # ``federation.write_audit_log`` — accessing via the module preserves
    # those patches.
    from typing import cast as _cast

    from . import federation as _fed_mod
    _fed = _cast(Any, _fed_mod)

    trust_mode = _fed.settings.trust_mode
    if trust_mode == "off":
        return

    # Try to fetch the peer's manifest from their well-known endpoint
    manifest_obj = None
    try:
        assert_safe_url(node_url, allow_schemes=frozenset({"https", "http"}))
        async with _fed.httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{node_url}/.well-known/stigmem-manifest.json",
                follow_redirects=False,
            )
        if resp.status_code == 200:
            try:
                manifest_obj = manifest_from_dict(resp.json())
                verify_manifest(manifest_obj, trust_mode=trust_mode)
            except (ManifestError, Exception):
                manifest_obj = None
    except Exception:
        manifest_obj = None

    has_tl_proof = False
    if manifest_obj is not None:
        # Check whether the manifest has a TL entry recorded
        existing = get_peer_manifest(manifest_obj.entity_uri, refresh_if_expired=False)
        if existing is None:
            with contextlib.suppress(ManifestError):
                store_peer_manifest(manifest_obj.entity_uri, manifest_obj, trust_mode=trust_mode)

        # Try to verify TL inclusion
        try:
            tl = make_transparency_log()
            from ..db import db as _db
            with _db() as conn:
                row = conn.execute(
                    "SELECT log_entry_json FROM federation_manifests WHERE entity_uri = ?",
                    (manifest_obj.entity_uri,),
                ).fetchone()
            if row and row["log_entry_json"]:
                import json as _json
                le_data = _json.loads(row["log_entry_json"])
                le = LogEntry(
                    log_id=le_data.get("log_id", ""),
                    leaf_hash=le_data.get("leaf_hash", ""),
                    log_index=le_data.get("log_index", -1),
                    integrated_time=le_data.get("integrated_time", 0),
                    inclusion_proof=le_data.get("inclusion_proof", {}),
                )
                tl.verify_inclusion(le)
                has_tl_proof = True
        except TransparencyLogUnavailable as exc:
            logger.debug("transparency log unavailable for TL inclusion check: %s", exc)
        except Exception as exc:  # nosec B110 — TL inclusion check is best-effort
            logger.debug("TL inclusion check failed: %s", exc)

    if not has_tl_proof:
        if trust_mode == "strict":
            _fed.write_audit_log(
                peer_id,
                "tl_proof_missing",
                {"node_id": node_id, "action": "downgraded_to_pending_tl_proof"},
            )
            from ..db import db as _db
            with _db() as conn:
                conn.execute(
                    "UPDATE peers SET status = 'pending_tl_proof' WHERE id = ?",
                    (peer_id,),
                )
        else:
            _fed.write_audit_log(
                peer_id,
                "tl_proof_missing",
                {"node_id": node_id, "action": "accepted_with_warning", "trust_mode": trust_mode},
            )


def federation_ingest_tombstone_impl(
    request: Request,
    payload: dict[str, Any],
    authorization: str | None,
    x_stigmem_capability: str | None,
    try_peer_token_auth: Any,
    get_mtls_peer_cert: Any,
) -> dict[str, Any]:
    """Inbound tombstone push from a federation peer (§23.4.2).

    Auth: peer JWT or capability token with tombstone:write verb (mirrors push_facts).
    Verifies signature against org manifest, writes to local tombstones table.
    """
    # Lazy lookup: tests monkey-patch ``federation.settings``.
    from typing import cast as _cast

    from . import federation as _fed_mod
    _fed = _cast(Any, _fed_mod)
    from ..tombstone_signing import verify_revocation_signature, verify_tombstone_signature
    from ..tombstones import apply_inbound_revocation, apply_inbound_tombstone

    # --- Caller authentication (F-1 fix) ---
    peer_auth = try_peer_token_auth(authorization)
    if peer_auth is not None:
        if _fed.settings.mtls_enabled and request is not None:
            peer_cert = get_mtls_peer_cert(request)
            if not check_peer_san(peer_cert, peer_auth[0]["node_id"]):
                raise HTTPException(
                status_code=401,
                detail="peer certificate URI SAN does not match node_id",
            )
    elif x_stigmem_capability is not None:
        try:
            verify_token(
                x_stigmem_capability,
                lambda uri: get_peer_manifest(
                    uri, refresh_if_expired=True, trust_mode=_fed.settings.trust_mode
                ),
                trust_mode=_fed.settings.trust_mode,
            )
        except CapabilityTokenError as exc:
            raise HTTPException(
                status_code=401, detail=f"capability token invalid: {exc}"
            ) from exc
        try:
            cap_token = json.loads(x_stigmem_capability)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=400, detail=f"malformed capability token JSON: {exc}"
            ) from exc
        verb = cap_token.get("verb", "")
        if verb not in ("tombstone:write", "write"):
            raise HTTPException(
                status_code=403, detail="capability token missing tombstone:write verb"
            )
    else:
        raise HTTPException(status_code=401, detail="peer token or capability token required")

    # --- Revocation branch ---
    if "tombstone_id" in payload:
        try:
            rev = TombstoneRevocationRecord(**payload)
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        # F-2 fix: verify revocation signature before applying (skip when trust_mode=off)
        if _fed.settings.trust_mode != "off":
            if not rev.key_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="revocation missing key_id",
                )
            manifest = get_peer_manifest(rev.signed_by)
            if manifest is None:
                raise HTTPException(status_code=401, detail="no manifest for revocation signer")
            pubkey_b64 = _resolve_pubkey_for_key_id(manifest, rev.key_id)
            if pubkey_b64 is None:
                raise HTTPException(status_code=401, detail="key_id not in signer manifest")
            try:
                verify_revocation_signature(rev, pubkey_b64)
            except ValueError as exc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"revocation_verification_failed: {exc}",
                ) from exc

        apply_inbound_revocation(rev)
        return {"status": "ok", "type": "revocation"}

    # --- Tombstone branch ---
    try:
        record = TombstoneRecord(**payload)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    # §23.4.2.1 — fail-closed signature verification (skip when trust_mode=off)
    if _fed.settings.trust_mode != "off":
        if not record.key_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="tombstone missing key_id",
            )

        manifest = get_peer_manifest(record.signed_by)
        if manifest is None:
            raise HTTPException(status_code=401, detail="no manifest for signer")

        pubkey_b64 = _resolve_pubkey_for_key_id(manifest, record.key_id)
        if pubkey_b64 is None:
            raise HTTPException(status_code=401, detail="key_id not in signer manifest")

        try:
            verify_tombstone_signature(record, pubkey_b64)
        except ValueError as exc:
            _emit_tombstone_verification_failed(record, str(exc))
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"tombstone_verification_failed: {exc}",
            ) from exc

    written = apply_inbound_tombstone(record)
    return {"status": "ok", "written": written}


def _resolve_pubkey_for_key_id(manifest: Any, key_id: str) -> str | None:
    """Return base64url public key from manifest matching key_id, or None."""
    if manifest.key_id == key_id:
        pk: str = manifest.public_key
        return pk
    for evt in getattr(manifest, "rotation_events", []):
        if getattr(evt, "new_key_id", None) == key_id:
            new_pk: str | None = getattr(evt, "new_public_key", None)
            return new_pk
    return None


def _emit_tombstone_verification_failed(record: TombstoneRecord, reason: str) -> None:
    import logging as _logging
    _logging.getLogger("stigmem.tombstones.ingest").error(
        "tombstone_verification_failed: tombstone_id=%s entity=%s reason=%s",
        record.id, record.entity_uri, reason,
    )
