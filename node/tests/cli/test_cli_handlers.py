"""B1 coverage push for stigmem_node.cli — direct invocations of the
command handler functions with httpx and the local DB monkey-patched.

The handlers were 22% covered because the CLI is normally invoked as a
subprocess; here we bypass argparse and call the ``_cmd_*`` functions
directly with fabricated argparse.Namespace objects, exercising both
success and error branches without any real HTTP or external services.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _args(**kwargs: object) -> argparse.Namespace:
    return argparse.Namespace(**kwargs)


class _FakeResponse:
    """Stand-in for httpx.Response used by handler tests."""

    def __init__(self, status_code: int, json_body: Any = None, text: str = "") -> None:
        self.status_code = status_code
        self._json = json_body if json_body is not None else {}
        self.text = text or json.dumps(self._json)

    def json(self) -> Any:
        return self._json

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def _patch_httpx_post(monkeypatch: pytest.MonkeyPatch, response: _FakeResponse) -> dict:
    """Patch httpx.post; return captured call kwargs."""
    captured: dict = {}

    def fake_post(url: str, **kw: Any) -> _FakeResponse:
        captured["url"] = url
        captured.update(kw)
        return response

    import httpx

    monkeypatch.setattr(httpx, "post", fake_post)
    return captured


def _patch_httpx_post_raises(monkeypatch: pytest.MonkeyPatch, exc: Exception) -> None:
    def fake_post(*a: Any, **kw: Any) -> Any:
        raise exc

    import httpx

    monkeypatch.setattr(httpx, "post", fake_post)


def _migrated_db(tmp_path: Path) -> str:
    """Return path to a freshly-migrated test SQLite DB."""
    from stigmem_node.db import apply_migrations

    db_file = str(tmp_path / "cli_test.db")
    apply_migrations(db_path=db_file)
    return db_file


# ---------------------------------------------------------------------------
# capability issue / verify / revoke
# ---------------------------------------------------------------------------


class TestCapabilityIssue:
    def test_success_human_readable_output(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        from stigmem_node.cli import _cmd_capability_issue

        _patch_httpx_post(
            monkeypatch,
            _FakeResponse(
                201,
                {
                    "token_id": "tok-1",
                    "issuer": "stigmem://node-a",
                    "subject": "stigmem://node-b",
                    "verb": "read",
                    "object": "stigmem://facts",
                    "expiry": "2026-12-31T00:00:00Z",
                    "token_json": "{...}",
                },
            ),
        )
        args = _args(
            issuer="stigmem://node-a",
            subject="stigmem://node-b",
            verb="read",
            object="stigmem://facts",
            ttl_seconds=3600,
            node_url="http://localhost:8765/",
            api_key="k1",
            json=False,
        )
        rc = _cmd_capability_issue(args)
        out = capsys.readouterr().out
        assert rc == 0
        assert "tok-1" in out
        assert "stigmem://node-a" in out

    def test_success_json_output(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        from stigmem_node.cli import _cmd_capability_issue

        _patch_httpx_post(
            monkeypatch,
            _FakeResponse(
                201,
                {
                    "token_id": "t",
                    "issuer": "a",
                    "subject": "b",
                    "verb": "v",
                    "object": "o",
                    "expiry": "x",
                    "token_json": "{}",
                },
            ),
        )
        args = _args(
            issuer="a",
            subject="b",
            verb="v",
            object="o",
            ttl_seconds=None,
            node_url="http://localhost:8765",
            api_key=None,
            json=True,
        )
        rc = _cmd_capability_issue(args)
        assert rc == 0
        # JSON mode prints raw JSON to stdout
        assert "token_id" in capsys.readouterr().out

    def test_network_failure_returns_1(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        from stigmem_node.cli import _cmd_capability_issue

        _patch_httpx_post_raises(monkeypatch, RuntimeError("connect refused"))
        args = _args(
            issuer="a",
            subject="b",
            verb="v",
            object="o",
            ttl_seconds=None,
            node_url="http://localhost:8765",
            api_key=None,
            json=False,
        )
        rc = _cmd_capability_issue(args)
        assert rc == 1
        assert "cannot reach node" in capsys.readouterr().err

    def test_bad_status_returns_1(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from stigmem_node.cli import _cmd_capability_issue

        _patch_httpx_post(monkeypatch, _FakeResponse(500, text="boom"))
        args = _args(
            issuer="a",
            subject="b",
            verb="v",
            object="o",
            ttl_seconds=None,
            node_url="http://localhost:8765",
            api_key="k",
            json=False,
        )
        assert _cmd_capability_issue(args) == 1


class TestPluginsCli:
    def test_list_no_plugins(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        import stigmem_node.plugins.lifecycle as lifecycle
        from stigmem_node.cli import _cmd_plugins_list

        monkeypatch.setattr(lifecycle, "discover_plugin_manifests", lambda: ())

        rc = _cmd_plugins_list(_args(json=False))

        assert rc == 0
        assert "No plugins registered" in capsys.readouterr().out

    def test_list_plugins_json(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        import stigmem_node.plugins.lifecycle as lifecycle
        import stigmem_node.settings as settings_module
        from stigmem_node.cli import _cmd_plugins_list
        from stigmem_node.plugins import (
            DiscoveredPlugin,
            PluginContext,
            PluginHealth,
            PluginHealthStatus,
            PluginManifest,
        )

        def health(_ctx: PluginContext) -> PluginHealth:
            return PluginHealth(PluginHealthStatus.HEALTHY, "ready")

        manifest = PluginManifest(
            name="cli-plugin",
            version="1.2.3",
            capabilities=frozenset({"audit.emit"}),
            hooks={},
            health_check=health,
        )
        discovered = DiscoveredPlugin(
            manifest=manifest,
            entry_point_name="cli-plugin",
            entry_point_value="pkg:manifest",
            distribution="pkg",
        )
        monkeypatch.setattr(lifecycle, "discover_plugin_manifests", lambda: (discovered,))
        monkeypatch.setattr(settings_module.settings, "plugin_signing_required", False)
        monkeypatch.setattr(lifecycle.settings, "plugin_signing_required", False)

        rc = _cmd_plugins_list(_args(json=True))
        payload = json.loads(capsys.readouterr().out)

        assert rc == 0
        assert payload[0]["name"] == "cli-plugin"
        assert payload[0]["version"] == "1.2.3"
        assert payload[0]["capabilities"] == ["audit.emit"]
        assert payload[0]["hook_count"] == 0
        assert payload[0]["signed_by"] == "unsigned"
        assert payload[0]["health"]["status"] == "healthy"

    def test_describe_plugin_human_output(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        import stigmem_node.plugins.lifecycle as lifecycle
        import stigmem_node.settings as settings_module
        from stigmem_node.cli import _cmd_plugins_describe
        from stigmem_node.plugins import Allow, DiscoveredPlugin, PluginContext, PluginManifest

        def handler(_ctx: PluginContext, **_: object) -> Allow:
            return Allow()

        manifest = PluginManifest(
            name="describe-plugin",
            version="2.0.0",
            capabilities=frozenset({"facts.read"}),
            hooks={"pre_assert_authorize": handler},
            depends_on=frozenset({"base-plugin"}),
        )
        base = PluginManifest(
            name="base-plugin",
            version="1.0.0",
            hooks={},
        )
        discovered = DiscoveredPlugin(
            manifest=manifest,
            entry_point_name="describe-plugin",
            entry_point_value="pkg:manifest",
            distribution="pkg",
        )
        base_discovered = DiscoveredPlugin(
            manifest=base,
            entry_point_name="base-plugin",
            entry_point_value="base:manifest",
            distribution="base",
        )
        monkeypatch.setattr(
            lifecycle,
            "discover_plugin_manifests",
            lambda: (discovered, base_discovered),
        )
        monkeypatch.setattr(settings_module.settings, "plugin_signing_required", False)
        monkeypatch.setattr(lifecycle.settings, "plugin_signing_required", False)

        rc = _cmd_plugins_describe(_args(name="describe-plugin", json=False))
        out = capsys.readouterr().out

        assert rc == 0
        assert "name: describe-plugin" in out
        assert "version: 2.0.0" in out
        assert "capabilities: facts.read" in out
        assert "hooks (1): pre_assert_authorize" in out
        assert "depends_on: base-plugin" in out
        assert "signed_by: unsigned" in out
        assert "health: unknown" in out

    def test_describe_unknown_plugin_returns_nonzero(
        self,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        import stigmem_node.plugins.lifecycle as lifecycle
        from stigmem_node.cli import _cmd_plugins_describe

        monkeypatch.setattr(lifecycle, "discover_plugin_manifests", lambda: ())

        rc = _cmd_plugins_describe(_args(name="missing-plugin", json=False))

        assert rc == 1
        assert "plugin not found: missing-plugin" in capsys.readouterr().err


class TestCapabilityVerify:
    def test_valid_token_human_output(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        from stigmem_node.cli import _cmd_capability_verify

        _patch_httpx_post(monkeypatch, _FakeResponse(200, {"valid": True}))
        args = _args(token_json="{}", node_url="http://x", api_key=None, json=False)
        assert _cmd_capability_verify(args) == 0
        assert "valid: True" in capsys.readouterr().out

    def test_invalid_token_human_output(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        from stigmem_node.cli import _cmd_capability_verify

        _patch_httpx_post(monkeypatch, _FakeResponse(200, {"valid": False, "reason": "expired"}))
        args = _args(token_json="{}", node_url="http://x", api_key="k", json=False)
        assert _cmd_capability_verify(args) == 0
        out = capsys.readouterr().out
        assert "valid: False" in out
        assert "expired" in out

    def test_json_output(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        from stigmem_node.cli import _cmd_capability_verify

        _patch_httpx_post(monkeypatch, _FakeResponse(200, {"valid": True}))
        args = _args(token_json="{}", node_url="http://x", api_key=None, json=True)
        assert _cmd_capability_verify(args) == 0
        assert '"valid"' in capsys.readouterr().out

    def test_422_treats_token_as_invalid(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        from stigmem_node.cli import _cmd_capability_verify

        _patch_httpx_post(monkeypatch, _FakeResponse(422, {"detail": "malformed"}))
        args = _args(token_json="{}", node_url="http://x", api_key=None, json=False)
        assert _cmd_capability_verify(args) == 1
        assert "invalid" in capsys.readouterr().err

    def test_400_bad_request_handled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from stigmem_node.cli import _cmd_capability_verify

        # Force the json() fallback by returning a non-JSON-ish 400
        class _BadJSON(_FakeResponse):
            def json(self) -> Any:
                raise ValueError("not json")

        monkeypatch.setattr(
            __import__("httpx"),
            "post",
            lambda *a, **kw: _BadJSON(400, text="raw error body"),
        )
        args = _args(token_json="{}", node_url="http://x", api_key=None, json=False)
        assert _cmd_capability_verify(args) == 1

    def test_500_error_returns_1(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from stigmem_node.cli import _cmd_capability_verify

        _patch_httpx_post(monkeypatch, _FakeResponse(500, text="boom"))
        args = _args(token_json="{}", node_url="http://x", api_key=None, json=False)
        assert _cmd_capability_verify(args) == 1

    def test_network_failure(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        from stigmem_node.cli import _cmd_capability_verify

        _patch_httpx_post_raises(monkeypatch, RuntimeError("down"))
        args = _args(token_json="{}", node_url="http://x", api_key=None, json=False)
        assert _cmd_capability_verify(args) == 1
        assert "cannot reach node" in capsys.readouterr().err


class TestCapabilityRevoke:
    def _args(self, **overrides: object) -> argparse.Namespace:
        base = dict(
            token_id="tok-1",
            reason="testing",
            node_url="http://x",
            api_key=None,
            json=False,
        )
        base.update(overrides)
        return _args(**base)

    def test_success_human_output(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        from stigmem_node.cli import _cmd_capability_revoke

        _patch_httpx_post(
            monkeypatch,
            _FakeResponse(200, {"token_id": "tok-1", "revoked_at": "2026-01-01T00:00:00Z"}),
        )
        assert _cmd_capability_revoke(self._args()) == 0
        assert "revoked: tok-1" in capsys.readouterr().out

    def test_success_json_output(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from stigmem_node.cli import _cmd_capability_revoke

        _patch_httpx_post(monkeypatch, _FakeResponse(200, {"token_id": "tok-1", "revoked_at": "x"}))
        assert _cmd_capability_revoke(self._args(json=True, api_key="k")) == 0

    def test_404_not_found(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        from stigmem_node.cli import _cmd_capability_revoke

        _patch_httpx_post(monkeypatch, _FakeResponse(404, text="not found"))
        assert _cmd_capability_revoke(self._args()) == 1
        assert "token not found" in capsys.readouterr().err

    def test_409_already_revoked(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
    ) -> None:
        from stigmem_node.cli import _cmd_capability_revoke

        _patch_httpx_post(monkeypatch, _FakeResponse(409, text="dup"))
        assert _cmd_capability_revoke(self._args()) == 1
        assert "already revoked" in capsys.readouterr().err

    def test_other_error_returns_1(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from stigmem_node.cli import _cmd_capability_revoke

        _patch_httpx_post(monkeypatch, _FakeResponse(500, text="boom"))
        assert _cmd_capability_revoke(self._args()) == 1

    def test_network_failure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from stigmem_node.cli import _cmd_capability_revoke

        _patch_httpx_post_raises(monkeypatch, RuntimeError("net"))
        assert _cmd_capability_revoke(self._args()) == 1

    def test_no_reason_omits_reason_field(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from stigmem_node.cli import _cmd_capability_revoke

        captured = _patch_httpx_post(
            monkeypatch, _FakeResponse(200, {"token_id": "t", "revoked_at": "x"})
        )
        assert _cmd_capability_revoke(self._args(reason=None)) == 0
        assert "reason" not in captured["json"]


# ---------------------------------------------------------------------------
# decay sweep / migrate normalize entities
# ---------------------------------------------------------------------------


class TestDecaySweep:
    def test_dry_run_prints_scanned_count(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from stigmem_node import db as db_mod
        from stigmem_node.cli import _cmd_decay_sweep

        db = _migrated_db(tmp_path)
        # decay sweep uses module-level settings.db_path under the hood
        monkeypatch.setattr(db_mod.settings, "db_path", db)

        args = _args(
            db=db,
            ttl_seconds=86400,
            min_confidence=0.5,
            scope="local",
            dry_run=True,
        )
        assert _cmd_decay_sweep(args) == 0
        assert "[dry-run]" in capsys.readouterr().err

    def test_live_run_prints_decayed_count(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from stigmem_node import db as db_mod
        from stigmem_node.cli import _cmd_decay_sweep

        db = _migrated_db(tmp_path)
        monkeypatch.setattr(db_mod.settings, "db_path", db)

        args = _args(
            db=db,
            ttl_seconds=86400,
            min_confidence=0.0,
            scope=None,
            dry_run=False,
        )
        assert _cmd_decay_sweep(args) == 0
        assert "decayed" in capsys.readouterr().err


class TestMigrateNormalizeEntities:
    def test_dry_run(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        from stigmem_node.cli import _cmd_migrate_normalize_entities

        db = _migrated_db(tmp_path)
        args = _args(db=db, dry_run=True)
        assert _cmd_migrate_normalize_entities(args) == 0
        assert "[dry-run]" in capsys.readouterr().err

    def test_live_run(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        from stigmem_node.cli import _cmd_migrate_normalize_entities

        db = _migrated_db(tmp_path)
        args = _args(db=db, dry_run=False)
        assert _cmd_migrate_normalize_entities(args) == 0
        assert "registered" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# federation cursor export / import
# ---------------------------------------------------------------------------


class TestFederationCursorExport:
    def test_export_empty_db_to_stdout(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        from stigmem_node.cli import _cmd_federation_cursor_export

        db = _migrated_db(tmp_path)
        args = _args(db=db, out="-")
        assert _cmd_federation_cursor_export(args) == 0
        out = capsys.readouterr().out
        payload = json.loads(out)
        assert payload["cursors"] == []
        assert "checkpoint_timestamp" in payload

    def test_export_with_rows_to_file(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        from stigmem_node.cli import _cmd_federation_cursor_export

        db = _migrated_db(tmp_path)
        # Seed a peer + cursor row
        conn = sqlite3.connect(db)
        conn.execute(
            "INSERT INTO peers (id, node_id, node_url, status, federation_pubkey, "
            "allowed_scopes, signed_at, declaration_sig) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("p1", "stigmem://peer1", "http://p1", "active", "pub", "[]", "now", "sig"),
        )
        conn.execute(
            "INSERT INTO replication_cursors (peer_id, direction, cursor, updated_at) "
            "VALUES (?, ?, ?, ?)",
            ("p1", "inbound", "abc123", "now"),
        )
        conn.commit()
        conn.close()

        out_path = tmp_path / "cp.json"
        args = _args(db=db, out=str(out_path))
        assert _cmd_federation_cursor_export(args) == 0
        assert "checkpoint written" in capsys.readouterr().err
        payload = json.loads(out_path.read_text())
        assert len(payload["cursors"]) == 1
        assert payload["cursors"][0]["cursor"] == "abc123"


class TestFederationCursorImport:
    def test_import_unreadable_file(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        from stigmem_node.cli import _cmd_federation_cursor_import

        db = _migrated_db(tmp_path)
        args = _args(db=db, checkpoint_file=str(tmp_path / "nope.json"), force=False)
        assert _cmd_federation_cursor_import(args) == 1
        assert "cannot read checkpoint" in capsys.readouterr().err

    def test_import_bad_shape(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        from stigmem_node.cli import _cmd_federation_cursor_import

        db = _migrated_db(tmp_path)
        bad = tmp_path / "bad.json"
        bad.write_text(json.dumps({"checkpoint_timestamp": "x"}))  # no "cursors"
        args = _args(db=db, checkpoint_file=str(bad), force=False)
        assert _cmd_federation_cursor_import(args) == 1
        assert "checkpoint missing" in capsys.readouterr().err

    def test_import_skips_missing_peer(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        from stigmem_node.cli import _cmd_federation_cursor_import

        db = _migrated_db(tmp_path)
        cp = tmp_path / "cp.json"
        cp.write_text(
            json.dumps(
                {
                    "cursors": [
                        {
                            "peer_id": "ghost",
                            "direction": "pull",
                            "cursor": "x",
                            "peer_node_id": "stigmem://ghost",
                        },
                    ],
                }
            )
        )
        args = _args(db=db, checkpoint_file=str(cp), force=False)
        assert _cmd_federation_cursor_import(args) == 0
        err = capsys.readouterr().err
        assert "not found in peers table" in err
        assert "0 restored" in err

    def test_import_idempotent_when_cursor_exists(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        from stigmem_node.cli import _cmd_federation_cursor_import

        db = _migrated_db(tmp_path)
        # Seed peer + existing cursor
        conn = sqlite3.connect(db)
        conn.execute(
            "INSERT INTO peers (id, node_id, node_url, status, federation_pubkey, "
            "allowed_scopes, signed_at, declaration_sig) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("p1", "stigmem://p1", "http://p1", "active", "pub", "[]", "now", "sig"),
        )
        conn.execute(
            "INSERT INTO replication_cursors (peer_id, direction, cursor, updated_at) "
            "VALUES (?, ?, ?, ?)",
            ("p1", "inbound", "existing", "now"),
        )
        conn.commit()
        conn.close()

        cp = tmp_path / "cp.json"
        cp.write_text(
            json.dumps(
                {
                    "cursors": [{"peer_id": "p1", "direction": "inbound", "cursor": "new"}],
                }
            )
        )
        # Without --force, the existing cursor is preserved
        args = _args(db=db, checkpoint_file=str(cp), force=False)
        assert _cmd_federation_cursor_import(args) == 0
        assert "already set" in capsys.readouterr().err

        # With --force, overwritten
        args2 = _args(db=db, checkpoint_file=str(cp), force=True)
        assert _cmd_federation_cursor_import(args2) == 0
        conn = sqlite3.connect(db)
        cur = conn.execute(
            "SELECT cursor FROM replication_cursors WHERE peer_id='p1' AND direction='inbound'"
        ).fetchone()
        conn.close()
        assert cur[0] == "new"

    def test_import_skips_malformed_entry(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        from stigmem_node.cli import _cmd_federation_cursor_import

        db = _migrated_db(tmp_path)
        cp = tmp_path / "cp.json"
        cp.write_text(
            json.dumps(
                {
                    "cursors": [
                        {"peer_id": "", "direction": "pull"},  # missing peer_id
                        {"direction": "pull", "cursor": "x"},  # missing peer_id entirely
                    ],
                }
            )
        )
        args = _args(db=db, checkpoint_file=str(cp), force=False)
        assert _cmd_federation_cursor_import(args) == 0
        assert "malformed" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# audit discovery
# ---------------------------------------------------------------------------


def _seed_audit_event(
    db_path: str,
    *,
    agent: str,
    loaded: list[str],
    used: list[str],
    missed: list[str],
    session_ms: int,
) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute(
        """INSERT INTO instruction_audit
           (id, agent_id, heartbeat_id, session_start, intent,
            loaded_chunks, used_chunks, missed_chunks, audit_token, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            f"audevent_{session_ms}",
            agent,
            f"hb_{session_ms}",
            session_ms,
            "test",
            json.dumps(loaded),
            json.dumps(used),
            json.dumps(missed),
            f"tok_{session_ms}",
            session_ms,
        ),
    )
    conn.commit()
    conn.close()


class TestAuditDiscovery:
    def test_no_records_prints_friendly_message(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture,
    ) -> None:
        from stigmem_node.cli import _cmd_audit_discovery

        db = _migrated_db(tmp_path)
        args = _args(db=db, agent="ghost", since=None, json=False)
        assert _cmd_audit_discovery(args) == 0
        assert "No audit records" in capsys.readouterr().out

    def test_invalid_since_returns_1(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture,
    ) -> None:
        from stigmem_node.cli import _cmd_audit_discovery

        db = _migrated_db(tmp_path)
        args = _args(db=db, agent="x", since="not-a-date", json=False)
        assert _cmd_audit_discovery(args) == 1
        assert "invalid --since" in capsys.readouterr().err

    def test_summary_human_output(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture,
    ) -> None:
        import time as _time

        from stigmem_node.cli import _cmd_audit_discovery

        db = _migrated_db(tmp_path)
        now_ms = int(_time.time() * 1000)
        # Two events, both partial recall: loaded {a,b}, used {a,c} (missed c)
        _seed_audit_event(
            db, agent="agent-1", loaded=["a", "b"], used=["a", "c"], missed=["c"], session_ms=now_ms
        )
        _seed_audit_event(
            db, agent="agent-1", loaded=["a", "b"], used=["b"], missed=[], session_ms=now_ms - 1000
        )

        args = _args(db=db, agent="agent-1", since=None, json=False)
        assert _cmd_audit_discovery(args) == 0
        out = capsys.readouterr().out
        assert "Recall@k" in out
        assert "Hit@k" in out
        assert "Miss rate" in out

    def test_high_miss_rate_triggers_alert(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture,
    ) -> None:
        import time as _time

        from stigmem_node.cli import _cmd_audit_discovery

        db = _migrated_db(tmp_path)
        now_ms = int(_time.time() * 1000)
        # used=[], missed=many → miss_rate = 1.0
        _seed_audit_event(
            db,
            agent="bad-agent",
            loaded=["x"],
            used=["x"],
            missed=["m1", "m2", "m3", "m4"],
            session_ms=now_ms,
        )

        args = _args(db=db, agent="bad-agent", since=None, json=False)
        assert _cmd_audit_discovery(args) == 0
        assert "ALERT" in capsys.readouterr().out

    def test_json_output(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture,
    ) -> None:
        import time as _time

        from stigmem_node.cli import _cmd_audit_discovery

        db = _migrated_db(tmp_path)
        now_ms = int(_time.time() * 1000)
        _seed_audit_event(
            db, agent="json-agent", loaded=["a"], used=["a"], missed=[], session_ms=now_ms
        )

        args = _args(db=db, agent="json-agent", since=None, json=True)
        assert _cmd_audit_discovery(args) == 0
        report = json.loads(capsys.readouterr().out)
        assert report["agent"] == "json-agent"
        assert report["total_events"] == 1


# ---------------------------------------------------------------------------
# snapshot create / restore
# ---------------------------------------------------------------------------


class TestSnapshotCreate:
    def test_create_default_path(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        from stigmem_node.cli import _cmd_snapshot_create

        db = _migrated_db(tmp_path)
        # snapshot_create defaults to writing into the cwd; chdir so it lands in tmp_path
        monkeypatch.chdir(tmp_path)
        args = _args(db=db, out=str(tmp_path / "snap.tar"), sign_with=None)
        assert _cmd_snapshot_create(args) == 0
        assert "snapshot created" in capsys.readouterr().err
        assert (tmp_path / "snap.tar").exists()


class TestSnapshotRestore:
    def test_restore_unverified_succeeds_with_force(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture,
    ) -> None:
        from stigmem_node.cli import _cmd_snapshot_create, _cmd_snapshot_restore

        db = _migrated_db(tmp_path)
        monkeypatch.chdir(tmp_path)

        # Create a snapshot tarball first
        snap_path = str(tmp_path / "round_trip.tar")
        create_args = _args(db=db, out=snap_path, sign_with=None)
        assert _cmd_snapshot_create(create_args) == 0

        # Now restore from it (force_unverified=True since unsigned)
        restore_db = str(tmp_path / "restored.db")
        restore_args = _args(
            db=restore_db,
            from_path=snap_path,
            trusted_keys=None,
            force_unverified=True,
        )
        assert _cmd_snapshot_restore(restore_args) == 0
        assert "snapshot restored" in capsys.readouterr().err

    def test_restore_verification_failure_returns_1(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from stigmem_node import snapshot as snap_mod
        from stigmem_node.cli import _cmd_snapshot_restore

        db = _migrated_db(tmp_path)

        def _raises(*a: Any, **kw: Any) -> None:
            raise snap_mod.SnapshotVerificationError("bad signature")

        monkeypatch.setattr(snap_mod, "snapshot_restore", _raises)

        args = _args(
            db=db,
            from_path=str(tmp_path / "any.tar"),
            trusted_keys=None,
            force_unverified=False,
        )
        assert _cmd_snapshot_restore(args) == 1
        assert "error" in capsys.readouterr().err
