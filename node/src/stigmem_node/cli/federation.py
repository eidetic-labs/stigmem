"""Federation CLI handlers."""

from __future__ import annotations

import argparse
import sys


def _cmd_federation_register_peer(args: argparse.Namespace) -> int:
    """Register this node as a peer with a remote node (Spec-05-Federation-Trust)."""
    import base64
    import json
    import ssl
    from datetime import UTC, datetime

    import httpx

    from ..db import apply_migrations
    from ..settings import settings

    # Ensure migrations are applied so keypair tables exist.
    apply_migrations()

    # Resolve local node URL: explicit flag > settings.
    local_url = (args.local_url or settings.node_url).rstrip("/")
    remote_url = args.remote_url.rstrip("/")
    allowed_scopes: list[str] = [s.strip() for s in args.scopes.split(",") if s.strip()]
    cert = (args.tls_cert, args.tls_key) if args.tls_cert and args.tls_key else None
    verify: ssl.SSLContext | str | bool | None = None
    if cert is not None:
        ssl_ctx = ssl.create_default_context(cafile=args.ca_bundle or None)
        ssl_ctx.load_cert_chain(*cert)
        verify = ssl_ctx
    elif args.ca_bundle:
        verify = args.ca_bundle

    # ------------------------------------------------------------------
    # 1. Fetch local /.well-known/stigmem to get our published metadata.
    # ------------------------------------------------------------------
    try:
        if verify is not None:
            with httpx.Client(timeout=15.0, trust_env=False, verify=verify) as client:
                wk = client.get(f"{local_url}/.well-known/stigmem")
        else:
            wk = httpx.get(f"{local_url}/.well-known/stigmem", timeout=10.0)
        wk.raise_for_status()
    except Exception as exc:
        print(f"error: cannot reach local node at {local_url}: {exc}", file=sys.stderr)
        return 1

    wk_data = wk.json()
    local_node_id: str = wk_data["node_id"]
    local_pubkey: str = wk_data.get("federation_pubkey", "")
    if not local_pubkey:
        print(
            "error: local node has no federation_pubkey in /.well-known/stigmem — "
            "set STIGMEM_FEDERATION_ENABLED=true and restart",
            file=sys.stderr,
        )
        return 1

    # ------------------------------------------------------------------
    # 2. Load local private key and sign the PeerDeclaration.
    # ------------------------------------------------------------------
    from ..federation.peer_token import init_federation_keys

    _, priv_b64 = init_federation_keys()

    def _pad(s: str) -> str:
        return s + "=" * (-len(s) % 4)

    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    priv_key = Ed25519PrivateKey.from_private_bytes(base64.urlsafe_b64decode(_pad(priv_b64)))

    signed_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    signed_fields: dict[str, object] = {
        "allowed_scopes": sorted(allowed_scopes),
        "federation_pubkey": local_pubkey,
        "node_id": local_node_id,
        "node_url": local_url,
        "signed_at": signed_at,
    }
    canonical = json.dumps(signed_fields, sort_keys=True, separators=(",", ":")).encode("utf-8")
    sig_bytes = priv_key.sign(canonical)
    declaration_sig = base64.urlsafe_b64encode(sig_bytes).decode().rstrip("=")

    # ------------------------------------------------------------------
    # 3. POST to the remote node.
    # ------------------------------------------------------------------
    payload = {
        "node_id": local_node_id,
        "node_url": local_url,
        "federation_pubkey": local_pubkey,
        "allowed_scopes": sorted(allowed_scopes),
        "signed_at": signed_at,
        "declaration_sig": declaration_sig,
    }

    headers = {"Content-Type": "application/json"}
    if args.api_key:
        headers["Authorization"] = f"Bearer {args.api_key}"

    try:
        if verify is not None:
            with httpx.Client(timeout=15.0, trust_env=False, verify=verify) as client:
                resp = client.post(
                    f"{remote_url}/v1/federation/peers",
                    json=payload,
                    headers=headers,
                )
        else:
            resp = httpx.post(
                f"{remote_url}/v1/federation/peers",
                json=payload,
                headers=headers,
                timeout=15.0,
            )
    except Exception as exc:
        print(f"error: cannot reach remote node at {remote_url}: {exc}", file=sys.stderr)
        return 1

    if resp.status_code in (200, 201):
        result = resp.json()
        peer_status = result.get("status", "unknown")
        peer_id = result.get("peer_id", "")
        if peer_status == "active":
            print(f"peer registered and verified (peer_id={peer_id})")
        else:
            print(
                f"peer registered but not yet active (status={peer_status}, peer_id={peer_id})\n"
                "Check that the remote node can reach this node's /.well-known/stigmem endpoint.",
                file=sys.stderr,
            )
            return 1
    elif resp.status_code == 409:
        print("peer already registered — nothing to do")
    else:
        print(
            f"error: remote node returned {resp.status_code}: {resp.text}",
            file=sys.stderr,
        )
        return 1

    return 0
