"""Org manifest format, signing, and verification — spec §19.1.

Public surface:
    OrgManifest       — dataclass matching §19.1.2 fields
    RotationEvent     — single step in a key-rotation chain
    ManifestError     — raised on any structural/cryptographic violation

    sign_manifest(manifest, private_key) -> OrgManifest
    verify_manifest(manifest, trust_mode) -> bool  (raises ManifestError on failure)
    verify_rotation_chain(manifest, previous_key_id, previous_pubkey) -> bool

Security requirements enforced here:
    - JCS via canonicaljson (RFC 8785), NOT json.dumps(sort_keys=True)
    - expires_at <= issued_at + 730 days; in strict mode <= 365 days
    - Rotation chain validated from the previously-accepted key, all steps
    - No key_id reuse (regression/cycle attack prevention)
    - rotation_events capped at 100 entries
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import canonicaljson
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

_MAX_VALIDITY_DAYS = 730
_STRICT_MAX_DAYS = 365
_MAX_ROTATION_EVENTS = 100


class ManifestError(ValueError):
    """Raised when a manifest fails structural or cryptographic validation."""


@dataclass
class RotationEvent:
    """A single key-rotation step in the org manifest chain.

    Each event is signed by the *previous* key, enabling chain verification
    without external key registry lookups.

    `previous_public_key` stores the retiring key's public bytes (base64url)
    so verifiers can check tokens issued under that key during the dual-trust
    window (§22.2) without an external key registry.  Empty string on events
    created before §22.2 support; present on all Phase-12-or-later rotations.
    """

    previous_key_id: str
    new_key_id: str
    new_public_key: str       # base64url Ed25519 public key for new_key_id
    rotated_at: str           # ISO-8601 UTC
    signature: str            # base64url Ed25519 sig over canonical body (by previous key)
    previous_public_key: str = ""  # base64url retiring key pubkey (§22.2 dual-trust)


@dataclass
class OrgManifest:
    """Org-identity manifest — spec §19.1.2.

    `entities` lists every entity URI this org is authorised to issue
    capability tokens for (including itself).  The C1 rule enforces that
    a token's `subject` must appear in the issuer's `entities` list.

    `signature` is the self-signature over the JCS body (all fields except
    `signature` itself).  It is empty-string before signing.
    """

    entity_uri: str
    key_id: str
    public_key: str          # base64url Ed25519 current signing key
    issued_at: str           # ISO-8601 UTC
    expires_at: str          # ISO-8601 UTC
    entities: list[str] = field(default_factory=list)
    rotation_events: list[RotationEvent] = field(default_factory=list)
    signature: str = ""      # base64url self-signature; empty before signing


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _pad(s: str) -> str:
    return s + "=" * (-len(s) % 4)


def _pubkey_from_b64(b64: str) -> Ed25519PublicKey:
    raw = base64.urlsafe_b64decode(_pad(b64))
    return Ed25519PublicKey.from_public_bytes(raw)


def _rotation_event_to_dict(evt: RotationEvent) -> dict[str, Any]:
    d: dict[str, Any] = {
        "new_key_id": evt.new_key_id,
        "new_public_key": evt.new_public_key,
        "previous_key_id": evt.previous_key_id,
        "rotated_at": evt.rotated_at,
        "signature": evt.signature,
    }
    if evt.previous_public_key:
        d["previous_public_key"] = evt.previous_public_key
    return d


def _manifest_signing_body(manifest: OrgManifest) -> bytes:
    """Return JCS-canonical bytes covering all fields except `signature`."""
    doc: dict[str, Any] = {
        "entities": manifest.entities,
        "entity_uri": manifest.entity_uri,
        "expires_at": manifest.expires_at,
        "issued_at": manifest.issued_at,
        "key_id": manifest.key_id,
        "public_key": manifest.public_key,
        "rotation_events": [_rotation_event_to_dict(e) for e in manifest.rotation_events],
    }
    return canonicaljson.encode_canonical_json(doc)


def _parse_iso(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _validate_expiry(manifest: OrgManifest, trust_mode: str) -> None:
    issued = _parse_iso(manifest.issued_at)
    expires = _parse_iso(manifest.expires_at)

    if expires <= issued:
        raise ManifestError("expires_at must be after issued_at")

    if expires > issued + timedelta(days=_MAX_VALIDITY_DAYS):
        raise ManifestError(
            f"expires_at exceeds maximum of {_MAX_VALIDITY_DAYS} days from issued_at"
        )

    if trust_mode == "strict" and expires > issued + timedelta(days=_STRICT_MAX_DAYS):
        raise ManifestError(
            f"expires_at exceeds {_STRICT_MAX_DAYS}-day limit enforced by trust_mode=strict"
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def sign_manifest(manifest: OrgManifest, private_key: Ed25519PrivateKey) -> OrgManifest:
    """Sign *manifest* in place; sets and returns manifest.signature."""
    manifest.signature = ""
    body = _manifest_signing_body(manifest)
    sig_bytes = private_key.sign(body)
    manifest.signature = base64.urlsafe_b64encode(sig_bytes).decode().rstrip("=")
    return manifest


def verify_manifest(manifest: OrgManifest, trust_mode: str = "relaxed") -> bool:
    """Self-signature check + expiry + rotation-event limit.

    Does NOT validate the rotation chain from a previously-accepted key —
    call verify_rotation_chain() separately for that.

    Returns True on success. Raises ManifestError on any failure.
    """
    _validate_expiry(manifest, trust_mode)

    if len(manifest.rotation_events) > _MAX_ROTATION_EVENTS:
        raise ManifestError(
            f"rotation_events has {len(manifest.rotation_events)} entries "
            f"(max {_MAX_ROTATION_EVENTS})"
        )

    try:
        pub = _pubkey_from_b64(manifest.public_key)
        body = _manifest_signing_body(manifest)
        sig_bytes = base64.urlsafe_b64decode(_pad(manifest.signature))
        pub.verify(sig_bytes, body)
    except InvalidSignature as exc:
        raise ManifestError("self-signature verification failed") from exc
    except Exception as exc:
        raise ManifestError(f"self-signature error: {exc}") from exc

    return True


def verify_rotation_chain(
    manifest: OrgManifest,
    previous_key_id: str,
    previous_pubkey_b64: str,
) -> bool:
    """Validate ALL rotation steps from the previously-accepted key to current.

    §19.1.4 invariants enforced:
      1. Chain is contiguous from previous_key_id
      2. Each event signature is valid (signed by the preceding key)
      3. manifest.key_id matches the terminal new_key_id
      4. manifest.public_key matches the terminal new_public_key
      5. No key_id reuse (regression / cross-entity replay prevention)

    Returns True on success. Raises ManifestError on any violation.
    """
    events = manifest.rotation_events

    # No rotation: current key must equal previous key
    if not events:
        if manifest.key_id != previous_key_id:
            raise ManifestError(
                f"no rotation events but manifest.key_id {manifest.key_id!r} "
                f"differs from previous_key_id {previous_key_id!r}"
            )
        return True

    # Find the starting index — the first event originating from previous_key_id
    start_idx: int | None = None
    for i, evt in enumerate(events):
        if evt.previous_key_id == previous_key_id:
            start_idx = i
            break

    if start_idx is None:
        # No event starts from previous_key_id; chain is disconnected
        if manifest.key_id == previous_key_id:
            return True  # key unchanged, no rotation needed
        raise ManifestError(
            f"rotation chain does not connect previous_key_id {previous_key_id!r} "
            f"to manifest.key_id {manifest.key_id!r}"
        )

    seen_key_ids: set[str] = {previous_key_id}
    current_key_id = previous_key_id
    current_pubkey_b64 = previous_pubkey_b64

    for i, evt in enumerate(events[start_idx:], start_idx):
        # Contiguity
        if evt.previous_key_id != current_key_id:
            raise ManifestError(
                f"rotation event {i}: expected previous_key_id={current_key_id!r}, "
                f"got {evt.previous_key_id!r} (chain gap)"
            )

        # No regression / cycle
        if evt.new_key_id in seen_key_ids:
            raise ManifestError(
                f"rotation event {i}: key_id {evt.new_key_id!r} already appears in "
                f"the chain (regression or cycle attack)"
            )

        # Verify rotation-event signature with the current (previous) key
        rotation_body = canonicaljson.encode_canonical_json({
            "new_key_id": evt.new_key_id,
            "new_public_key": evt.new_public_key,
            "previous_key_id": evt.previous_key_id,
            "rotated_at": evt.rotated_at,
        })
        try:
            pub = _pubkey_from_b64(current_pubkey_b64)
            sig_bytes = base64.urlsafe_b64decode(_pad(evt.signature))
            pub.verify(sig_bytes, rotation_body)
        except InvalidSignature as exc:
            raise ManifestError(
                f"rotation event {i}: signature invalid (signed with key {current_key_id!r})"
            ) from exc
        except Exception as exc:
            raise ManifestError(f"rotation event {i}: verification error: {exc}") from exc

        seen_key_ids.add(evt.new_key_id)
        current_key_id = evt.new_key_id
        current_pubkey_b64 = evt.new_public_key

    # Terminal invariants
    if current_key_id != manifest.key_id:
        raise ManifestError(
            f"rotation chain terminates at {current_key_id!r} "
            f"but manifest.key_id is {manifest.key_id!r}"
        )
    if current_pubkey_b64 != manifest.public_key:
        raise ManifestError(
            "rotation chain terminal public_key does not match manifest.public_key"
        )

    return True


def sign_rotation_event(
    previous_key_id: str,
    new_key_id: str,
    new_public_key_b64: str,
    rotated_at: str,
    private_key: Ed25519PrivateKey,
) -> str:
    """Sign a rotation event with the *previous* private key. Returns base64url signature."""
    body = canonicaljson.encode_canonical_json({
        "new_key_id": new_key_id,
        "new_public_key": new_public_key_b64,
        "previous_key_id": previous_key_id,
        "rotated_at": rotated_at,
    })
    sig_bytes = private_key.sign(body)
    return base64.urlsafe_b64encode(sig_bytes).decode().rstrip("=")


# ---------------------------------------------------------------------------
# Serialisation helpers
# ---------------------------------------------------------------------------


def manifest_to_dict(manifest: OrgManifest) -> dict[str, Any]:
    return {
        "entities": manifest.entities,
        "entity_uri": manifest.entity_uri,
        "expires_at": manifest.expires_at,
        "issued_at": manifest.issued_at,
        "key_id": manifest.key_id,
        "public_key": manifest.public_key,
        "rotation_events": [_rotation_event_to_dict(e) for e in manifest.rotation_events],
        "signature": manifest.signature,
    }


def manifest_from_dict(data: dict[str, Any]) -> OrgManifest:
    return OrgManifest(
        entity_uri=data["entity_uri"],
        key_id=data["key_id"],
        public_key=data["public_key"],
        issued_at=data["issued_at"],
        expires_at=data["expires_at"],
        entities=data.get("entities", []),
        rotation_events=[
            RotationEvent(
                previous_key_id=e["previous_key_id"],
                new_key_id=e["new_key_id"],
                new_public_key=e["new_public_key"],
                rotated_at=e["rotated_at"],
                signature=e["signature"],
                previous_public_key=e.get("previous_public_key", ""),
            )
            for e in data.get("rotation_events", [])
        ],
        signature=data.get("signature", ""),
    )
