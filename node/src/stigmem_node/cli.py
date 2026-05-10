"""Stigmem reference node CLI — spec §2.6.6."""

from __future__ import annotations

import argparse
import logging
import sys

logger = logging.getLogger("stigmem.cli")


def _cmd_capability_issue(args: argparse.Namespace) -> int:
    """Issue a capability token via the local node HTTP API."""
    import json

    import httpx

    payload = {
        "issuer": args.issuer,
        "subject": args.subject,
        "verb": args.verb,
        "object": args.object,
    }
    if args.ttl_seconds is not None:
        payload["ttl_seconds"] = args.ttl_seconds

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if args.api_key:
        headers["Authorization"] = f"Bearer {args.api_key}"

    try:
        resp = httpx.post(
            f"{args.node_url.rstrip('/')}/v1/federation/capability-tokens",
            json=payload,
            headers=headers,
            timeout=15.0,
        )
    except Exception as exc:
        print(f"error: cannot reach node at {args.node_url}: {exc}", file=sys.stderr)
        return 1

    if resp.status_code == 201:
        data = resp.json()
        if args.json:
            print(json.dumps(data, indent=2))
        else:
            print(f"token_id:  {data['token_id']}")
            print(f"issuer:    {data['issuer']}")
            print(f"subject:   {data['subject']}")
            print(f"verb:      {data['verb']}")
            print(f"object:    {data['object']}")
            print(f"expiry:    {data['expiry']}")
            print(f"token_json: {data['token_json']}")
        return 0

    print(f"error: {resp.status_code}: {resp.text}", file=sys.stderr)
    return 1


def _cmd_capability_verify(args: argparse.Namespace) -> int:
    """Verify a capability token via the local node HTTP API."""
    import json

    import httpx

    token_json_str = args.token_json
    if token_json_str == "-":  # nosec B105 — "-" is stdin sentinel, not a password
        token_json_str = sys.stdin.read().strip()

    headers: dict[str, str] = {}
    if args.api_key:
        headers["Authorization"] = f"Bearer {args.api_key}"

    try:
        resp = httpx.post(
            f"{args.node_url.rstrip('/')}/v1/federation/capability-tokens/verify",
            json={"token_json": token_json_str},
            headers=headers,
            timeout=15.0,
        )
    except Exception as exc:
        print(f"error: cannot reach node at {args.node_url}: {exc}", file=sys.stderr)
        return 1

    if resp.status_code == 200:
        data = resp.json()
        if args.json:
            print(json.dumps(data, indent=2))
        else:
            valid = data.get("valid", False)
            print(f"valid: {valid}")
            if not valid:
                print(f"reason: {data.get('reason', 'unknown')}")
        return 0

    # Treat 422/400 as invalid (not an HTTP error — the token itself is invalid)
    if resp.status_code in (422, 400):
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        print(f"invalid: {detail}", file=sys.stderr)
        return 1

    print(f"error: {resp.status_code}: {resp.text}", file=sys.stderr)
    return 1


def _cmd_capability_revoke(args: argparse.Namespace) -> int:
    """Revoke a capability token via the local node HTTP API."""
    import json

    import httpx

    payload: dict[str, str] = {}
    if args.reason:
        payload["reason"] = args.reason

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if args.api_key:
        headers["Authorization"] = f"Bearer {args.api_key}"

    try:
        resp = httpx.post(
            f"{args.node_url.rstrip('/')}/v1/federation/capability-tokens/{args.token_id}/revoke",
            json=payload,
            headers=headers,
            timeout=15.0,
        )
    except Exception as exc:
        print(f"error: cannot reach node at {args.node_url}: {exc}", file=sys.stderr)
        return 1

    if resp.status_code == 200:
        data = resp.json()
        if args.json:
            print(json.dumps(data, indent=2))
        else:
            print(f"revoked: {data['token_id']} at {data['revoked_at']}")
        return 0

    if resp.status_code == 404:
        print(f"error: token not found: {args.token_id}", file=sys.stderr)
        return 1
    if resp.status_code == 409:
        print(f"error: token already revoked: {args.token_id}", file=sys.stderr)
        return 1

    print(f"error: {resp.status_code}: {resp.text}", file=sys.stderr)
    return 1


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

    # ------------------------------------------------------------------ capability
    cap_p = sub.add_parser("capability", help="capability token management (spec §19.3)")
    cap_sub = cap_p.add_subparsers(dest="cap_command", metavar="SUBCOMMAND")
    cap_sub.required = True

    _cap_common = argparse.ArgumentParser(add_help=False)
    _cap_common.add_argument(
        "--node-url",
        dest="node_url",
        default="http://localhost:8765",
        metavar="URL",
        help="base URL of the local node (default: http://localhost:8765)",
    )
    _cap_common.add_argument(
        "--api-key",
        dest="api_key",
        default=None,
        metavar="KEY",
        help="API key for authentication",
    )
    _cap_common.add_argument(
        "--json",
        action="store_true",
        help="output raw JSON response",
    )

    # capability issue
    ci_p = cap_sub.add_parser(
        "issue",
        parents=[_cap_common],
        help="issue a new capability token",
    )
    ci_p.add_argument("--issuer", required=True, metavar="URI", help="issuer entity URI")
    ci_p.add_argument("--subject", required=True, metavar="URI", help="subject entity URI")
    ci_p.add_argument(
        "--verb",
        required=True,
        metavar="VERB",
        help="permission verb (e.g. read, write)",
    )
    ci_p.add_argument(
        "--object",
        required=True,
        metavar="OBJECT",
        help="object URI the token grants access to (e.g. stigmem://facts)",
    )
    ci_p.add_argument(
        "--ttl-seconds",
        dest="ttl_seconds",
        type=int,
        default=None,
        metavar="N",
        help="token lifetime in seconds (default: node default; max: 7776000 / 90 days)",
    )
    ci_p.set_defaults(func=_cmd_capability_issue)

    # capability verify
    cv_p = cap_sub.add_parser(
        "verify",
        parents=[_cap_common],
        help="verify a capability token",
    )
    cv_p.add_argument(
        "token_json",
        metavar="TOKEN_JSON",
        help="capability token JSON string; pass '-' to read from stdin",
    )
    cv_p.set_defaults(func=_cmd_capability_verify)

    # capability revoke
    cr_p = cap_sub.add_parser(
        "revoke",
        parents=[_cap_common],
        help="revoke a capability token by token_id",
    )
    cr_p.add_argument("token_id", metavar="TOKEN_ID", help="ID of the token to revoke")
    cr_p.add_argument(
        "--reason",
        default="",
        metavar="REASON",
        help="human-readable reason for revocation",
    )
    cr_p.set_defaults(func=_cmd_capability_revoke)

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
        help=(
            "output path for the .tar.gz "
            "(default: auto-named stigmem-snapshot-<ts>-<hash>.tar.gz)"
        ),
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
        help=(
            "restore even if signature or hash verification fails "
            "(logged loudly; NOT recommended)"
        ),
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

    # ------------------------------------------------------------------ instruction
    instr_p = sub.add_parser("instruction", help="instruction manifest tools (Phase 10 §21)")
    instr_sub = instr_p.add_subparsers(dest="instr_command", metavar="SUBCOMMAND")
    instr_sub.required = True

    im_p = instr_sub.add_parser("manifest", help="manage instruction manifests")
    im_sub = im_p.add_subparsers(dest="manifest_command", metavar="SUBCOMMAND")
    im_sub.required = True

    img_p = im_sub.add_parser(
        "generate",
        help="generate a manifest JSON from a directory of markdown instruction files",
    )
    img_p.add_argument(
        "path", metavar="PATH", help="directory containing markdown instruction files"
    )
    img_p.add_argument(
        "--agent-id",
        dest="agent_id",
        required=True,
        metavar="AGENT_ID",
        help="agent UUID to embed in generated fact_uri values",
    )
    img_p.add_argument(
        "--deployment",
        default="default",
        metavar="DEPLOYMENT",
        help="deployment namespace for instruction: URIs (default: default)",
    )
    img_p.add_argument(
        "--version",
        default="v1",
        metavar="VERSION",
        help="manifest version string (default: v1)",
    )
    img_p.add_argument(
        "--out",
        default=None,
        metavar="FILE",
        help="write JSON to FILE instead of stdout",
    )
    img_p.set_defaults(func=_cmd_instruction_manifest_generate)

    # instruction migrate
    imig_p = instr_sub.add_parser(
        "migrate",
        help="migrate markdown instruction files to stigmem facts + publish manifest",
    )
    imig_p.add_argument("path", metavar="PATH", help="markdown file or directory to migrate")
    scope_grp = imig_p.add_mutually_exclusive_group(required=True)
    scope_grp.add_argument(
        "--role", default=None, metavar="ROLE", help="agent role name (e.g. cto)"
    )
    scope_grp.add_argument(
        "--skill", default=None, metavar="SKILL", help="skill name (e.g. paperclip)"
    )
    imig_p.add_argument(
        "--agent-id",
        dest="agent_id",
        required=True,
        metavar="AGENT_ID",
        help="agent UUID owning the manifest",
    )
    imig_p.add_argument(
        "--deployment",
        default="default",
        metavar="DEPLOYMENT",
        help="deployment namespace (default: default)",
    )
    imig_p.add_argument(
        "--version",
        default="v1",
        metavar="VERSION",
        help="fact version string (default: v1)",
    )
    imig_p.add_argument(
        "--node-url",
        dest="node_url",
        default="http://127.0.0.1:8000",
        metavar="URL",
        help="stigmem node base URL (default: http://127.0.0.1:8000)",
    )
    imig_p.add_argument(
        "--api-key",
        dest="api_key",
        default=None,
        metavar="KEY",
        help="API key (or set STIGMEM_API_KEY env var)",
    )
    imig_p.add_argument(
        "--db",
        default=None,
        metavar="PATH",
        help="path to stigmem.db for local idempotency checks (skips HTTP fact queries)",
    )
    imig_p.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="show diff without writing any facts or manifest",
    )
    imig_p.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="skip confirmation prompt",
    )
    imig_p.set_defaults(func=_cmd_instruction_migrate)

    # ------------------------------------------------------------------ audit
    audit_p = sub.add_parser("audit", help="discovery audit reports (Phase 10 §21.5)")
    audit_sub = audit_p.add_subparsers(dest="audit_command", metavar="SUBCOMMAND")
    audit_sub.required = True

    ad_p = audit_sub.add_parser(
        "discovery",
        help="print discovery audit metrics: Recall@k, Hit@k, miss rate",
    )
    ad_p.add_argument(
        "--agent",
        required=True,
        metavar="AGENT_ID_OR_ROLE",
        help="agent ID (UUID) or role substring to filter",
    )
    ad_p.add_argument(
        "--since",
        default=None,
        metavar="DATE",
        help="ISO 8601 date/datetime to start from (default: 7 days ago)",
    )
    ad_p.add_argument(
        "--db",
        default=None,
        metavar="PATH",
        help="path to stigmem.db (default: STIGMEM_DB_PATH env or settings default)",
    )
    ad_p.add_argument("--json", action="store_true", help="output as JSON")
    ad_p.set_defaults(func=_cmd_audit_discovery)

    # ------------------------------------------------------------------ identity
    id_p = sub.add_parser("identity", help="node identity management (spec §22.2)")
    id_sub = id_p.add_subparsers(dest="identity_command", metavar="SUBCOMMAND")
    id_sub.required = True

    rk_p = id_sub.add_parser(
        "rotate-key",
        help="rotate the node or issuer Ed25519 key with a dual-trust window (§22.2)",
    )
    rk_p.add_argument(
        "--kind",
        choices=["node", "issuer"],
        required=True,
        metavar="KIND",
        help="key type to rotate: node (federation identity) or issuer (capability token signing)",
    )
    rk_p.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="generate artefacts and print new key without writing to TL or DB",
    )
    rk_p.add_argument(
        "--dual-trust-days",
        dest="dual_trust_days",
        type=int,
        default=90,
        metavar="DAYS",
        help="days the retiring key stays in accept_set (default: 90; must be ≥ 90)",
    )
    rk_p.add_argument(
        "--db",
        default=None,
        metavar="PATH",
        help="path to stigmem.db (default: STIGMEM_DB_PATH env or settings default)",
    )
    rk_p.set_defaults(func=_cmd_identity_rotate_key)

    # ------------------------------------------------------------------ backfill-cids
    bc_p = sub.add_parser(
        "backfill-cids",
        help="compute and persist CIDs for facts that pre-date Phase 13 (spec §25.6.3)",
    )
    bc_p.add_argument(
        "--db",
        dest="db",
        default=None,
        metavar="PATH",
        help="path to stigmem.db (default: STIGMEM_DB_PATH env or settings default)",
    )
    bc_p.add_argument(
        "--batch-size",
        dest="batch_size",
        type=int,
        default=500,
        metavar="N",
        help="facts to process per transaction (default: 500)",
    )
    bc_p.add_argument(
        "--quiet",
        action="store_true",
        help="suppress progress output",
    )
    bc_p.set_defaults(func=_cmd_backfill_cids)

    # ------------------------------------------------------------------ auth
    auth_p = sub.add_parser("auth", help="API key management (spec §3.5)")
    auth_sub = auth_p.add_subparsers(dest="auth_command", metavar="SUBCOMMAND")
    auth_sub.required = True

    # auth bootstrap-key
    bk_p = auth_sub.add_parser(
        "bootstrap-key",
        help=(
            "mint the first admin API key on a fresh install "
            "(refuses to run if the api_keys table is non-empty)"
        ),
    )
    bk_p.add_argument(
        "--entity-uri",
        dest="entity_uri",
        default="agent:admin",
        metavar="URI",
        help="entity URI to associate with the bootstrap key (default: agent:admin)",
    )
    bk_p.add_argument(
        "--permissions",
        dest="permissions",
        default="admin,write,read",
        metavar="LIST",
        help=(
            "comma-separated permissions for the bootstrap key "
            "(default: admin,write,read)"
        ),
    )
    bk_p.set_defaults(func=_cmd_auth_bootstrap_key)

    return parser


def _cmd_instruction_migrate(args: argparse.Namespace) -> int:
    """Migrate markdown instruction files to stigmem facts and publish manifest."""
    import os
    import time
    from pathlib import Path

    from .instruction_migrate import (
        compute_diff,
        format_preview,
        parse_instruction_chunks,
        publish_manifest,
        scope_prefix_for_role,
        scope_prefix_for_skill,
        write_facts,
    )

    path = Path(args.path)
    if not path.exists():
        print(f"error: path '{args.path}' does not exist", file=sys.stderr)
        return 1

    api_key = args.api_key or os.environ.get("STIGMEM_API_KEY", "")
    node_url = args.node_url
    deployment = args.deployment
    version = args.version
    agent_id = args.agent_id

    # Build scope prefix and label
    if args.role:
        scope_prefix = scope_prefix_for_role(deployment, agent_id)
        scope_label = f"role:{args.role}  agent:{agent_id}"
    else:
        scope_prefix = scope_prefix_for_skill(deployment, args.skill)
        scope_label = f"skill:{args.skill}  agent:{agent_id}"

    # Parse
    chunks = parse_instruction_chunks(path)
    if not chunks:
        print(
            "No instruction chunks found. Check that the path contains .md files.",
            file=sys.stderr,
        )
        return 0

    # Load existing state for idempotency checks
    # Initial diff pass to know which URIs to query
    from .instruction_migrate import build_fact_uri
    stub_diff_uris = {build_fact_uri(scope_prefix, c.slug, version) for c in chunks}
    existing_content: dict[str, str] = {}
    prev_names: set[str] = set()

    if args.db:
        # We need DiffEntry stubs for the DB loader — use dict approach
        import sqlite3
        try:
            conn = sqlite3.connect(args.db)
            conn.row_factory = sqlite3.Row
            for uri in stub_diff_uris:
                row = conn.execute(
                    "SELECT value_v FROM facts WHERE entity = ? ORDER BY timestamp DESC LIMIT 1",
                    (uri,),
                ).fetchone()
                if row:
                    existing_content[uri] = str(row["value_v"])
            # Previous manifest names
            row = conn.execute(
                "SELECT body FROM instruction_manifests"
                " WHERE agent_id = ? AND superseded_at IS NULL"
                " ORDER BY created_at DESC LIMIT 1",
                (agent_id,),
            ).fetchone()
            if row:
                import json as _json
                prev_names = {e["name"] for e in _json.loads(row["body"])}
            conn.close()
        except Exception as exc:
            print(f"warning: db query failed: {exc}", file=sys.stderr)
    elif api_key:
        try:
            import httpx
            import httpx as _httpx  # noqa: F401
            headers = {"Authorization": f"Bearer {api_key}"}
            base = node_url.rstrip("/")
            for uri in stub_diff_uris:
                try:
                    r = httpx.get(
                        f"{base}/v1/facts",
                        params={"entity": uri, "limit": 1},
                        headers=headers,
                        timeout=10.0,
                    )
                    if r.status_code == 200:
                        facts = r.json().get("facts", [])
                        if facts:
                            existing_content[uri] = str(facts[0]["value"]["v"])
                except Exception as exc:  # nosec B110 — best-effort pre-flight
                    logger.debug("instruction migrate pre-flight fact fetch failed: %s", exc)
            try:
                r = httpx.get(
                    f"{base}/v1/agents/{agent_id}/instruction-manifest",
                    headers=headers,
                    timeout=10.0,
                )
                if r.status_code == 200:
                    prev_names = {e["name"] for e in r.json().get("entries", [])}
            except Exception as exc:  # nosec B110 — best-effort pre-flight
                logger.debug("instruction migrate pre-flight manifest fetch failed: %s", exc)
        except ImportError:
            print("warning: httpx not installed — skipping idempotency checks", file=sys.stderr)

    # Compute diff
    diff = compute_diff(chunks, scope_prefix, version, existing_content, prev_names)

    # Show preview
    print(format_preview(diff, scope_label, path, version))

    if args.dry_run:
        print("Dry-run mode — no changes written.")
        return 0

    creates = [d for d in diff if d.action == "CREATE"]
    updates = [d for d in diff if d.action == "UPDATE"]
    tombstones = [d for d in diff if d.action == "TOMBSTONE"]

    if not creates and not updates and not tombstones:
        print("Nothing to do.")
        return 0

    if not args.yes:
        try:
            answer = input("Proceed? [y/N] ")
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            return 1
        if answer.lower() not in ("y", "yes"):
            print("Aborted.")
            return 1

    if not api_key:
        print(
            "error: --api-key or STIGMEM_API_KEY env var required to write facts",
            file=sys.stderr,
        )
        return 1

    # Write facts
    written, failed = write_facts(diff, node_url, api_key)
    if failed > 0:
        print(
            f"\n{failed} fact(s) failed to write. Manifest will NOT be published.",
            file=sys.stderr,
        )
        return 1

    # Publish manifest with a unique version per run (timestamp suffix)
    manifest_version = f"{version}-{int(time.time())}"
    ok = publish_manifest(agent_id, diff, manifest_version, node_url, api_key)
    if not ok:
        return 1

    print(f"\nDone. {written} fact(s) written, manifest published as version '{manifest_version}'.")
    print(f"Verify: stigmem recall-instruction via POST /v1/agents/{agent_id}/recall-instruction")
    return 0


def _cmd_instruction_manifest_generate(args: argparse.Namespace) -> int:
    """Generate an instruction manifest JSON from a directory of markdown files."""
    import json
    import re
    from pathlib import Path

    path = Path(args.path)
    if not path.is_dir():
        print(f"error: '{args.path}' is not a directory", file=sys.stderr)
        return 1

    entries = []
    md_files = sorted(path.glob("*.md")) + sorted(path.glob("**/*.md"))

    for md_file in md_files:
        try:
            text = md_file.read_text(encoding="utf-8")
        except Exception as exc:
            print(f"warning: skipping {md_file}: {exc}", file=sys.stderr)
            continue

        # Split at H2/H3 boundaries
        sections = re.split(r"(?m)^(#{2,3}\s+.+)$", text)

        # Merge heading with following content
        chunks: list[tuple[str, str]] = []
        i = 0
        while i < len(sections):
            if re.match(r"^#{2,3}\s+", sections[i].strip()):
                heading = sections[i].strip()
                body = sections[i + 1].strip() if i + 1 < len(sections) else ""
                chunks.append((heading, body))
                i += 2
            else:
                if sections[i].strip():
                    chunks.append(
                        ("# " + md_file.stem.replace("-", " ").title(), sections[i].strip())
                    )
                i += 1

        if not chunks:
            chunks = [("# " + md_file.stem.replace("-", " ").title(), text.strip())]

        for heading, body in chunks:
            heading_text = re.sub(r"^#{2,3}\s+", "", heading).strip()
            slug = re.sub(r"[^a-z0-9]+", "-", heading_text.lower()).strip("-")
            if not slug:
                slug = md_file.stem
            unit_name = f"{md_file.stem}-{slug}" if md_file.stem not in slug else slug

            keywords = list(
                {
                    w.lower()
                    for w in re.findall(
                        r"\b[a-zA-Z]{4,}\b", heading_text + " " + body[:200]
                    )
                }
            )[:8]
            token_est = max(1, len(body) // 4)
            fact_uri = (
                f"instruction:{args.deployment}/agent/{args.agent_id}"
                f"/{unit_name}/{args.version}"
            )

            entries.append({
                "name": unit_name,
                "description": heading_text[:120],
                "required_by_task_types": [],
                "guarantee_load": False,
                "load_triggers": {
                    "intents": [heading_text.lower()],
                    "keywords": keywords,
                    "task_types": [],
                },
                "fact_uri": fact_uri,
                "path": str(md_file),
                "token_estimate": token_est,
            })

    result = {
        "version": args.version,
        "agent_id": args.agent_id,
        "deployment": args.deployment,
        "generated_from": str(path),
        "entries": entries,
    }
    output = json.dumps(result, indent=2)

    if args.out:
        with open(args.out, "w") as f:
            f.write(output)
        print(f"Wrote {len(entries)} entries to {args.out}")
    else:
        print(output)

    return 0


def _cmd_audit_discovery(args: argparse.Namespace) -> int:
    """Print discovery audit metrics from the local database."""
    import json
    import sqlite3
    from datetime import UTC, datetime, timedelta

    from .settings import settings

    db_path = args.db or settings.db_path

    if args.since:
        try:
            since_dt = datetime.fromisoformat(args.since.replace("Z", "+00:00"))
        except ValueError:
            print(f"error: invalid --since date: {args.since}", file=sys.stderr)
            return 1
    else:
        since_dt = datetime.now(UTC) - timedelta(days=7)
    since_ms = int(since_dt.timestamp() * 1000)

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
    except Exception as exc:
        print(f"error: cannot open database {db_path}: {exc}", file=sys.stderr)
        return 1

    agent_filter = args.agent
    rows = conn.execute(
        "SELECT * FROM instruction_audit WHERE agent_id LIKE ? AND session_start >= ?",
        (f"%{agent_filter}%", since_ms),
    ).fetchall()

    if not rows:
        print(f"No audit records found for agent '{agent_filter}' since {since_dt.date()}")
        return 0

    total = len(rows)
    recall_at_k_num: float = 0.0
    hit_at_k_num = 0
    total_used = 0
    total_missed = 0

    for row in rows:
        loaded = set(json.loads(row["loaded_chunks"]))
        used = json.loads(row["used_chunks"])
        missed = json.loads(row["missed_chunks"])
        used_set = set(used)
        missed_set = set(missed)

        if used_set:
            recall_at_k = len(used_set & loaded) / len(used_set)
            recall_at_k_num += recall_at_k
            if used_set & loaded:
                hit_at_k_num += 1

        total_used += len(used_set)
        total_missed += len(missed_set)

    recall_at_k_avg = recall_at_k_num / total if total > 0 else 0.0
    hit_at_k_avg = hit_at_k_num / total if total > 0 else 0.0
    miss_rate = (
        total_missed / (total_used + total_missed) if (total_used + total_missed) > 0 else 0.0
    )

    report = {
        "agent": agent_filter,
        "since": since_dt.isoformat(),
        "total_events": total,
        "recall_at_k": round(recall_at_k_avg, 4),
        "hit_at_k": round(hit_at_k_avg, 4),
        "miss_rate": round(miss_rate, 4),
    }

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"Discovery audit — agent: {agent_filter}  since: {since_dt.date()}")
        print(f"  Total events : {total}")
        print(f"  Recall@k     : {recall_at_k_avg:.1%}")
        print(f"  Hit@k        : {hit_at_k_avg:.1%}")
        print(f"  Miss rate    : {miss_rate:.1%}")
        if miss_rate > 0.15:
            print("  ALERT: miss_rate > 0.15 — manifest descriptions or triggers need review")

    conn.close()
    return 0


def _cmd_identity_rotate_key(args: argparse.Namespace) -> int:
    """Rotate the node or issuer Ed25519 key (spec §22.2).

    Generates a next-gen keypair, appends a rotation event to the manifest,
    submits updated manifest + KeyRotationLogEntry to the transparency log,
    and prints the new private key seed for injection into your secrets manager.

    The retiring key stays in the dual-trust accept_set for --dual-trust-days
    (default 90), covering all in-flight tokens signed under the old key.
    """
    import json as _json

    from .db import apply_migrations
    from .identity.capability import load_node_private_key
    from .identity.key_rotation import rotate_key
    from .identity.manifest import manifest_from_dict

    if args.db:
        import stigmem_node.settings as settings_module

        from .settings import Settings
        patched = Settings(db_path=args.db)
        settings_module.settings = patched

    from .settings import settings

    apply_migrations(db_path=settings.db_path)

    old_priv = load_node_private_key()
    if old_priv is None:
        print(
            "error: STIGMEM_NODE_PRIVATE_KEY is not configured — cannot rotate",
            file=sys.stderr,
        )
        return 1

    entity_uri = settings.node_url

    from .db import db as _db_ctx
    with _db_ctx() as conn:
        row = conn.execute(
            "SELECT manifest_json FROM federation_manifests WHERE entity_uri = ?",
            (entity_uri,),
        ).fetchone()

    if row is None:
        print(
            f"error: no manifest found for {entity_uri!r} in federation_manifests\n"
            "Publish a manifest first via PUT /v1/federation/manifest",
            file=sys.stderr,
        )
        return 1

    old_manifest = manifest_from_dict(_json.loads(row["manifest_json"]))

    try:
        result = rotate_key(
            entity_uri=entity_uri,
            old_manifest=old_manifest,
            old_private_key=old_priv,
            dual_trust_days=args.dual_trust_days,
            dry_run=args.dry_run,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    tag = "[DRY RUN] " if args.dry_run else ""
    print(f"{tag}Key rotation ({args.kind}) complete")
    print(f"  old key_id : {old_manifest.key_id}")
    print(f"  new key_id : {result.new_manifest.key_id}")
    print(f"  dual-trust : {result.rotation_log_entry.dual_trust_expires_at}")

    if not args.dry_run and result.manifest_log_entry and result.rotation_tl_entry:
        print(f"  manifest TL index  : {result.manifest_log_entry.log_index}")
        print(f"  rotation TL index  : {result.rotation_tl_entry.log_index}")

        from .identity.trust_store import store_peer_manifest
        store_peer_manifest(entity_uri, result.new_manifest, result.manifest_log_entry)
        print("  manifest stored in federation_manifests")

    print()
    print("ACTION REQUIRED — update your secrets manager with the new private key:")
    print(f"  STIGMEM_NODE_PRIVATE_KEY={result.new_private_key_b64}")
    print("Then restart the node.  Keep the old key value until the dual-trust window closes.")
    return 0


def _cmd_backfill_cids(args: argparse.Namespace) -> int:
    """Compute and persist CIDs for facts that pre-date Phase 13 (spec §25.6.3)."""
    import sqlite3 as _sqlite3

    from .cid import compute_cid as _compute_cid

    db_path: str | None = getattr(args, "db", None)
    if db_path is None:
        import os as _os
        db_path = _os.environ.get("STIGMEM_DB_PATH", "stigmem.db")

    batch_size: int = getattr(args, "batch_size", 500)
    quiet: bool = getattr(args, "quiet", False)

    conn = _sqlite3.connect(db_path)
    conn.row_factory = _sqlite3.Row

    total_updated = 0
    collision_skipped = 0

    while True:
        rows = conn.execute(
            "SELECT id, entity, relation, value_type, value_v, source, scope, confidence"
            " FROM facts WHERE cid IS NULL LIMIT ?",
            (batch_size,),
        ).fetchall()
        if not rows:
            break

        for row in rows:
            cid = _compute_cid(
                entity=row["entity"],
                relation=row["relation"],
                value_type=row["value_type"],
                value_v=row["value_v"] or "",
                source=row["source"],
                scope=row["scope"],
                confidence=float(row["confidence"]),
            )
            # Check for CID collision before writing
            existing = conn.execute(
                "SELECT fact_id FROM fact_cid_aliases WHERE cid = ?", (cid,)
            ).fetchone()
            if existing and existing["fact_id"] != row["id"]:
                collision_skipped += 1
                continue

            conn.execute("UPDATE facts SET cid = ? WHERE id = ?", (cid, row["id"]))
            conn.execute(
                "INSERT OR IGNORE INTO fact_cid_aliases (fact_id, cid) VALUES (?, ?)",
                (row["id"], cid),
            )

        conn.commit()
        total_updated += len(rows)
        if not quiet:
            print(f"backfill-cids: processed {total_updated} facts…", file=sys.stderr)

    conn.close()
    if not quiet:
        print(
            f"backfill-cids: done — {total_updated} facts updated"
            + (f", {collision_skipped} CID collisions skipped" if collision_skipped else ""),
            file=sys.stderr,
        )
    return 0


def _cmd_auth_bootstrap_key(args: argparse.Namespace) -> int:
    """Mint the first admin-scope API key on a fresh install.

    Refuses to run if the api_keys table is non-empty — bootstrap is
    one-shot. After bootstrap, additional keys must go through the
    `POST /v1/auth/keys` API authenticated with the bootstrap key
    (or any later admin key).
    """
    from .auth import create_api_key
    from .db import db

    with db() as conn:
        row = conn.execute("SELECT COUNT(*) FROM api_keys").fetchone()
        existing = int(row[0]) if row else 0

    if existing > 0:
        print(
            f"ERROR: api_keys table is not empty ({existing} row(s)). "
            "Bootstrap is one-shot.",
            file=sys.stderr,
        )
        print(
            "Mint additional keys via `POST /v1/auth/keys` "
            "authenticated with an existing admin key.",
            file=sys.stderr,
        )
        return 1

    permissions: list[str] = args.permissions.split(",") if args.permissions else ["admin", "write", "read"]
    expires_at = None  # never; mirrors create_api_key default

    raw_key = create_api_key(
        entity_uri=args.entity_uri,
        permissions=permissions,
        expires_at=expires_at,
    )

    # Print key to stdout (capture-able), informational to stderr.
    print(raw_key)
    print(
        f"# stigmem auth bootstrap-key: minted admin key for "
        f"entity={args.entity_uri!r} permissions={permissions!r}",
        file=sys.stderr,
    )
    print(
        "# Save the value above — you will not see it again. "
        "Use it as `Authorization: Bearer <key>` for all subsequent requests.",
        file=sys.stderr,
    )
    return 0


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
