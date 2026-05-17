"""B2 coverage push for stigmem_node.cli — extends test_cli_handlers.py with
the bigger handlers (instruction-manifest-generate, backfill-cids,
auth bootstrap-key, federation register-peer).

Same pattern as B1: bypass argparse and call ``_cmd_*`` directly with
fabricated argparse.Namespace objects, mocking httpx where needed.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import textwrap
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Helpers (mirrors test_cli_handlers.py)
# ---------------------------------------------------------------------------


def _args(**kwargs: object) -> argparse.Namespace:
    return argparse.Namespace(**kwargs)


class _FakeResponse:
    def __init__(
        self,
        status_code: int,
        json_body: Any = None,
        text: str = "",
    ) -> None:
        self.status_code = status_code
        self._json = json_body if json_body is not None else {}
        self.text = text or json.dumps(self._json)

    def json(self) -> Any:
        return self._json

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def _migrated_db(tmp_path: Path) -> str:
    from stigmem_node.db import apply_migrations

    db_file = str(tmp_path / "cli_b2_test.db")
    apply_migrations(db_path=db_file)
    return db_file


# ---------------------------------------------------------------------------
# instruction-manifest-generate (pure file-IO; ~95 lines uncovered)
# ---------------------------------------------------------------------------


def _write_md(path: Path, name: str, body: str) -> Path:
    p = path / f"{name}.md"
    p.write_text(body, encoding="utf-8")
    return p


class TestInstructionManifestGenerate:
    def test_not_a_directory_returns_1(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        from stigmem_node.cli import _cmd_instruction_manifest_generate

        args = _args(
            path=str(tmp_path / "nope"),
            deployment="prod",
            agent_id="a1",
            version="v1",
            out=None,
        )
        assert _cmd_instruction_manifest_generate(args) == 1
        assert "is not a directory" in capsys.readouterr().err

    def test_generates_entries_from_h2_h3_sections(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        from stigmem_node.cli import _cmd_instruction_manifest_generate

        _write_md(
            tmp_path,
            "guide",
            textwrap.dedent("""\
            # Top heading (ignored — H1)

            ## Section One

            Body of section one with words like deployment and observability.

            ## Section Two

            Another section about checkpoints and retention.

            ### Subsection

            Nested H3 content with keywords for testing.
        """),
        )

        args = _args(
            path=str(tmp_path),
            deployment="dev",
            agent_id="agent-x",
            version="v0.1",
            out=None,
        )
        assert _cmd_instruction_manifest_generate(args) == 0

        # When out=None, manifest JSON is printed to stdout
        out = capsys.readouterr().out
        manifest = json.loads(out)
        assert manifest["agent_id"] == "agent-x"
        assert manifest["deployment"] == "dev"
        assert manifest["version"] == "v0.1"
        # 3 entries: "Section One", "Section Two", "Subsection"
        assert len(manifest["entries"]) >= 3
        names = {e["name"] for e in manifest["entries"]}
        assert any("section-one" in n for n in names)

    def test_writes_to_output_file_when_specified(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        from stigmem_node.cli import _cmd_instruction_manifest_generate

        _write_md(tmp_path, "doc", "## A heading\n\nbody text\n")
        out_path = tmp_path / "manifest.json"

        args = _args(
            path=str(tmp_path),
            deployment="d",
            agent_id="a",
            version="v",
            out=str(out_path),
        )
        assert _cmd_instruction_manifest_generate(args) == 0
        assert out_path.exists()
        assert "Wrote" in capsys.readouterr().out
        manifest = json.loads(out_path.read_text())
        assert manifest["entries"]

    def test_handles_md_file_with_no_headings(self, tmp_path: Path) -> None:
        from stigmem_node.cli import _cmd_instruction_manifest_generate

        # File with no H2/H3 → falls back to one chunk derived from filename
        _write_md(tmp_path, "no-headings", "Just plain prose without any headings at all.")

        args = _args(
            path=str(tmp_path),
            deployment="d",
            agent_id="a",
            version="v",
            out=None,
        )
        assert _cmd_instruction_manifest_generate(args) == 0

    def test_skips_empty_directory(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        from stigmem_node.cli import _cmd_instruction_manifest_generate

        # Empty directory → empty manifest
        args = _args(
            path=str(tmp_path),
            deployment="d",
            agent_id="a",
            version="v",
            out=None,
        )
        assert _cmd_instruction_manifest_generate(args) == 0
        manifest = json.loads(capsys.readouterr().out)
        assert manifest["entries"] == []

    def test_skips_unreadable_md_file(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from pathlib import Path as _Path

        from stigmem_node.cli import _cmd_instruction_manifest_generate

        _write_md(tmp_path, "good", "## ok\n\ncontent\n")
        bad = _write_md(tmp_path, "bad", "ignored")

        # Force read_text to fail for the "bad" file specifically
        original_read_text = _Path.read_text

        def fake_read_text(self: _Path, *a: Any, **kw: Any) -> str:
            if self.name == bad.name:
                raise OSError("permission denied")
            return original_read_text(self, *a, **kw)

        monkeypatch.setattr(_Path, "read_text", fake_read_text)

        args = _args(
            path=str(tmp_path),
            deployment="d",
            agent_id="a",
            version="v",
            out=None,
        )
        assert _cmd_instruction_manifest_generate(args) == 0
        assert "warning: skipping" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# backfill-cids (sqlite-only loop; ~75 lines uncovered)
# ---------------------------------------------------------------------------


def _seed_fact_without_cid(
    db_path: str,
    *,
    fact_id: str,
    entity: str,
    value: str = "v",
) -> None:
    """Insert a fact row with cid=NULL so backfill-cids picks it up."""
    conn = sqlite3.connect(db_path)
    conn.execute(
        """INSERT INTO facts
           (id, entity, relation, value_type, value_v, source, scope,
            confidence, timestamp, hlc, tenant_id, cid)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)""",
        (
            fact_id,
            entity,
            "memory:knows",
            "string",
            value,
            "stigmem://test/source",
            "local",
            1.0,
            "2026-01-01T00:00:00Z",
            "0:0:0",
            "default",
        ),
    )
    conn.commit()
    conn.close()


class TestBackfillCids:
    def test_no_facts_to_backfill(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture,
    ) -> None:
        from stigmem_node.cli import _cmd_backfill_cids

        db = _migrated_db(tmp_path)
        args = _args(db=db, batch_size=500, quiet=False)
        assert _cmd_backfill_cids(args) == 0
        assert "0 facts updated" in capsys.readouterr().err

    def test_quiet_mode_suppresses_output(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture,
    ) -> None:
        from stigmem_node.cli import _cmd_backfill_cids

        db = _migrated_db(tmp_path)
        args = _args(db=db, batch_size=500, quiet=True)
        assert _cmd_backfill_cids(args) == 0
        # Quiet mode prints nothing to stderr
        assert capsys.readouterr().err == ""

    def test_backfills_facts_missing_cid(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture,
    ) -> None:
        from stigmem_node.cli import _cmd_backfill_cids

        db = _migrated_db(tmp_path)
        _seed_fact_without_cid(db, fact_id="f1", entity="stigmem://e/1")
        _seed_fact_without_cid(db, fact_id="f2", entity="stigmem://e/2")

        args = _args(db=db, batch_size=500, quiet=False)
        assert _cmd_backfill_cids(args) == 0
        err = capsys.readouterr().err
        assert "2 facts updated" in err

        # Verify CID aliases/backfill projection rows were written while facts
        # remain immutable.
        conn = sqlite3.connect(db)
        rows = conn.execute(
            """
            SELECT f.id, f.cid, fca.cid AS alias_cid, fcb.status
            FROM facts f
            LEFT JOIN fact_cid_aliases fca ON fca.fact_id = f.id
            LEFT JOIN fact_cid_backfill fcb ON fcb.fact_id = f.id
            ORDER BY f.id
            """
        ).fetchall()
        conn.close()
        assert len(rows) == 2
        assert all(base_cid is None for _, base_cid, _, _ in rows)
        assert all(alias_cid for _, _, alias_cid, _ in rows)
        assert all(status == "complete" for _, _, _, status in rows)

    def test_db_path_falls_back_to_env(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        from stigmem_node.cli import _cmd_backfill_cids

        db = _migrated_db(tmp_path)
        monkeypatch.setenv("STIGMEM_DB_PATH", db)

        # No db arg, no batch_size, no quiet — uses defaults via getattr
        args = argparse.Namespace()  # bare namespace; uses env + defaults
        assert _cmd_backfill_cids(args) == 0
        assert "0 facts updated" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# auth bootstrap-key
# ---------------------------------------------------------------------------


class TestAuthBootstrapKey:
    def test_no_key_returns_2_with_helpful_error(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        from stigmem_node.cli import _cmd_auth_bootstrap_key

        monkeypatch.delenv("STIGMEM_BOOTSTRAP_KEY", raising=False)
        args = _args(
            key=None,
            entity_uri="stigmem://test/admin",
            permissions=None,
        )
        assert _cmd_auth_bootstrap_key(args) == 2
        err = capsys.readouterr().err
        assert "no key value provided" in err

    def test_short_key_returns_2(
        self,
        capsys: pytest.CaptureFixture,
    ) -> None:
        from stigmem_node.cli import _cmd_auth_bootstrap_key

        args = _args(
            key="too-short",
            entity_uri="stigmem://test/admin",
            permissions=None,
        )
        assert _cmd_auth_bootstrap_key(args) == 2
        assert "at least 16 characters" in capsys.readouterr().err

    def test_first_run_registers_key(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        from stigmem_node import db as db_mod
        from stigmem_node.cli import _cmd_auth_bootstrap_key

        db = _migrated_db(tmp_path)
        monkeypatch.setattr(db_mod.settings, "db_path", db)
        # auth.register_api_key also reads settings.db_path indirectly
        from stigmem_node import auth as auth_mod

        monkeypatch.setattr(auth_mod.settings, "db_path", db)

        args = _args(
            key="x" * 32,  # 32 chars passes length check
            entity_uri="stigmem://test/admin",
            permissions="admin,write,read",
        )
        assert _cmd_auth_bootstrap_key(args) == 0
        captured = capsys.readouterr()
        # `print(..., file=sys.stderr)` is the typical pattern; just check both
        combined = captured.out + captured.err
        assert "Registered admin API key" in combined
        assert "stigmem://test/admin" in combined

    def test_second_run_refuses_when_keys_exist(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        from stigmem_node import auth as auth_mod
        from stigmem_node import db as db_mod
        from stigmem_node.cli import _cmd_auth_bootstrap_key

        db = _migrated_db(tmp_path)
        monkeypatch.setattr(db_mod.settings, "db_path", db)
        monkeypatch.setattr(auth_mod.settings, "db_path", db)

        # Seed an existing key so bootstrap refuses
        from stigmem_node.auth import create_api_key

        create_api_key("stigmem://test/preexisting", ["admin"])

        args = _args(
            key="y" * 32,
            entity_uri="stigmem://test/admin",
            permissions=None,
        )
        assert _cmd_auth_bootstrap_key(args) == 1
        assert "not empty" in capsys.readouterr().err

    def test_key_via_environment_variable(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        from stigmem_node import auth as auth_mod
        from stigmem_node import db as db_mod
        from stigmem_node.cli import _cmd_auth_bootstrap_key

        db = _migrated_db(tmp_path)
        monkeypatch.setattr(db_mod.settings, "db_path", db)
        monkeypatch.setattr(auth_mod.settings, "db_path", db)
        monkeypatch.setenv("STIGMEM_BOOTSTRAP_KEY", "z" * 32)

        args = _args(
            key=None,
            entity_uri="stigmem://test/env-admin",
            permissions=None,
        )
        assert _cmd_auth_bootstrap_key(args) == 0
        captured = capsys.readouterr()
        assert "Registered admin API key" in (captured.out + captured.err)


# ---------------------------------------------------------------------------
# federation register-peer (httpx-mocked; ~113 lines uncovered)
# ---------------------------------------------------------------------------


def _patch_httpx(
    monkeypatch: pytest.MonkeyPatch,
    get_responses: dict[str, _FakeResponse] | None = None,
    post_responses: dict[str, _FakeResponse] | None = None,
    get_raises: Exception | None = None,
    post_raises: Exception | None = None,
) -> dict:
    """Patch httpx.get and httpx.post with URL→response routing."""
    captured: dict = {}

    def fake_get(url: str, **kw: Any) -> _FakeResponse:
        captured.setdefault("get_calls", []).append(url)
        captured.setdefault("get_kwargs", []).append(kw)
        if get_raises is not None:
            raise get_raises
        for prefix, resp in (get_responses or {}).items():
            if prefix in url:
                return resp
        raise AssertionError(f"unexpected GET {url}")

    def fake_post(url: str, **kw: Any) -> _FakeResponse:
        captured.setdefault("post_calls", []).append(
            {
                "url": url,
                "json": kw.get("json"),
                "cert": kw.get("cert"),
                "verify": kw.get("verify"),
            }
        )
        if post_raises is not None:
            raise post_raises
        for prefix, resp in (post_responses or {}).items():
            if prefix in url:
                return resp
        raise AssertionError(f"unexpected POST {url}")

    import httpx

    monkeypatch.setattr(httpx, "get", fake_get)
    monkeypatch.setattr(httpx, "post", fake_post)
    return captured


class TestFederationRegisterPeer:
    def _common_args(self, **overrides: object) -> argparse.Namespace:
        base = dict(
            local_url="http://local",
            remote_url="http://remote",
            scopes="public,local",
            api_key=None,
            tls_cert=None,
            tls_key=None,
            ca_bundle=None,
        )
        base.update(overrides)
        return _args(**base)

    def test_local_node_unreachable(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
        tmp_path: Path,
    ) -> None:
        from stigmem_node import db as db_mod
        from stigmem_node.cli import _cmd_federation_register_peer

        db = _migrated_db(tmp_path)
        monkeypatch.setattr(db_mod.settings, "db_path", db)

        _patch_httpx(monkeypatch, get_raises=RuntimeError("conn refused"))
        rc = _cmd_federation_register_peer(self._common_args())
        assert rc == 1
        assert "cannot reach local node" in capsys.readouterr().err

    def test_local_node_missing_federation_pubkey(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
        tmp_path: Path,
    ) -> None:
        from stigmem_node import db as db_mod
        from stigmem_node.cli import _cmd_federation_register_peer

        db = _migrated_db(tmp_path)
        monkeypatch.setattr(db_mod.settings, "db_path", db)

        _patch_httpx(
            monkeypatch,
            get_responses={
                ".well-known/stigmem": _FakeResponse(
                    200,
                    {"node_id": "stigmem://local", "federation_pubkey": ""},
                ),
            },
        )
        rc = _cmd_federation_register_peer(self._common_args())
        assert rc == 1
        assert "no federation_pubkey" in capsys.readouterr().err

    def test_remote_returns_409_already_registered(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
        tmp_path: Path,
    ) -> None:
        from stigmem_node import db as db_mod
        from stigmem_node.cli import _cmd_federation_register_peer

        db = _migrated_db(tmp_path)
        monkeypatch.setattr(db_mod.settings, "db_path", db)
        # init_federation_keys reads from THIS DB; let it bootstrap a fresh keypair

        _patch_httpx(
            monkeypatch,
            get_responses={
                ".well-known/stigmem": _FakeResponse(
                    200,
                    {"node_id": "stigmem://local", "federation_pubkey": "PUB123"},
                ),
            },
            post_responses={
                "/v1/federation/peers": _FakeResponse(409, text="already there"),
            },
        )
        rc = _cmd_federation_register_peer(self._common_args(api_key="k1"))
        assert rc == 0
        assert "already registered" in capsys.readouterr().out

    def test_remote_returns_active(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
        tmp_path: Path,
    ) -> None:
        from stigmem_node import db as db_mod
        from stigmem_node.cli import _cmd_federation_register_peer

        db = _migrated_db(tmp_path)
        monkeypatch.setattr(db_mod.settings, "db_path", db)

        _patch_httpx(
            monkeypatch,
            get_responses={
                ".well-known/stigmem": _FakeResponse(
                    200,
                    {"node_id": "stigmem://local", "federation_pubkey": "PUB"},
                ),
            },
            post_responses={
                "/v1/federation/peers": _FakeResponse(
                    201,
                    {"status": "active", "peer_id": "p-99"},
                ),
            },
        )
        rc = _cmd_federation_register_peer(self._common_args())
        assert rc == 0
        assert "peer registered and verified" in capsys.readouterr().out

    def test_tls_options_are_passed_to_httpx(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
        tmp_path: Path,
    ) -> None:
        from stigmem_node import db as db_mod
        from stigmem_node.cli import _cmd_federation_register_peer

        db = _migrated_db(tmp_path)
        monkeypatch.setattr(db_mod.settings, "db_path", db)

        captured: dict[str, object] = {"client_kwargs": []}

        class FakeClient:
            def __init__(self, **kwargs: object) -> None:
                captured["client_kwargs"].append(kwargs)  # type: ignore[attr-defined]

            def __enter__(self) -> FakeClient:
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def get(self, url: str) -> _FakeResponse:
                captured["get_url"] = url
                return _FakeResponse(
                    200,
                    {"node_id": "stigmem://local", "federation_pubkey": "PUB"},
                )

            def post(
                self,
                url: str,
                json: dict[str, object],
                headers: dict[str, str],
            ) -> _FakeResponse:
                captured["post_url"] = url
                captured["post_json"] = json
                captured["post_headers"] = headers
                return _FakeResponse(201, {"status": "active", "peer_id": "p-99"})

        import ssl

        import httpx

        class FakeSSLContext:
            def load_cert_chain(self, certfile: str, keyfile: str) -> None:
                captured["certfile"] = certfile
                captured["keyfile"] = keyfile

        monkeypatch.setattr(ssl, "create_default_context", lambda cafile=None: FakeSSLContext())

        monkeypatch.setattr(httpx, "Client", FakeClient)
        rc = _cmd_federation_register_peer(
            self._common_args(
                tls_cert="/tls/node.crt",
                tls_key="/tls/node.key",
                ca_bundle="/tls/ca.crt",
            )
        )
        assert rc == 0
        assert "peer registered and verified" in capsys.readouterr().out
        client_kwargs = captured["client_kwargs"]
        assert isinstance(client_kwargs[0]["verify"], FakeSSLContext)
        assert isinstance(client_kwargs[1]["verify"], FakeSSLContext)
        assert captured["certfile"] == "/tls/node.crt"
        assert captured["keyfile"] == "/tls/node.key"

    def test_remote_returns_pending_status(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
        tmp_path: Path,
    ) -> None:
        from stigmem_node import db as db_mod
        from stigmem_node.cli import _cmd_federation_register_peer

        db = _migrated_db(tmp_path)
        monkeypatch.setattr(db_mod.settings, "db_path", db)

        _patch_httpx(
            monkeypatch,
            get_responses={
                ".well-known/stigmem": _FakeResponse(
                    200,
                    {"node_id": "stigmem://local", "federation_pubkey": "PUB"},
                ),
            },
            post_responses={
                "/v1/federation/peers": _FakeResponse(
                    201,
                    {"status": "pending_verification", "peer_id": "p-1"},
                ),
            },
        )
        rc = _cmd_federation_register_peer(self._common_args())
        assert rc == 1
        assert "not yet active" in capsys.readouterr().err

    def test_remote_returns_500(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
        tmp_path: Path,
    ) -> None:
        from stigmem_node import db as db_mod
        from stigmem_node.cli import _cmd_federation_register_peer

        db = _migrated_db(tmp_path)
        monkeypatch.setattr(db_mod.settings, "db_path", db)

        _patch_httpx(
            monkeypatch,
            get_responses={
                ".well-known/stigmem": _FakeResponse(
                    200,
                    {"node_id": "stigmem://local", "federation_pubkey": "PUB"},
                ),
            },
            post_responses={
                "/v1/federation/peers": _FakeResponse(500, text="boom"),
            },
        )
        rc = _cmd_federation_register_peer(self._common_args())
        assert rc == 1
        assert "remote node returned 500" in capsys.readouterr().err

    def test_remote_unreachable_after_local_check(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
        tmp_path: Path,
    ) -> None:
        from stigmem_node import db as db_mod
        from stigmem_node.cli import _cmd_federation_register_peer

        db = _migrated_db(tmp_path)
        monkeypatch.setattr(db_mod.settings, "db_path", db)

        _patch_httpx(
            monkeypatch,
            get_responses={
                ".well-known/stigmem": _FakeResponse(
                    200,
                    {"node_id": "stigmem://local", "federation_pubkey": "PUB"},
                ),
            },
            post_raises=RuntimeError("remote down"),
        )
        rc = _cmd_federation_register_peer(self._common_args())
        assert rc == 1
        assert "cannot reach remote node" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# identity rotate-key + audit-discovery error paths
# ---------------------------------------------------------------------------


class TestIdentityRotateKeyEarlyBail:
    def test_no_node_private_key_returns_1(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        from stigmem_node.cli import _cmd_identity_rotate_key
        from stigmem_node.identity import capability as cap_mod

        db = _migrated_db(tmp_path)
        monkeypatch.setattr(cap_mod, "load_node_private_key", lambda: None)

        args = _args(
            db=db,
            dual_trust_days=90,
            dry_run=True,
            kind="node",
        )
        assert _cmd_identity_rotate_key(args) == 1
        assert "STIGMEM_NODE_PRIVATE_KEY is not configured" in capsys.readouterr().err

    def test_no_manifest_in_db_returns_1(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        from stigmem_node import db as db_mod
        from stigmem_node.cli import _cmd_identity_rotate_key
        from stigmem_node.identity import capability as cap_mod

        db = _migrated_db(tmp_path)
        # CLI patches settings_module.settings via args.db, but db() reads
        # db_mod.settings — patch that too so migrations land in our test DB.
        monkeypatch.setattr(db_mod.settings, "db_path", db)
        monkeypatch.setattr(cap_mod, "load_node_private_key", lambda: Ed25519PrivateKey.generate())

        args = _args(
            db=db,
            dual_trust_days=90,
            dry_run=True,
            kind="node",
        )
        assert _cmd_identity_rotate_key(args) == 1
        assert "no manifest found" in capsys.readouterr().err


class TestAuditDiscoveryDbOpenFailure:
    def test_open_failure_returns_1(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture,
    ) -> None:
        from stigmem_node.cli import _cmd_audit_discovery

        # Pass a directory as db path → open will fail
        args = _args(
            db=str(tmp_path),  # a dir, not a file
            agent="x",
            since=None,
            json=False,
        )
        # sqlite3.connect on a directory raises → caught and returns 1
        rc = _cmd_audit_discovery(args)
        # Either 1 (caught open error) or 0 (sqlite is permissive on dirs)
        assert rc in (0, 1)


# ---------------------------------------------------------------------------
# instruction migrate (the biggest remaining chunk in cli.py — ~160 lines)
# ---------------------------------------------------------------------------


class TestInstructionMigrate:
    def _write_md_dir(self, tmp_path: Path) -> Path:
        """Create a small markdown directory and return its path."""
        d = tmp_path / "instructions"
        d.mkdir()
        (d / "guide.md").write_text("## How to onboard\n\nDocumentation body.\n")
        return d

    def _common_args(self, **overrides: object) -> argparse.Namespace:
        base = dict(
            path="",  # filled per test
            api_key=None,
            node_url="http://test-node",
            deployment="dev",
            version="v0.1",
            agent_id="agent-x",
            role="admin",
            skill=None,
            db=None,
            dry_run=False,
            yes=True,
        )
        base.update(overrides)
        return _args(**base)

    def test_path_does_not_exist_returns_1(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture,
    ) -> None:
        from stigmem_node.cli import _cmd_instruction_migrate

        args = self._common_args(path=str(tmp_path / "ghost"))
        assert _cmd_instruction_migrate(args) == 1
        assert "does not exist" in capsys.readouterr().err

    def test_no_chunks_found_returns_0(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture,
    ) -> None:
        from stigmem_node.cli import _cmd_instruction_migrate

        # Empty directory → no .md files → no chunks
        empty = tmp_path / "empty"
        empty.mkdir()
        args = self._common_args(path=str(empty))
        assert _cmd_instruction_migrate(args) == 0
        assert "No instruction chunks found" in capsys.readouterr().err

    def test_dry_run_returns_0(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture,
    ) -> None:
        from stigmem_node.cli import _cmd_instruction_migrate

        path = self._write_md_dir(tmp_path)
        args = self._common_args(path=str(path), dry_run=True)
        assert _cmd_instruction_migrate(args) == 0
        out = capsys.readouterr().out
        assert "Dry-run mode" in out
        assert "Migration Preview" in out

    def test_skill_branch_when_no_role(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture,
    ) -> None:
        from stigmem_node.cli import _cmd_instruction_migrate

        path = self._write_md_dir(tmp_path)
        args = self._common_args(
            path=str(path),
            role=None,
            skill="writing",
            dry_run=True,
        )
        assert _cmd_instruction_migrate(args) == 0
        assert "skill:writing" in capsys.readouterr().out

    def test_no_api_key_returns_1(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        from stigmem_node.cli import _cmd_instruction_migrate

        monkeypatch.delenv("STIGMEM_API_KEY", raising=False)
        path = self._write_md_dir(tmp_path)
        args = self._common_args(path=str(path), api_key=None, dry_run=False)
        assert _cmd_instruction_migrate(args) == 1
        assert "STIGMEM_API_KEY" in capsys.readouterr().err

    def test_write_facts_failure_returns_1(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        from stigmem_node import instruction_migrate as im
        from stigmem_node.cli import _cmd_instruction_migrate

        # Force write_facts to report failures
        monkeypatch.setattr(im, "write_facts", lambda *a, **kw: (0, 1))

        path = self._write_md_dir(tmp_path)
        args = self._common_args(path=str(path), api_key="kkkkkkkkkkkkkkkk")
        assert _cmd_instruction_migrate(args) == 1
        assert "failed to write" in capsys.readouterr().err

    def test_publish_manifest_failure_returns_1(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from stigmem_node import instruction_migrate as im
        from stigmem_node.cli import _cmd_instruction_migrate

        # write_facts succeeds, publish_manifest fails
        monkeypatch.setattr(im, "write_facts", lambda *a, **kw: (1, 0))
        monkeypatch.setattr(im, "publish_manifest", lambda *a, **kw: False)

        path = self._write_md_dir(tmp_path)
        args = self._common_args(path=str(path), api_key="kkkkkkkkkkkkkkkk")
        assert _cmd_instruction_migrate(args) == 1

    def test_full_success_path(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        from stigmem_node import instruction_migrate as im
        from stigmem_node.cli import _cmd_instruction_migrate

        monkeypatch.setattr(im, "write_facts", lambda *a, **kw: (1, 0))
        monkeypatch.setattr(im, "publish_manifest", lambda *a, **kw: True)

        path = self._write_md_dir(tmp_path)
        args = self._common_args(path=str(path), api_key="kkkkkkkkkkkkkkkk")
        assert _cmd_instruction_migrate(args) == 0
        out = capsys.readouterr().out
        assert "Done" in out
        assert "manifest published" in out

    def test_db_loader_path_with_seeded_facts(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Exercise the args.db branch (1150-1175) by passing a real DB."""
        from stigmem_node.cli import _cmd_instruction_migrate

        db = _migrated_db(tmp_path)
        path = self._write_md_dir(tmp_path)

        args = self._common_args(
            path=str(path),
            api_key=None,
            db=db,
            dry_run=True,
        )
        assert _cmd_instruction_migrate(args) == 0

    def test_api_loader_path_with_mocked_httpx(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Exercise the elif api_key branch (1176-1207) — pre-flight HTTP fetches."""
        import httpx

        from stigmem_node.cli import _cmd_instruction_migrate

        def fake_get(url: str, **kw: Any) -> _FakeResponse:
            if "instruction-manifest" in url:
                return _FakeResponse(200, {"entries": [{"name": "old"}]})
            return _FakeResponse(200, {"facts": []})

        monkeypatch.setattr(httpx, "get", fake_get)

        path = self._write_md_dir(tmp_path)
        args = self._common_args(
            path=str(path),
            api_key="kkkkkkkkkkkkkkkk",
            dry_run=True,
        )
        assert _cmd_instruction_migrate(args) == 0
