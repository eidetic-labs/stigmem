from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import pytest


def _args(**kwargs: object) -> argparse.Namespace:
    return argparse.Namespace(**kwargs)


def test_mcp_config_lists_editors(capsys: pytest.CaptureFixture[str]) -> None:
    import stigmem_node.cli.mcp as mcp

    rc = mcp._cmd_mcp_config(_args(list=True, editor=None))

    out = capsys.readouterr().out
    assert rc == 0
    assert "codex-cli" in out
    assert "claude-code" in out


def test_mcp_config_emits_codex_metadata(capsys: pytest.CaptureFixture[str]) -> None:
    import stigmem_node.cli.mcp as mcp

    rc = mcp._cmd_mcp_config(
        _args(
            list=False,
            editor="codex-cli",
            stigmem_url="http://node.example",
            stigmem_api_key="sk-test",
        )
    )

    out = capsys.readouterr().out
    assert rc == 0
    assert "codex-cli" in out
    assert "~/.codex/config.toml" in out
    assert "integrations/mcp/codex-cli" in out
    assert "sk-test" not in out


def test_mcp_config_rejects_unknown_editor(capsys: pytest.CaptureFixture[str]) -> None:
    import stigmem_node.cli.mcp as mcp

    rc = mcp._cmd_mcp_config(
        _args(
            list=False,
            editor="unknown",
            stigmem_url="http://localhost:8765",
            stigmem_api_key="sk",
        )
    )

    assert rc == 1
    assert "unknown MCP editor" in capsys.readouterr().out


def test_mcp_detect_json_uses_home(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import stigmem_node.cli.mcp as mcp

    monkeypatch.setenv("HOME", str(tmp_path))
    codex = tmp_path / ".codex"
    codex.mkdir()
    (codex / "config.toml").write_text('[mcp_servers.stigmem]\ncommand = "stigmem-mcp"\n')

    rc = mcp._cmd_mcp_detect(_args(json=True))
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload["codex-cli"]["config_exists"] is True
    assert payload["codex-cli"]["has_stigmem_mcp"] is True


def test_mcp_install_dry_run_does_not_write(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import stigmem_node.cli.mcp as mcp

    monkeypatch.setenv("HOME", str(tmp_path))
    rc = mcp._cmd_mcp_install(
        _args(
            editor="codex-cli",
            write=False,
            force=False,
            yes=True,
            backup_dir=None,
            stigmem_url="http://localhost:8765",
            stigmem_api_key="sk",
        )
    )

    assert rc == 0
    assert "Dry-run only" in capsys.readouterr().out
    assert not (tmp_path / ".codex" / "config.toml").exists()


def test_mcp_install_warns_when_api_key_sourced_from_env(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import stigmem_node.cli.mcp as mcp

    api_key = "sk-test-1234567890abcdef"
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("STIGMEM_API_KEY", api_key)

    rc = mcp._cmd_mcp_install(
        _args(
            editor="codex-cli",
            write=False,
            force=False,
            yes=True,
            backup_dir=None,
            stigmem_url="http://localhost:8765",
            stigmem_api_key=api_key,
        )
    )

    out = capsys.readouterr().out
    assert rc == 0
    assert "$STIGMEM_API_KEY environment variable" in out
    assert "Press Ctrl-C" in out
    assert api_key not in out


def test_mcp_install_warns_when_api_key_is_placeholder(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import stigmem_node.cli.mcp as mcp

    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("STIGMEM_API_KEY", raising=False)

    rc = mcp._cmd_mcp_install(
        _args(
            editor="codex-cli",
            write=False,
            force=False,
            yes=True,
            backup_dir=None,
            stigmem_url="http://localhost:8765",
            stigmem_api_key="<your-api-key>",
        )
    )

    out = capsys.readouterr().out
    assert rc == 0
    assert "placeholder (you must edit the file before use)" in out


def test_mcp_install_dry_run_prints_merged_config_body_with_key_redacted(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import stigmem_node.cli.mcp as mcp

    api_key = "test-key-12345"
    monkeypatch.setenv("HOME", str(tmp_path))

    rc = mcp._cmd_mcp_install(
        _args(
            editor="codex-cli",
            write=False,
            force=False,
            yes=True,
            backup_dir=None,
            stigmem_url="http://localhost:8765",
            stigmem_api_key=api_key,
        )
    )

    out = capsys.readouterr().out
    assert rc == 0
    assert "--- planned config body" in out
    assert "<STIGMEM_API_KEY>" in out
    assert api_key not in out
    assert "--- end planned config body ---" in out


def test_mcp_install_write_creates_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import stigmem_node.cli.mcp as mcp

    monkeypatch.setenv("HOME", str(tmp_path))
    rc = mcp._cmd_mcp_install(
        _args(
            editor="codex-cli",
            write=True,
            force=False,
            yes=True,
            backup_dir=None,
            stigmem_url="http://localhost:8765",
            stigmem_api_key="sk",
        )
    )

    config = tmp_path / ".codex" / "config.toml"
    assert rc == 0
    assert config.exists()
    assert "stigmem-mcp" in config.read_text()


@pytest.mark.skipif(os.name != "posix", reason="POSIX permissions only")
def test_mcp_install_backup_file_is_owner_only(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import stigmem_node.cli.mcp as mcp

    monkeypatch.setenv("HOME", str(tmp_path))
    codex = tmp_path / ".codex"
    codex.mkdir()
    (codex / "config.toml").write_text("# existing operator content\n")
    backup_dir = tmp_path / "backups"

    rc = mcp._cmd_mcp_install(
        _args(
            editor="codex-cli",
            write=True,
            force=False,
            yes=True,
            backup_dir=str(backup_dir),
            stigmem_url="http://localhost:8765",
            stigmem_api_key="sk",
        )
    )

    out = capsys.readouterr().out
    backups = list(backup_dir.glob("config.toml.stigmem-bak-*"))
    assert rc == 0
    assert "owner-only mode" in out
    assert len(backups) == 1
    assert backups[0].stat().st_mode & 0o777 == 0o600


def test_mcp_install_refuses_existing_without_force(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import stigmem_node.cli.mcp as mcp

    monkeypatch.setenv("HOME", str(tmp_path))
    codex = tmp_path / ".codex"
    codex.mkdir()
    (codex / "config.toml").write_text('[mcp_servers.stigmem]\ncommand = "stigmem-mcp"\n')

    rc = mcp._cmd_mcp_install(
        _args(
            editor="codex-cli",
            write=True,
            force=False,
            yes=True,
            backup_dir=None,
            stigmem_url="http://localhost:8765",
            stigmem_api_key="sk",
        )
    )

    assert rc == 1


def test_mcp_smoke_checks_config_binary_and_script(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import stigmem_node.cli.mcp as mcp

    monkeypatch.setenv("HOME", str(tmp_path))
    codex = tmp_path / ".codex"
    codex.mkdir()
    (codex / "config.toml").write_text('[mcp_servers.stigmem]\ncommand = "stigmem-mcp"\n')
    monkeypatch.setattr(mcp.shutil, "which", lambda _name: "/usr/local/bin/stigmem-mcp")

    calls: list[list[str]] = []

    class Result:
        returncode = 0

    def fake_run(cmd: list[str], **_kwargs: Any) -> Result:
        calls.append(cmd)
        return Result()

    monkeypatch.setattr(mcp.subprocess, "run", fake_run)

    assert mcp._cmd_mcp_smoke(_args(editor="codex-cli")) == 0
    assert calls
