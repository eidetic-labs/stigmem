"""Pytest fixtures for the eval harness — node startup and corpus loading."""

from __future__ import annotations

import contextlib
import importlib
import os
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Allow imports from the node package when running eval/ tests directly.
# ---------------------------------------------------------------------------
_NODE_SRC = Path(__file__).resolve().parent.parent / "node" / "src"
if str(_NODE_SRC) not in sys.path:
    sys.path.insert(0, str(_NODE_SRC))


# ---------------------------------------------------------------------------
# In-process node fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def eval_node():
    """Start an in-process stigmem-node for the eval suite.

    Uses a temporary SQLite database with auth disabled so the harness can
    assert facts and run recall without needing a real API key.

    Yields an httpx.Client already pointed at the in-process node.
    """
    import tempfile

    import httpx

    # Import here so missing deps produce a clear skip message.
    try:
        import stigmem_node.auth as auth_mod
        import stigmem_node.routes.wellknown as wk_mod
        from fastapi.testclient import TestClient
        from stigmem_node.main import create_app
    except ImportError as exc:
        pytest.skip(f"stigmem_node not importable: {exc}")
    db_mod = importlib.import_module("stigmem_node.db")
    settings_module = importlib.import_module("stigmem_node.settings")

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        tmp = tmp_file.name
    original = settings_module.settings

    def _extra_mods():
        extra = []
        for name, mod in sys.modules.items():
            if name.startswith("stigmem_node") and hasattr(mod, "settings"):
                extra.append(mod)
        return extra

    test_settings = settings_module.Settings(
        db_path=tmp,
        storage_backend="sqlite",
        auth_required=False,
        node_url="http://127.0.0.1:8765",
    )
    settings_module.settings = test_settings  # type: ignore[assignment]
    auth_mod.settings = test_settings  # type: ignore[assignment]
    db_mod.settings = test_settings  # type: ignore[assignment]
    wk_mod.settings = test_settings  # type: ignore[assignment]
    extra = _extra_mods()
    for mod in extra:
        mod.settings = test_settings

    db_mod.apply_migrations(db_path=tmp)
    app = create_app()

    with TestClient(app, raise_server_exceptions=False) as tc:
        # Wrap TestClient in an httpx.Client-compatible shim
        class _TestClientAdapter(httpx.Client):
            """Thin wrapper so harness code works with either TestClient or real httpx."""

            def __init__(self, tc_inner: TestClient) -> None:
                self._tc = tc_inner

            def post(self, url: str, **kwargs):  # type: ignore[override]
                return self._tc.post(url, **kwargs)

            def get(self, url: str, **kwargs):  # type: ignore[override]
                return self._tc.get(url, **kwargs)

            @property
            def base_url(self):
                return "http://127.0.0.1:8765"

        yield _TestClientAdapter(tc)

    # Restore settings
    settings_module.settings = original  # type: ignore[assignment]
    auth_mod.settings = original  # type: ignore[assignment]
    db_mod.settings = original  # type: ignore[assignment]
    wk_mod.settings = original  # type: ignore[assignment]
    for mod in extra:
        if hasattr(mod, "settings"):
            mod.settings = original

    # Clean up temp DB. The file may already be gone if the fixture failed during setup.
    with contextlib.suppress(FileNotFoundError):
        os.unlink(tmp)


# ---------------------------------------------------------------------------
# Auth-enabled node fixture (for capability-token forgery tests)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def auth_eval_node():
    """In-process node with auth_required=True — forged tokens get 401/403.

    Creates a standalone auth-enabled TestClient against a separate temp DB.
    Settings are patched locally and restored from the snapshot taken BEFORE
    the patch, so the non-auth eval_node is unaffected.
    """
    import tempfile

    import httpx

    try:
        from fastapi.testclient import TestClient
        from stigmem_node.main import create_app
    except ImportError as exc:
        pytest.skip(f"stigmem_node not importable: {exc}")
    db_mod = importlib.import_module("stigmem_node.db")
    settings_module = importlib.import_module("stigmem_node.settings")

    saved_map: dict[str, object] = {}
    for name, mod in list(sys.modules.items()):
        if name.startswith("stigmem_node") and hasattr(mod, "settings"):
            saved_map[name] = mod.settings

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        tmp = tmp_file.name
    auth_settings = settings_module.Settings(
        db_path=tmp,
        storage_backend="sqlite",
        auth_required=True,
        node_url="http://eval-authnode",
    )
    for name in saved_map:
        sys.modules[name].settings = auth_settings

    db_mod.apply_migrations(db_path=tmp)
    app = create_app()

    with TestClient(app, raise_server_exceptions=False) as tc:

        class _AuthAdapter(httpx.Client):
            def __init__(self, tc_inner: TestClient) -> None:
                self._tc = tc_inner

            def post(self, url: str, **kwargs):  # type: ignore[override]
                return self._tc.post(url, **kwargs)

            def get(self, url: str, **kwargs):  # type: ignore[override]
                return self._tc.get(url, **kwargs)

            @property
            def base_url(self):
                return "http://eval-authnode"

        yield _AuthAdapter(tc)

    for name, saved_val in saved_map.items():
        if name in sys.modules:
            sys.modules[name].settings = saved_val

    # Clean up temp DB. The file may already be gone if the fixture failed during setup.
    with contextlib.suppress(FileNotFoundError):
        os.unlink(tmp)


# ---------------------------------------------------------------------------
# Corpus fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def adversarial_corpus():
    from eval.harness.utils import load_all_adversarial

    return load_all_adversarial()


@pytest.fixture(scope="session")
def recall_probes():
    from eval.harness.utils import load_probes

    return load_probes()
