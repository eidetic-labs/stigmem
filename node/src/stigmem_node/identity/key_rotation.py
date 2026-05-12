"""Key-rotation primitive — spec §22.2 (Phase 12).

Public surface:
    KeyRotationLogEntry  — TL entry shape for a key-rotation event (§22.2.3)
    RotationResult       — output bundle from rotate_key()
    generate_key_id()    — derive hex key_id from Ed25519PublicKey
    sign_key_rotation_entry()  — sign KeyRotationLogEntry with retiring key
    rotate_key()         — orchestrate a full rotation or dry-run preview

Security design (§22.2):
    - Dual-trust window: retiring key stays in accept_set for at least
      dual_trust_days (minimum 90 = max token TTL per §19.3.2 / §22.2.2).
    - Rotation event signed by old key (proves continuity from prior identity).
    - Updated manifest signed by new key and submitted to TL.
    - KeyRotationLogEntry signed by old key and submitted to TL separately,
      providing non-repudiation and allowing third-party auditability.
    - dry_run=True produces all artefacts for inspection without TL writes.
"""

from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import canonicaljson
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)

from .manifest import (
    OrgManifest,
    RotationEvent,
    manifest_to_dict,
    sign_manifest,
    sign_rotation_event,
)
from .transparency_log import LogEntry, make_transparency_log

_DUAL_TRUST_DAYS = 90  # §22.2.2: must be ≥ max token TTL


@dataclass
class KeyRotationLogEntry:
    """Transparency-log entry for a key-rotation event — spec §22.2.3.

    `rotation_sig` is an Ed25519 signature by the retiring key over the
    JCS-canonical body of all fields except rotation_sig itself.  This
    anchors the rotation event to the prior cryptographic identity and lets
    third parties verify the chain without trusting the submitter.
    """

    event_type: str  # always "key_rotation"
    entity_uri: str
    old_key_id: str
    new_key_id: str
    rotated_at: str  # ISO-8601 UTC
    dual_trust_expires_at: str  # ISO-8601 UTC; old key tokens accepted until here
    manifest_log_index: int  # TL index of the updated manifest; -1 on dry-run
    rotation_sig: str  # base64url Ed25519 sig by retiring key


@dataclass
class RotationResult:
    """All artefacts produced by a successful key rotation."""

    new_private_key: Ed25519PrivateKey
    new_private_key_b64: str  # base64url raw seed — store in secrets manager
    new_manifest: OrgManifest
    manifest_log_entry: LogEntry | None  # None on dry-run
    rotation_log_entry: KeyRotationLogEntry
    rotation_tl_entry: LogEntry | None  # None on dry-run


def generate_key_id(public_key: Ed25519PublicKey) -> str:
    """Derive a short deterministic hex key_id from raw Ed25519 public key bytes."""
    raw = public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)
    return hashlib.sha256(raw).hexdigest()[:16]


def sign_key_rotation_entry(
    entry: KeyRotationLogEntry,
    old_private_key: Ed25519PrivateKey,
) -> str:
    """Sign *entry* with the retiring private key.  Returns base64url signature.

    Signing body is JCS-canonical JSON of all fields except rotation_sig.
    Lexicographic key order is guaranteed by canonicaljson (RFC 8785).
    """
    body = canonicaljson.encode_canonical_json(
        {
            "dual_trust_expires_at": entry.dual_trust_expires_at,
            "entity_uri": entry.entity_uri,
            "event_type": entry.event_type,
            "manifest_log_index": entry.manifest_log_index,
            "new_key_id": entry.new_key_id,
            "old_key_id": entry.old_key_id,
            "rotated_at": entry.rotated_at,
        }
    )
    sig_bytes = old_private_key.sign(body)
    return base64.urlsafe_b64encode(sig_bytes).decode().rstrip("=")


def rotate_key(
    entity_uri: str,
    old_manifest: OrgManifest,
    old_private_key: Ed25519PrivateKey,
    *,
    dual_trust_days: int = _DUAL_TRUST_DAYS,
    manifest_validity_days: int = 365,
    dry_run: bool = False,
) -> RotationResult:
    """Orchestrate an Ed25519 key rotation (§22.2).

    Steps performed:
      1. Generate new Ed25519 keypair; derive new_key_id.
      2. Sign the rotation event with the old (retiring) key.
      3. Build the updated manifest with the new key and rotation event appended.
      4. Re-sign the manifest with the new key.
      5. Submit updated manifest to the transparency log.
      6. Build and sign the KeyRotationLogEntry with the retiring key.
      7. Submit KeyRotationLogEntry to the transparency log.

    Args:
        entity_uri:             The rotating org's canonical URI.
        old_manifest:           Current signed manifest; must already pass
                                verify_manifest() — caller is responsible.
        old_private_key:        Retiring Ed25519 private key.
        dual_trust_days:        Days the retiring key stays in accept_set.
                                Must be ≥ 90 (max token TTL per §19.3.2).
        manifest_validity_days: Validity window for the new manifest (≤ 365
                                in strict trust_mode per §19.1.3).
        dry_run:                Skip TL submission; manifest_log_index = -1.

    Returns:
        RotationResult with new key material, updated manifest, and TL entries.

    Raises:
        ValueError:                  if dual_trust_days < 90.
        TransparencyLogUnavailable:  on TL write failure (non-dry-run only).
    """
    if dual_trust_days < _DUAL_TRUST_DAYS:
        raise ValueError(
            f"dual_trust_days must be ≥ {_DUAL_TRUST_DAYS} (max token TTL §19.3.2); "
            f"got {dual_trust_days}"
        )

    now = datetime.now(UTC)
    rotated_at = now.isoformat().replace("+00:00", "Z")
    dual_trust_expires_at = (
        (now + timedelta(days=dual_trust_days)).isoformat().replace("+00:00", "Z")
    )

    # 1. Generate new keypair
    new_priv = Ed25519PrivateKey.generate()
    new_pub = new_priv.public_key()
    new_priv_raw = new_priv.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
    new_pub_raw = new_pub.public_bytes(Encoding.Raw, PublicFormat.Raw)
    new_priv_b64 = base64.urlsafe_b64encode(new_priv_raw).decode().rstrip("=")
    new_pub_b64 = base64.urlsafe_b64encode(new_pub_raw).decode().rstrip("=")
    new_key_id = generate_key_id(new_pub)

    old_key_id = old_manifest.key_id
    old_pub_b64 = old_manifest.public_key

    # 2. Sign rotation event with retiring key
    rot_sig = sign_rotation_event(
        previous_key_id=old_key_id,
        new_key_id=new_key_id,
        new_public_key_b64=new_pub_b64,
        rotated_at=rotated_at,
        private_key=old_private_key,
    )
    rotation_event = RotationEvent(
        previous_key_id=old_key_id,
        new_key_id=new_key_id,
        new_public_key=new_pub_b64,
        rotated_at=rotated_at,
        signature=rot_sig,
        previous_public_key=old_pub_b64,  # stored for §22.2 dual-trust verification
    )

    # 3–4. Build and sign new manifest
    new_issued_at = rotated_at
    new_expires_at = (
        (now + timedelta(days=manifest_validity_days)).isoformat().replace("+00:00", "Z")
    )
    new_manifest = OrgManifest(
        entity_uri=entity_uri,
        key_id=new_key_id,
        public_key=new_pub_b64,
        issued_at=new_issued_at,
        expires_at=new_expires_at,
        entities=list(old_manifest.entities),
        rotation_events=list(old_manifest.rotation_events) + [rotation_event],
    )
    sign_manifest(new_manifest, new_priv)

    if dry_run:
        rotation_log_entry = KeyRotationLogEntry(
            event_type="key_rotation",
            entity_uri=entity_uri,
            old_key_id=old_key_id,
            new_key_id=new_key_id,
            rotated_at=rotated_at,
            dual_trust_expires_at=dual_trust_expires_at,
            manifest_log_index=-1,
            rotation_sig="",
        )
        return RotationResult(
            new_private_key=new_priv,
            new_private_key_b64=new_priv_b64,
            new_manifest=new_manifest,
            manifest_log_entry=None,
            rotation_log_entry=rotation_log_entry,
            rotation_tl_entry=None,
        )

    # 5. Submit updated manifest to TL
    tl = make_transparency_log()
    manifest_log_entry = tl.submit(manifest_to_dict(new_manifest))

    # 6. Build and sign KeyRotationLogEntry (signed by retiring key)
    rotation_log_entry = KeyRotationLogEntry(
        event_type="key_rotation",
        entity_uri=entity_uri,
        old_key_id=old_key_id,
        new_key_id=new_key_id,
        rotated_at=rotated_at,
        dual_trust_expires_at=dual_trust_expires_at,
        manifest_log_index=manifest_log_entry.log_index,
        rotation_sig="",
    )
    rotation_log_entry.rotation_sig = sign_key_rotation_entry(rotation_log_entry, old_private_key)

    # 7. Submit KeyRotationLogEntry to TL
    rotation_entry_dict = {
        "dual_trust_expires_at": rotation_log_entry.dual_trust_expires_at,
        "entity_uri": rotation_log_entry.entity_uri,
        "event_type": rotation_log_entry.event_type,
        "manifest_log_index": rotation_log_entry.manifest_log_index,
        "new_key_id": rotation_log_entry.new_key_id,
        "old_key_id": rotation_log_entry.old_key_id,
        "rotated_at": rotation_log_entry.rotated_at,
        "rotation_sig": rotation_log_entry.rotation_sig,
    }
    rotation_tl_entry = tl.submit(rotation_entry_dict)

    return RotationResult(
        new_private_key=new_priv,
        new_private_key_b64=new_priv_b64,
        new_manifest=new_manifest,
        manifest_log_entry=manifest_log_entry,
        rotation_log_entry=rotation_log_entry,
        rotation_tl_entry=rotation_tl_entry,
    )
