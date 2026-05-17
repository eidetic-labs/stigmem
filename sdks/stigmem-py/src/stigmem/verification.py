"""Client-side integrity verification helpers for Stigmem responses."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .models import Fact, FactChainCheckpointProof, FactChainProof

_HASH_PREFIX = "sha256:"


class StigmemVerificationError(ValueError):
    """Raised when local verification rejects Stigmem proof material."""


def _encoded_value_v(fact: Fact) -> str:
    if fact.value.type == "null":
        return "null"
    if fact.value.type == "boolean":
        return "true" if fact.value.v else "false"
    return "" if fact.value.v is None else str(fact.value.v)


def compute_fact_cid(fact: Fact) -> str:
    """Compute the canonical CID for a fact body."""
    body: dict[str, Any] = {
        "confidence": fact.confidence,
        "entity": fact.entity,
        "relation": fact.relation,
        "scope": fact.scope,
        "source": fact.source,
        "value_type": fact.value.type,
        "value_v": _encoded_value_v(fact),
    }
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return f"{_HASH_PREFIX}{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


def verify_fact_cid(fact: Fact) -> str:
    """Verify a fact's stored CID and return the computed CID.

    Legacy responses may omit ``cid``; those cannot be independently verified and are
    accepted by this helper for backward compatibility.
    """
    computed = compute_fact_cid(fact)
    if fact.cid is not None and fact.cid != computed:
        raise StigmemVerificationError(
            f"CID mismatch for fact {fact.id}: stored={fact.cid!r}, computed={computed!r}"
        )
    return computed


def _sha256_json(body: dict[str, Any]) -> str:
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _checkpoint_payload(checkpoint: FactChainCheckpointProof) -> dict[str, Any]:
    return {
        "chain_hash": checkpoint.chain_hash,
        "covered_chain_seq": checkpoint.covered_chain_seq,
        "created_at": checkpoint.created_at,
        "kind": "stigmem.fact_chain_checkpoint",
        "tenant_id": checkpoint.tenant_id,
        "version": 1,
    }


def verify_checkpoint_proof(checkpoint: FactChainCheckpointProof) -> None:
    """Verify deterministic checkpoint proof material available to the SDK.

    Local transparency-log checkpoints include the submitted payload in ``tl_raw``.
    For Rekor-backed checkpoints, this validates mandatory inclusion metadata shape;
    cryptographic Rekor STH verification remains a node/operator concern because it
    requires Rekor log material and trust roots.
    """
    if checkpoint.status != "submitted":
        raise StigmemVerificationError(
            f"checkpoint {checkpoint.id} is not submitted: {checkpoint.status}"
        )
    if not checkpoint.tl_leaf_hash:
        raise StigmemVerificationError(f"checkpoint {checkpoint.id} is missing tl_leaf_hash")
    if checkpoint.tl_log_index is None:
        raise StigmemVerificationError(f"checkpoint {checkpoint.id} is missing tl_log_index")

    raw_payload = checkpoint.tl_raw.get("payload")
    if isinstance(raw_payload, dict):
        expected_leaf_hash = _sha256_json(raw_payload)
        if checkpoint.tl_leaf_hash != expected_leaf_hash:
            raise StigmemVerificationError(
                f"checkpoint {checkpoint.id} leaf hash mismatch: "
                f"stored={checkpoint.tl_leaf_hash!r}, computed={expected_leaf_hash!r}"
            )
        expected_payload = _checkpoint_payload(checkpoint)
        if raw_payload != expected_payload:
            raise StigmemVerificationError(
                f"checkpoint {checkpoint.id} payload does not match chain head metadata"
            )


def verify_fact_chain_proof(
    proof: FactChainProof | None,
    *,
    require_checkpoint: bool = False,
) -> None:
    """Verify compact fact-chain proof metadata returned by ``Stigmem-Verify: full``."""
    if proof is None:
        raise StigmemVerificationError("missing fact-chain proof")
    if proof.checked_entries < 0:
        raise StigmemVerificationError("fact-chain proof has negative checked_entries")
    if proof.checked_entries > 0 and not proof.head_hash:
        raise StigmemVerificationError("fact-chain proof is missing head_hash")

    checkpoint = proof.checkpoint
    if checkpoint is None:
        if require_checkpoint:
            raise StigmemVerificationError("fact-chain proof is missing checkpoint metadata")
        return

    if checkpoint.tenant_id != proof.tenant_id:
        raise StigmemVerificationError("checkpoint tenant does not match fact-chain proof")
    if proof.head_hash is not None and checkpoint.chain_hash != proof.head_hash:
        raise StigmemVerificationError("checkpoint chain_hash does not match proof head_hash")
    if checkpoint.covered_chain_seq > proof.checked_entries:
        raise StigmemVerificationError("checkpoint covers more entries than the verified chain")
    verify_checkpoint_proof(checkpoint)
