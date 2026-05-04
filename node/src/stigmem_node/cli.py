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


def _cmd_federation_cursor_export(args: argparse.Namespace) -> int:
    """Export replication cursor state to a portable JSON checkpoint.

    Reads every row from replication_cursors (joined to peers for human-readable
    node_id / node_url context) and writes a checkpoint file.  The checkpoint can
    be used with ``cursor-import`` to restore cursor positions after a DB loss so
    that the node re-pulls only the facts it missed rather than re-pulling
    everything from the beginning of time.

    See stigmem/docs/cursor-reset-recovery.md for the full recovery procedure.
    """
    import json
    import sqlite3
    from datetime import UTC, datetime

    from .db import apply_migrations
    from .settings import settings

    db_path: str = args.db or settings.db_path
    apply_migrations(db_path=db_path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        rows = conn.execute(
            """
            SELECT rc.peer_id, rc.direction, rc.cursor, rc.updated_at,
                   p.node_id, p.node_url, p.status AS peer_status
            FROM replication_cursors rc
            JOIN peers p ON p.id = rc.peer_id
            ORDER BY p.node_id, rc.direction
            """
        ).fetchall()
    finally:
        conn.close()

    checkpoint = {
        "checkpoint_timestamp": datetime.now(UTC).isoformat(),
        "db_path": db_path,
        "cursors": [
            {
                "peer_id": r["peer_id"],
                "peer_node_id": r["node_id"],
                "peer_url": r["node_url"],
                "peer_status": r["peer_status"],
                "direction": r["direction"],
                "cursor": r["cursor"],
                "updated_at": r["updated_at"],
            }
            for r in rows
        ],
    }

    payload = json.dumps(checkpoint, indent=2)

    if args.out == "-":
        print(payload)
    else:
        with open(args.out, "w") as fh:
            fh.write(payload)
            fh.write("\n")
        print(f"checkpoint written: {args.out} ({len(rows)} cursor(s))", file=sys.stderr)

    return 0


def _cmd_federation_cursor_import(args: argparse.Namespace) -> int:
    """Restore replication cursors from a checkpoint file after DB loss.

    For each entry in the checkpoint:
    - Skips entries whose peer_id is not present in the peers table (FK would
      fail; the peer may not yet be re-registered after a DB restore).
    - Upserts the cursor using ON CONFLICT so the command is idempotent and safe
      to re-run.
    - With --force, overwrites cursors that are newer than the checkpoint entry.
      Without --force (default), skips entries where the existing cursor is already
      set to a value (conservative: do not overwrite live state).

    After import, the next pull cycle will resume from the restored positions
    rather than re-pulling from the start of time.

    See stigmem/docs/cursor-reset-recovery.md for the full recovery procedure.
    """
    import json
    import sqlite3
    from datetime import UTC, datetime

    from .db import apply_migrations
    from .settings import settings

    db_path: str = args.db or settings.db_path
    apply_migrations(db_path=db_path)

    try:
        with open(args.checkpoint_file) as fh:
            checkpoint = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: cannot read checkpoint file: {exc}", file=sys.stderr)
        return 1

    cursors = checkpoint.get("cursors")
    if not isinstance(cursors, list):
        print("error: checkpoint missing 'cursors' array", file=sys.stderr)
        return 1

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")

    imported = skipped_no_peer = skipped_exists = 0
    now_iso = datetime.now(UTC).isoformat()

    try:
        for entry in cursors:
            peer_id = entry.get("peer_id")
            direction = entry.get("direction")
            cursor_val = entry.get("cursor")

            if not peer_id or not direction:
                print(
                    f"warning: skipping malformed entry: {entry}",
                    file=sys.stderr,
                )
                continue

            peer_row = conn.execute(
                "SELECT id FROM peers WHERE id = ?", (peer_id,)
            ).fetchone()
            if peer_row is None:
                print(
                    f"warning: peer {peer_id!r} ({entry.get('peer_node_id','?')}) "
                    "not found in peers table — skipping (re-register the peer first)",
                    file=sys.stderr,
                )
                skipped_no_peer += 1
                continue

            if not args.force:
                existing = conn.execute(
                    "SELECT cursor FROM replication_cursors WHERE peer_id = ? AND direction = ?",
                    (peer_id, direction),
                ).fetchone()
                if existing is not None and existing["cursor"] is not None:
                    print(
                        f"info: cursor for peer {entry.get('peer_node_id','?')} "
                        f"({direction}) already set — skipping (use --force to overwrite)",
                        file=sys.stderr,
                    )
                    skipped_exists += 1
                    continue

            conn.execute(
                """INSERT INTO replication_cursors (peer_id, direction, cursor, updated_at)
                   VALUES (?, ?, ?, ?)
                   ON CONFLICT(peer_id, direction)
                   DO UPDATE SET cursor = excluded.cursor, updated_at = excluded.updated_at""",
                (peer_id, direction, cursor_val, now_iso),
            )
            imported += 1

        conn.commit()
    except Exception:
        conn.rollback()
        conn.close()
        raise
    finally:
        conn.close()

    print(
        f"cursor import complete: {imported} restored, "
        f"{skipped_no_peer} skipped (peer not found), "
        f"{skipped_exists} skipped (already set)",
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


def _cmd_snapshot_create(args: argparse.Namespace) -> int:
    """Create a signed, content-addressed snapshot tarball."""
    from pathlib import Path

    from .db import apply_migrations
    from .settings import settings
    from .snapshot import snapshot_create

    db_path: str = args.db or settings.db_path
    apply_migrations(db_path=db_path)

    out_path = Path(args.out) if args.out else None
    sign_with = Path(args.sign_with) if args.sign_with else None

    result = snapshot_create(db_path=db_path, out_path=out_path, sign_with_key_path=sign_with)
    print(f"snapshot created: {result}", file=sys.stderr)
    return 0


def _cmd_snapshot_restore(args: argparse.Namespace) -> int:
    """Verify and restore a snapshot tarball."""
    from pathlib import Path

    from .settings import settings
    from .snapshot import SnapshotVerificationError, snapshot_restore

    db_path: str = args.db or settings.db_path
    from_path = Path(args.from_path)
    trusted_keys = Path(args.trusted_keys) if args.trusted_keys else None

    try:
        snapshot_restore(
            tarball_path=from_path,
            db_path=db_path,
            trusted_keys_path=trusted_keys,
            force_unverified=args.force_unverified,
        )
    except SnapshotVerificationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"snapshot restored to {db_path}", file=sys.stderr)
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

    # ------------------------------------------------------------------ federation cursor-export
    ce_p = fed_sub.add_parser(
        "cursor-export",
        help="export replication cursor positions to a JSON checkpoint file",
    )
    ce_p.add_argument(
        "--out",
        default="-",
        metavar="FILE",
        help='output file path (default: stdout, use "-" for stdout)',
    )
    ce_p.add_argument(
        "--db",
        metavar="PATH",
        default=None,
        help="path to stigmem.db (default: STIGMEM_DB_PATH env or settings default)",
    )
    ce_p.set_defaults(func=_cmd_federation_cursor_export)

    # ------------------------------------------------------------------ federation cursor-import
    ci_p = fed_sub.add_parser(
        "cursor-import",
        help="restore replication cursors from a checkpoint file after DB loss",
    )
    ci_p.add_argument(
        "checkpoint_file",
        metavar="FILE",
        help="path to checkpoint JSON produced by cursor-export",
    )
    ci_p.add_argument(
        "--force",
        action="store_true",
        help="overwrite cursors that are already set (default: skip existing non-null cursors)",
    )
    ci_p.add_argument(
        "--db",
        metavar="PATH",
        default=None,
        help="path to stigmem.db (default: STIGMEM_DB_PATH env or settings default)",
    )
    ci_p.set_defaults(func=_cmd_federation_cursor_import)

    # ------------------------------------------------------------------ snapshot
    snap_p = sub.add_parser("snapshot", help="backup/restore with signed manifests (Phase 8)")
    snap_sub = snap_p.add_subparsers(dest="snap_command", metavar="SUBCOMMAND")
    snap_sub.required = True

    sc_p = snap_sub.add_parser(
        "create",
        help="create a signed, content-addressed snapshot tarball",
    )
    sc_p.add_argument(
        "--out",
        metavar="PATH",
        default=None,
        help="output path for the .tar.gz (default: auto-named stigmem-snapshot-<ts>-<hash>.tar.gz)",
    )
    sc_p.add_argument(
        "--sign-with",
        dest="sign_with",
        metavar="KEY_FILE",
        default=None,
        help="path to a file containing a raw base64url Ed25519 private key (32 bytes); "
        "default: use the node's built-in federation key",
    )
    sc_p.add_argument(
        "--db",
        metavar="PATH",
        default=None,
        help="path to stigmem.db (default: STIGMEM_DB_PATH env or settings default)",
    )
    sc_p.set_defaults(func=_cmd_snapshot_create)

    sr_p = snap_sub.add_parser(
        "restore",
        help="verify signature + hashes and restore a snapshot tarball",
    )
    sr_p.add_argument(
        "--from",
        dest="from_path",
        metavar="PATH",
        required=True,
        help="path to the .tar.gz snapshot to restore",
    )
    sr_p.add_argument(
        "--trusted-keys",
        dest="trusted_keys",
        metavar="PATH",
        default=None,
        help="JSON file listing trusted base64url Ed25519 public keys; "
        "default: only the local node's own key",
    )
    sr_p.add_argument(
        "--force-unverified",
        dest="force_unverified",
        action="store_true",
        help="restore even if signature or hash verification fails (logged loudly; NOT recommended)",
    )
    sr_p.add_argument(
        "--db",
        metavar="PATH",
        default=None,
        help="destination database path (default: STIGMEM_DB_PATH env or settings default)",
    )
    sr_p.set_defaults(func=_cmd_snapshot_restore)

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
