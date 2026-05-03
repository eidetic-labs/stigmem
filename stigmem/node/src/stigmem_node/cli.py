"""Stigmem reference node CLI — spec §2.6.6."""

from __future__ import annotations

import argparse
import sys


def _cmd_decay_sweep(args: argparse.Namespace) -> int:
    from .db import apply_migrations
    from .decay import run_decay_sweep
    from .settings import settings

    db_path: str = args.db or settings.db_path
    apply_migrations(db_path=db_path)

    result = run_decay_sweep(
        ttl_seconds=args.ttl_seconds,
        min_confidence=args.min_confidence,
        scope=args.scope or None,
        dry_run=args.dry_run,
    )

    if args.dry_run:
        print(f"[dry-run] {result['scanned']} facts would be decayed", file=sys.stderr)
    else:
        print(f"{result['decayed']} facts decayed ({result['scanned']} scanned)", file=sys.stderr)
    return 0


def _cmd_migrate_normalize_entities(args: argparse.Namespace) -> int:
    from .db import apply_migrations
    from .migrate import normalize_entities_sweep
    from .settings import settings

    db_path: str = args.db or settings.db_path
    apply_migrations(db_path=db_path)

    registered, already_present = normalize_entities_sweep(db_path, dry_run=args.dry_run)

    if args.dry_run:
        print(
            f"[dry-run] {registered} aliases would be registered",
            file=sys.stderr,
        )
    else:
        print(
            f"{registered} aliases registered, {already_present} already present",
            file=sys.stderr,
        )
    return 0


def _cmd_federation_register_peer(args: argparse.Namespace) -> int:
    """Register this node as a peer with a remote node (spec §6.1).

    Fetches local /.well-known/stigmem, signs the PeerDeclaration with the
    local Ed25519 private key, and POSTs to the remote node's
    /v1/federation/peers endpoint.
    """
    import base64
    import json
    from datetime import UTC, datetime

    import httpx

    from .db import apply_migrations
    from .settings import settings

    # Ensure migrations are applied so keypair tables exist.
    apply_migrations()

    # Resolve local node URL: explicit flag > settings.
    local_url = (args.local_url or settings.node_url).rstrip("/")
    remote_url = args.remote_url.rstrip("/")
    allowed_scopes: list[str] = [s.strip() for s in args.scopes.split(",") if s.strip()]

    # ------------------------------------------------------------------
    # 1. Fetch local /.well-known/stigmem to get our published metadata.
    # ------------------------------------------------------------------
    try:
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
    from .peer_token import init_federation_keys

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
        headers["X-API-Key"] = args.api_key

    try:
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


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="stigmem",
        description="Stigmem reference node CLI",
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True

    # ------------------------------------------------------------------ migrate
    migrate_p = sub.add_parser("migrate", help="database migration utilities")
    migrate_sub = migrate_p.add_subparsers(dest="migrate_command", metavar="SUBCOMMAND")
    migrate_sub.required = True

    ne_p = migrate_sub.add_parser(
        "normalize-entities",
        help="populate entity_aliases from non-canonical entity/source URIs in facts (spec §2.6.6)",
    )
    ne_p.add_argument(
        "--dry-run",
        action="store_true",
        help="print aliases without inserting",
    )
    ne_p.add_argument(
        "--db",
        metavar="PATH",
        default=None,
        help="path to stigmem.db (default: STIGMEM_DB_PATH env or settings default)",
    )
    ne_p.set_defaults(func=_cmd_migrate_normalize_entities)

    # ------------------------------------------------------------------ federation
    fed_p = sub.add_parser("federation", help="federation management (spec §6)")
    fed_sub = fed_p.add_subparsers(dest="fed_command", metavar="SUBCOMMAND")
    fed_sub.required = True

    rp_p = fed_sub.add_parser(
        "register-peer",
        help="register this node as a peer with a remote node (spec §6.1)",
    )
    rp_p.add_argument(
        "--remote-url",
        required=True,
        metavar="URL",
        help="base URL of the remote node (e.g. http://node-b:8765)",
    )
    rp_p.add_argument(
        "--local-url",
        default=None,
        metavar="URL",
        help="base URL of this node as seen by the remote (default: STIGMEM_NODE_URL)",
    )
    rp_p.add_argument(
        "--scopes",
        default="company,public",
        metavar="SCOPE[,SCOPE]",
        help='comma-separated scopes to share (default: "company,public")',
    )
    rp_p.add_argument(
        "--api-key",
        default=None,
        metavar="KEY",
        help="API key for the remote node (required when remote auth_required=true)",
    )
    rp_p.set_defaults(func=_cmd_federation_register_peer)

    # ------------------------------------------------------------------ decay
    decay_p = sub.add_parser("decay", help="decay sweeper — expire stale facts (Phase 6)")
    decay_sub = decay_p.add_subparsers(dest="decay_command", metavar="SUBCOMMAND")
    decay_sub.required = True

    sw_p = decay_sub.add_parser(
        "sweep",
        help="mark non-expiring or low-confidence facts as expired",
    )
    sw_p.add_argument(
        "--ttl-seconds",
        dest="ttl_seconds",
        type=int,
        default=None,
        metavar="N",
        help="expire non-expiring facts older than N seconds (0 = expire all)",
    )
    sw_p.add_argument(
        "--min-confidence",
        dest="min_confidence",
        type=float,
        default=None,
        metavar="F",
        help="expire active facts with confidence below F (0.0–1.0)",
    )
    sw_p.add_argument(
        "--scope",
        default="",
        metavar="SCOPE",
        help="restrict sweep to one scope (local/team/company/public)",
    )
    sw_p.add_argument(
        "--dry-run",
        action="store_true",
        help="print what would be decayed without writing",
    )
    sw_p.add_argument(
        "--db",
        metavar="PATH",
        default=None,
        help="path to stigmem.db (default: STIGMEM_DB_PATH env or settings default)",
    )
    sw_p.set_defaults(func=_cmd_decay_sweep)

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
