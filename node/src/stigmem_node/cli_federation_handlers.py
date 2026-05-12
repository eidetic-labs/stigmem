"""Federation cursor CLI handlers extracted from cli.py.

These handlers are imported back into ``stigmem_node.cli`` so the public
import surface is preserved.  No behavioural changes — code was moved
verbatim from cli.py.
"""

from __future__ import annotations

import argparse
import sys


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

            peer_row = conn.execute("SELECT id FROM peers WHERE id = ?", (peer_id,)).fetchone()
            if peer_row is None:
                print(
                    f"warning: peer {peer_id!r} ({entry.get('peer_node_id', '?')}) "
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
                        f"info: cursor for peer {entry.get('peer_node_id', '?')} "
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
