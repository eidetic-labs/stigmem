"""Conformance suite fixtures — parameterized over all three backends.

How back-end selection works
----------------------------
* When run via ``python -m stigmem_conformance --backend <name>`` the
  ``--conformance-backend`` pytest option is set and the ``conformance_client``
  fixture is created for that single backend only.
* When run directly with ``pytest node/src/stigmem_conformance/tests/`` the
  fixture is parametrized over all three backends; unavailable backends are
  skipped automatically.

Skip conditions
---------------
* libsql  — ``libsql_experimental`` not installed.
* postgres — ``psycopg2`` not installed **or** ``STIGMEM_TEST_PG_DSN`` unset.
"""

from __future__ import annotations

import importlib
import os
import uuid
from collections.abc import Generator
from pathlib import Path
from typing import NamedTuple

import pytest
from fastapi.testclient import TestClient

_MIGRATIONS_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent  # node/src
    .parent  # node
    / "migrations"
)

_ALL_BACKENDS = ["sqlite", "libsql", "postgres"]


# ---------------------------------------------------------------------------
# CLI option: allow runner to pin to one backend
# ---------------------------------------------------------------------------


def pytest_addoption(parser: pytest.Parser) -> None:  # type: ignore[name-defined]
    parser.addoption(
        "--conformance-backend",
        default=None,
        choices=_ALL_BACKENDS,
        help="Run conformance suite against a single backend (default: all)",
    )


# ---------------------------------------------------------------------------
# Settings / app patching helpers (mirrored from node/tests/conftest.py)
# ---------------------------------------------------------------------------

_PATCHABLE_MODULES = [
    "stigmem_node.federation_pull",
    "stigmem_node.peer_token",
    "stigmem_node.federation_ingest",
    "stigmem_node.routes.federation",
    "stigmem_node.routes.identity",
    "stigmem_node.identity.trust_store",
    "stigmem_node.decay",
    "stigmem_node.routes.decay",
    "stigmem_node.routes.lint",
    "stigmem_node.routes.synthesize",
    "stigmem_node.routes.recall",
    "stigmem_node.routes.cards",
    "stigmem_node.card_materializer",
    "stigmem_node.rate_limit",
]


def _get_extra_modules() -> list:
    mods = []
    for name in _PATCHABLE_MODULES:
        try:
            mods.append(importlib.import_module(name))
        except ImportError:
            pass
    return mods


def _patch_settings(test_settings: object) -> list:
    import stigmem_node.auth as auth_mod
    import stigmem_node.db as db_mod
    import stigmem_node.routes.wellknown as wk_mod
    import stigmem_node.settings as settings_module

    extra = _get_extra_modules()
    settings_module.settings = test_settings  # type: ignore[assignment]
    auth_mod.settings = test_settings  # type: ignore[assignment]
    db_mod.settings = test_settings  # type: ignore[assignment]
    wk_mod.settings = test_settings  # type: ignore[assignment]
    for mod in extra:
        if hasattr(mod, "settings"):
            setattr(mod, "settings", test_settings)
    return extra


def _restore_settings(original: object, extra: list) -> None:
    import stigmem_node.auth as auth_mod
    import stigmem_node.db as db_mod
    import stigmem_node.routes.wellknown as wk_mod
    import stigmem_node.settings as settings_module

    settings_module.settings = original  # type: ignore[assignment]
    auth_mod.settings = original  # type: ignore[assignment]
    db_mod.settings = original  # type: ignore[assignment]
    wk_mod.settings = original  # type: ignore[assignment]
    for mod in extra:
        if hasattr(mod, "settings"):
            setattr(mod, "settings", original)


# ---------------------------------------------------------------------------
# Backend availability checks
# ---------------------------------------------------------------------------


def _backend_available(backend_name: str) -> tuple[bool, str]:
    """Return (available, skip_reason)."""
    if backend_name == "libsql":
        try:
            import libsql_experimental  # type: ignore[import]  # noqa: F401
        except ImportError:
            return False, "libsql-experimental not installed (pip install 'stigmem-node[libsql]')"
    elif backend_name == "postgres":
        try:
            import psycopg2  # type: ignore[import]  # noqa: F401
        except ImportError:
            return False, "psycopg2 not installed (pip install 'stigmem-node[postgres]')"
        if not os.environ.get("STIGMEM_TEST_PG_DSN"):
            return False, "STIGMEM_TEST_PG_DSN env var not set"
    return True, ""


# ---------------------------------------------------------------------------
# Core fixture
# ---------------------------------------------------------------------------


class ConformanceClient(NamedTuple):
    client: TestClient
    backend: str


def _build_client(
    backend_name: str,
    tmp_path: Path,
    pg_dsn: str = "",
    pg_schema: str = "",
) -> Generator[ConformanceClient, None, None]:
    from stigmem_node.main import create_app
    from stigmem_node.settings import Settings
    from stigmem_node.storage import make_backend
    import stigmem_node.settings as settings_module

    original = settings_module.settings

    if backend_name == "postgres":
        schema = pg_schema or f"conformance_{uuid.uuid4().hex[:12]}"
        settings_obj = Settings(
            db_path="conformance_pg",
            storage_backend="postgres",
            pg_dsn=pg_dsn,
            pg_schema=schema,
            auth_required=False,
            node_url="http://testnode",
        )
    else:
        db_file = str(tmp_path / f"conformance_{backend_name}.db")
        settings_obj = Settings(
            db_path=db_file,
            storage_backend=backend_name,
            auth_required=False,
            node_url="http://testnode",
        )

    b = make_backend(_settings=settings_obj)
    b.apply_migrations(_MIGRATIONS_DIR)

    extra = _patch_settings(settings_obj)
    app = create_app()
    with TestClient(app, raise_server_exceptions=True) as c:
        yield ConformanceClient(client=c, backend=backend_name)
    _restore_settings(original, extra)

    # Drop Postgres schema to clean up
    if backend_name == "postgres":
        try:
            import psycopg2  # type: ignore[import]

            conn = psycopg2.connect(pg_dsn)
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")  # noqa: S608
            conn.close()
        except Exception:
            pass  # best-effort cleanup; CI job isolation handles the rest


@pytest.fixture(params=_ALL_BACKENDS)
def conformance_client(
    request: pytest.FixtureRequest, tmp_path: Path
) -> Generator[ConformanceClient, None, None]:
    """TestClient parametrized over all three backends.

    Each backend is skipped if its runtime dependency is missing or (for
    postgres) the test DSN is not configured.

    Can be pinned to a single backend via ``--conformance-backend``.
    """
    pinned: str | None = request.config.getoption("--conformance-backend")
    backend_name: str = request.param

    if pinned is not None and backend_name != pinned:
        pytest.skip(f"pinned to backend={pinned}")

    ok, reason = _backend_available(backend_name)
    if not ok:
        pytest.skip(reason)

    pg_dsn = os.environ.get("STIGMEM_TEST_PG_DSN", "")
    pg_schema = os.environ.get("STIGMEM_TEST_PG_SCHEMA", "")

    yield from _build_client(backend_name, tmp_path, pg_dsn=pg_dsn, pg_schema=pg_schema)
