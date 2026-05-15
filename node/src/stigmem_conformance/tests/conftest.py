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
from collections.abc import Callable, Generator
from pathlib import Path
from typing import NamedTuple, cast

import pytest
from fastapi.testclient import TestClient

import stigmem_node.auth as auth_mod
import stigmem_node.db as db_mod
import stigmem_node.main as main_mod
import stigmem_node.plugins as plugins_mod
import stigmem_node.plugins.lifecycle as plugin_lifecycle
import stigmem_node.routes.wellknown as wk_mod
import stigmem_node.settings as settings_module
import stigmem_node.storage as storage_mod

Settings = settings_module.Settings
make_backend = storage_mod.make_backend


_MIGRATIONS_DIR = (
    Path(__file__).resolve().parent.parent.parent.parent.parent  # node/src  # node
    / "migrations"
)

_ALL_BACKENDS = ["sqlite", "libsql", "postgres"]
_PLUGIN_PROFILES = ["default", "full"]
_CONFORMANCE_PLUGIN_SIGNING_IDENTITY = "sigstore:conformance-full-plugin"
_DiscoverPlugins = Callable[[], tuple[plugins_mod.DiscoveredPlugin, ...]]


# ---------------------------------------------------------------------------
# CLI option: allow runner to pin to one backend
# ---------------------------------------------------------------------------


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--conformance-backend",
        default=None,
        choices=_ALL_BACKENDS,
        help="Run conformance suite against a single backend (default: all)",
    )
    parser.addoption(
        "--conformance-plugin-profile",
        default="default",
        choices=_PLUGIN_PROFILES,
        help=(
            "Plugin install profile for conformance runs: default keeps the "
            "v1.0 critical path plugin-free; full registers a representative "
            "signed plugin set."
        ),
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


def _get_extra_modules() -> list[object]:
    import contextlib

    mods: list[object] = []
    for name in _PATCHABLE_MODULES:
        with contextlib.suppress(ImportError):
            mods.append(importlib.import_module(name))
    return mods


def _patch_settings(test_settings: Settings) -> list[object]:
    extra = _get_extra_modules()
    settings_module.settings = test_settings
    auth_mod.settings = test_settings
    db_mod.settings = test_settings
    wk_mod.settings = test_settings
    for mod in extra:
        if hasattr(mod, "settings"):
            mod.settings = test_settings
    return extra


def _restore_settings(original: Settings, extra: list[object]) -> None:
    settings_module.settings = original
    auth_mod.settings = original
    db_mod.settings = original
    wk_mod.settings = original
    for mod in extra:
        if hasattr(mod, "settings"):
            mod.settings = original


# ---------------------------------------------------------------------------
# Plugin install profiles
# ---------------------------------------------------------------------------


def _allow(_ctx: plugins_mod.PluginContext, **_: object) -> plugins_mod.Allow:
    return plugins_mod.Allow()


def _identity(
    _ctx: plugins_mod.PluginContext, value: object, **_: object
) -> object:
    return value


def _score_delta(
    _ctx: plugins_mod.PluginContext, _scored_results: list[object], **_: object
) -> dict[str, float]:
    return {}


def _noop(_ctx: plugins_mod.PluginContext, **_: object) -> None:
    return None


def _conformance_full_plugin() -> plugins_mod.DiscoveredPlugin:
    manifest = plugins_mod.PluginManifest(
        name="conformance-full-plugin",
        version="1.0.0",
        capabilities=frozenset({"audit.emit", "facts.read", "recall.read"}),
        hooks={
            "pre_assert_authorize": _allow,
            "pre_assert_transform": _identity,
            "recall_rank": _score_delta,
            "post_assert_persist": _noop,
        },
        health_check=lambda _ctx: plugins_mod.PluginHealth(
            plugins_mod.PluginHealthStatus.HEALTHY,
            "conformance plugin profile ready",
        ),
    )
    return plugins_mod.DiscoveredPlugin(
        manifest=manifest,
        entry_point_name=manifest.name,
        entry_point_value="stigmem_conformance.plugins:full_profile",
        distribution="stigmem-conformance",
        signing_identity=_CONFORMANCE_PLUGIN_SIGNING_IDENTITY,
        signature_verified=True,
    )


def _install_plugin_profile(profile: str) -> object:
    original = cast(
        _DiscoverPlugins,
        plugin_lifecycle.discover_plugin_manifests,  # type: ignore[attr-defined]
    )
    if profile == "default":
        def discover_default() -> tuple[plugins_mod.DiscoveredPlugin, ...]:
            return ()

        plugin_lifecycle.discover_plugin_manifests = discover_default  # type: ignore[assignment,attr-defined]
    elif profile == "full":
        def discover_full() -> tuple[plugins_mod.DiscoveredPlugin, ...]:
            return (_conformance_full_plugin(),)

        plugin_lifecycle.discover_plugin_manifests = discover_full  # type: ignore[assignment,attr-defined]
    else:
        raise ValueError(f"unknown conformance plugin profile: {profile}")
    return original


def _restore_plugin_profile(original: object) -> None:
    plugin_lifecycle.discover_plugin_manifests = original  # type: ignore[assignment,attr-defined]


# ---------------------------------------------------------------------------
# Backend availability checks
# ---------------------------------------------------------------------------


def _backend_available(backend_name: str) -> tuple[bool, str]:
    """Return (available, skip_reason)."""
    if backend_name == "libsql":
        try:
            import libsql_experimental  # noqa: F401
        except ImportError:
            return False, "libsql-experimental not installed (pip install 'stigmem-node[libsql]')"
    elif backend_name == "postgres":
        try:
            import psycopg2  # noqa: F401
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
    plugin_profile: str = "default",
    pg_dsn: str = "",
    pg_schema: str = "",
) -> Generator[ConformanceClient, None, None]:
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
            plugin_trusted_publishers=_CONFORMANCE_PLUGIN_SIGNING_IDENTITY,
        )
    else:
        db_file = str(tmp_path / f"conformance_{backend_name}.db")
        settings_obj = Settings(
            db_path=db_file,
            storage_backend=backend_name,
            auth_required=False,
            node_url="http://testnode",
            plugin_trusted_publishers=_CONFORMANCE_PLUGIN_SIGNING_IDENTITY,
        )

    b = make_backend(_settings=settings_obj)
    b.apply_migrations(_MIGRATIONS_DIR)

    extra = _patch_settings(settings_obj)
    original_discovery = _install_plugin_profile(plugin_profile)
    previous_registry = plugins_mod.set_registry(plugins_mod.HookRegistry())
    try:
        app = main_mod.create_app()
        with TestClient(app, raise_server_exceptions=True) as c:
            yield ConformanceClient(client=c, backend=backend_name)
    finally:
        plugins_mod.set_registry(previous_registry)
        _restore_plugin_profile(original_discovery)
        _restore_settings(original, extra)

    # Drop Postgres schema to clean up; best-effort, CI job isolation handles the rest.
    if backend_name == "postgres":
        import logging as _log

        try:
            import psycopg2

            conn = psycopg2.connect(pg_dsn)
            conn.autocommit = True
            with conn.cursor() as cur:
                cur.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")  # noqa: S608
            conn.close()
        except Exception as exc:
            _log.getLogger("stigmem.conformance").debug(
                "postgres schema drop failed (best-effort): %s", exc
            )


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
    plugin_profile: str = request.config.getoption("--conformance-plugin-profile")
    backend_name: str = request.param

    if pinned is not None and backend_name != pinned:
        pytest.skip(f"pinned to backend={pinned}")

    ok, reason = _backend_available(backend_name)
    if not ok:
        pytest.skip(reason)

    pg_dsn = os.environ.get("STIGMEM_TEST_PG_DSN", "")
    pg_schema = os.environ.get("STIGMEM_TEST_PG_SCHEMA", "")

    yield from _build_client(
        backend_name,
        tmp_path,
        plugin_profile=plugin_profile,
        pg_dsn=pg_dsn,
        pg_schema=pg_schema,
    )
