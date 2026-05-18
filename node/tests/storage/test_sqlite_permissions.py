"""SQLite file permission coverage for local database artifacts."""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from stigmem_node.db import _enforce_sqlite_owner_only_permissions, apply_migrations


@pytest.mark.skipif(os.name == "nt", reason="POSIX file modes are not available")
def test_apply_migrations_restricts_sqlite_artifact_permissions(tmp_path: Path) -> None:
    db_path = tmp_path / "permissions.db"

    apply_migrations(db_path=str(db_path))

    assert stat.S_IMODE(db_path.stat().st_mode) == 0o600


@pytest.mark.skipif(os.name == "nt", reason="POSIX file modes are not available")
def test_permission_helper_restricts_existing_sqlite_sidecars(tmp_path: Path) -> None:
    db_path = tmp_path / "permissions-sidecars.db"
    wal_path = Path(f"{db_path}-wal")
    shm_path = Path(f"{db_path}-shm")

    apply_migrations(db_path=str(db_path))
    for sidecar in (wal_path, shm_path):
        sidecar.write_text("placeholder")
        sidecar.chmod(0o644)

    _enforce_sqlite_owner_only_permissions(db_path)

    assert stat.S_IMODE(wal_path.stat().st_mode) == 0o600
    assert stat.S_IMODE(shm_path.stat().st_mode) == 0o600
