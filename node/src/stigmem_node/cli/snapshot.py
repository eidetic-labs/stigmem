"""Snapshot CLI handlers."""

from __future__ import annotations

import argparse
import sys


def _cmd_snapshot_create(args: argparse.Namespace) -> int:
    """Create a signed, content-addressed snapshot tarball."""
    from pathlib import Path

    from ..db import apply_migrations
    from ..settings import settings
    from ..snapshot import snapshot_create

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

    from ..settings import settings
    from ..snapshot import SnapshotVerificationError, snapshot_restore

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
