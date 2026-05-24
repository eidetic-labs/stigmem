"""MCP editor integration CLI handlers."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess  # nosec B404 - fixed-command local MCP diagnostics only.
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

ConfigFormat = Literal["toml", "json", "jsonc"]
ValidationTier = Literal["validated", "caveated", "experimental"]


@dataclass(frozen=True)
class EditorConfig:
    editor: str
    label: str
    validation_tier: ValidationTier
    config_path: str
    config_format: ConfigFormat
    docs_link: str
    config_template: str


EDITOR_CONFIGS: dict[str, EditorConfig] = {
    "codex-cli": EditorConfig(
        editor="codex-cli",
        label="Codex CLI",
        validation_tier="validated",
        config_path="~/.codex/config.toml",
        config_format="toml",
        docs_link="https://docs.stigmem.dev/en/latest/docs/integrations/mcp/codex-cli",
        config_template="""[mcp_servers.stigmem]
command = "stigmem-mcp"

[mcp_servers.stigmem.env]
STIGMEM_URL = "{stigmem_url}"
STIGMEM_API_KEY = "{stigmem_api_key}"
""",
    ),
    "claude-code": EditorConfig(
        editor="claude-code",
        label="Claude Code",
        validation_tier="validated",
        config_path="~/.claude/mcp_servers.json",
        config_format="json",
        docs_link="https://docs.stigmem.dev/en/latest/docs/integrations/mcp/claude-code",
        config_template="""{
  "mcpServers": {
    "stigmem": {
      "command": "stigmem-mcp",
      "env": {
        "STIGMEM_URL": "{stigmem_url}",
        "STIGMEM_API_KEY": "{stigmem_api_key}"
      }
    }
  }
}
""",
    ),
    "gemini-cli": EditorConfig(
        editor="gemini-cli",
        label="Gemini CLI",
        validation_tier="caveated",
        config_path="~/.gemini/settings.json",
        config_format="json",
        docs_link="https://docs.stigmem.dev/en/latest/docs/integrations/mcp/gemini-cli",
        config_template="""{
  "mcpServers": {
    "stigmem": {
      "command": "stigmem-mcp",
      "env": {
        "STIGMEM_URL": "{stigmem_url}",
        "STIGMEM_API_KEY": "{stigmem_api_key}"
      }
    }
  }
}
""",
    ),
    "continue-dev": EditorConfig(
        editor="continue-dev",
        label="Continue.dev",
        validation_tier="experimental",
        config_path="~/.continue/config.json",
        config_format="json",
        docs_link="https://docs.stigmem.dev/en/latest/docs/integrations/mcp/continue-dev",
        config_template="""{
  "mcpServers": [
    {
      "name": "stigmem",
      "command": "stigmem-mcp",
      "env": {
        "STIGMEM_URL": "{stigmem_url}",
        "STIGMEM_API_KEY": "{stigmem_api_key}"
      }
    }
  ]
}
""",
    ),
    "cursor": EditorConfig(
        editor="cursor",
        label="Cursor",
        validation_tier="experimental",
        config_path="~/.cursor/mcp.json",
        config_format="json",
        docs_link="https://docs.stigmem.dev/en/latest/docs/integrations/mcp/cursor",
        config_template="""{
  "mcpServers": {
    "stigmem": {
      "command": "stigmem-mcp",
      "env": {
        "STIGMEM_URL": "{stigmem_url}",
        "STIGMEM_API_KEY": "{stigmem_api_key}"
      }
    }
  }
}
""",
    ),
    "zed": EditorConfig(
        editor="zed",
        label="Zed",
        validation_tier="experimental",
        config_path="~/.config/zed/settings.json",
        config_format="jsonc",
        docs_link="https://docs.stigmem.dev/en/latest/docs/integrations/mcp/zed",
        config_template="""{
  "mcp_servers": {
    "stigmem": {
      "command": "stigmem-mcp",
      "env": {
        "STIGMEM_URL": "{stigmem_url}",
        "STIGMEM_API_KEY": "{stigmem_api_key}"
      }
    }
  }
}
""",
    ),
}


def editor_catalog() -> list[dict[str, str]]:
    """Return the supported MCP editor catalog as JSON-safe dictionaries."""
    return [
        {
            "editor": config.editor,
            "label": config.label,
            "validation_tier": config.validation_tier,
            "docs_link": config.docs_link,
            "config_path": config.config_path,
            "config_format": config.config_format,
        }
        for config in EDITOR_CONFIGS.values()
    ]


def _config_for(editor: str) -> EditorConfig | None:
    return EDITOR_CONFIGS.get(editor)


def _render_snippet(config: EditorConfig, stigmem_url: str, stigmem_api_key: str) -> str:
    return config.config_template.format(
        stigmem_url=stigmem_url,
        stigmem_api_key=stigmem_api_key,
    )


def _render_display_snippet(config: EditorConfig, stigmem_url: str) -> str:
    return _render_snippet(config, stigmem_url, "<redacted; set STIGMEM_API_KEY manually>")


def _json_stigmem_entry(stigmem_url: str, stigmem_api_key: str) -> dict[str, object]:
    return {
        "command": "stigmem-mcp",
        "env": {
            "STIGMEM_URL": stigmem_url,
            "STIGMEM_API_KEY": stigmem_api_key,
        },
    }


def _merge_json_config(
    editor: str,
    existing: str,
    stigmem_url: str,
    stigmem_api_key: str,
    fallback: str,
) -> str:
    if not existing.strip():
        return fallback
    try:
        data = json.loads(existing)
    except json.JSONDecodeError:
        return f"{existing.rstrip()}\n\n{fallback}"
    if not isinstance(data, dict):
        return fallback
    if editor == "continue-dev":
        current = data.get("mcpServers")
        server_list = current if isinstance(current, list) else []
        server_list = [server for server in server_list if not _server_named_stigmem(server)]
        server_list.append({"name": "stigmem", **_json_stigmem_entry(stigmem_url, stigmem_api_key)})
        data["mcpServers"] = server_list
    elif editor == "zed":
        current = data.get("mcp_servers")
        server_map = current if isinstance(current, dict) else {}
        server_map["stigmem"] = _json_stigmem_entry(stigmem_url, stigmem_api_key)
        data["mcp_servers"] = server_map
    else:
        current = data.get("mcpServers")
        server_map = current if isinstance(current, dict) else {}
        server_map["stigmem"] = _json_stigmem_entry(stigmem_url, stigmem_api_key)
        data["mcpServers"] = server_map
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


def _server_named_stigmem(server: object) -> bool:
    return isinstance(server, dict) and server.get("name") == "stigmem"


def _merge_config(
    config: EditorConfig,
    existing: str,
    stigmem_url: str,
    stigmem_api_key: str,
) -> str:
    snippet = _render_snippet(config, stigmem_url, stigmem_api_key)
    if not existing.strip():
        return snippet
    if config.config_format in {"json", "jsonc"}:
        return _merge_json_config(config.editor, existing, stigmem_url, stigmem_api_key, snippet)
    return f"{existing.rstrip()}\n\n# Added by stigmem mcp install at {_iso_timestamp()}\n{snippet}"


def _iso_timestamp() -> str:
    return dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H-%M-%SZ")


def _config_path(config: EditorConfig) -> Path:
    return Path(config.config_path).expanduser()


def _read_existing(path: Path) -> str:
    try:
        return path.read_text()
    except FileNotFoundError:
        return ""
    except OSError as exc:
        raise RuntimeError(f"cannot read existing config at {path}: {exc}") from exc


def _detect_editors() -> dict[str, dict[str, object]]:
    detected: dict[str, dict[str, object]] = {}
    for editor, config in EDITOR_CONFIGS.items():
        path = _config_path(config)
        content = ""
        if path.exists():
            try:
                content = path.read_text()
            except OSError:
                content = ""
        detected[editor] = {
            "label": config.label,
            "validation_tier": config.validation_tier,
            "config_path": str(path),
            "editor_dir_exists": path.parent.exists(),
            "config_exists": path.exists(),
            "has_stigmem_mcp": "stigmem-mcp" in content,
        }
    return detected


def _stigmem_mcp_version() -> str | None:
    binary = shutil.which("stigmem-mcp")
    if binary is None:
        return None
    try:
        result = subprocess.run(  # noqa: S603
            [binary, "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )  # nosec B603 - fixed executable resolved from PATH for local diagnostics.
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    output = (result.stdout or result.stderr).strip()
    return output or None


def _mcp_report() -> dict[str, object]:
    binary = shutil.which("stigmem-mcp")
    return {
        "stigmem_mcp_on_path": binary is not None,
        "stigmem_mcp_path": binary,
        "stigmem_mcp_version": _stigmem_mcp_version() if binary else None,
        "stigmem_url_set": "STIGMEM_URL" in os.environ,
        "stigmem_api_key_set": "STIGMEM_API_KEY" in os.environ,
        "detected_editors": _detect_editors(),
    }


def _cmd_mcp_doctor(args: argparse.Namespace) -> int:
    report = _mcp_report()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    print("Stigmem MCP doctor:")
    print(
        "  stigmem-mcp on PATH: "
        f"{'yes' if report['stigmem_mcp_on_path'] else 'no - run: npm install -g stigmem-mcp'}"
    )
    if report["stigmem_mcp_path"]:
        print(f"    path: {report['stigmem_mcp_path']}")
    if report["stigmem_mcp_version"]:
        print(f"    version: {report['stigmem_mcp_version']}")
    print(f"  STIGMEM_URL: {'set' if report['stigmem_url_set'] else 'unset'}")
    print(f"  STIGMEM_API_KEY: {'set' if report['stigmem_api_key_set'] else 'unset'}")
    print("Detected editors:")
    for editor, state in sorted(_detect_editors().items()):
        marker = "configured" if state["has_stigmem_mcp"] else "not configured"
        print(f"  {editor}: {marker} ({state['config_path']})")
    return 0


def _cmd_mcp_detect(args: argparse.Namespace) -> int:
    detected = _detect_editors()
    if args.json:
        print(json.dumps(detected, indent=2, sort_keys=True))
        return 0
    for editor, state in sorted(detected.items()):
        if state["editor_dir_exists"] or state["config_exists"]:
            marker = "configured" if state["has_stigmem_mcp"] else "detected"
            print(f"{editor}: {marker} ({state['config_path']})")
    return 0


def _cmd_mcp_status(args: argparse.Namespace) -> int:
    detected = _detect_editors()
    if args.json:
        print(json.dumps(detected, indent=2, sort_keys=True))
        return 0
    print("MCP integration status:")
    for editor, state in sorted(detected.items()):
        if state["config_exists"]:
            marker = "configured" if state["has_stigmem_mcp"] else "not configured"
            print(f"  {editor}: {marker}")
    return 0


def _cmd_mcp_config(args: argparse.Namespace) -> int:
    if args.list:
        for editor_config in EDITOR_CONFIGS.values():
            print(
                f"{editor_config.editor} "
                f"({editor_config.validation_tier}) - {editor_config.docs_link}"
            )
        return 0
    config = _config_for(args.editor or "")
    if config is None:
        print(f"error: unknown MCP editor: {args.editor}")
        return 1
    print(f"# Paste into: {config.config_path}")
    print(_render_display_snippet(config, args.stigmem_url), end="")
    print("# API keys are not echoed. Set STIGMEM_API_KEY in the target config manually.")
    return 0


def _cmd_mcp_install(args: argparse.Namespace) -> int:
    config = _config_for(args.editor)
    if config is None:
        print(f"error: unknown MCP editor: {args.editor}")
        return 1
    path = _config_path(config)
    try:
        existing = _read_existing(path)
    except RuntimeError as exc:
        print(f"error: {exc}")
        return 1
    if "stigmem-mcp" in existing and not args.force:
        print(f"error: {path} already references stigmem-mcp; pass --force to replace it")
        return 1
    merged = _merge_config(config, existing, args.stigmem_url, args.stigmem_api_key)
    backup_dir = Path(args.backup_dir).expanduser() if args.backup_dir else path.parent
    backup_path = backup_dir / f"{path.name}.stigmem-bak-{_iso_timestamp()}"
    action = "WRITE" if args.write else "DRY-RUN"
    print(f"Editor: {config.editor}")
    print(f"Config path: {path}")
    print(f"Backup path: {backup_path}")
    print(f"Action: {action}")
    print("--- planned stigmem MCP snippet (redacted) ---")
    print(_render_display_snippet(config, args.stigmem_url), end="")
    print("--- end planned snippet ---")
    if not args.write:
        print("Dry-run only. Re-run with --write to apply.")
        return 0
    if os.isatty(0) and not args.yes:
        answer = input("Apply this change? [y/N] ").strip().lower()
        if answer not in {"y", "yes"}:
            print("Aborted.")
            return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    if existing:
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path.write_text(existing)
        print(f"Backed up existing config to {backup_path}")
    path.write_text(merged)
    print(f"Wrote {path}")
    print(f"Verify with: stigmem mcp smoke {config.editor}")
    return 0


def _cmd_mcp_smoke(args: argparse.Namespace) -> int:
    config = _config_for(args.editor)
    if config is None:
        print(f"error: unknown MCP editor: {args.editor}")
        return 1
    path = _config_path(config)
    try:
        content = path.read_text()
    except FileNotFoundError:
        print(f"error: editor config not found at {path}")
        return 1
    except OSError as exc:
        print(f"error: cannot read editor config at {path}: {exc}")
        return 1
    if "stigmem-mcp" not in content:
        print(f"error: editor config at {path} does not reference stigmem-mcp")
        return 1
    if shutil.which("stigmem-mcp") is None:
        print("error: stigmem-mcp is not on PATH; run: npm install -g stigmem-mcp")
        return 1
    smoke_script = (
        Path(__file__).resolve().parents[4] / "adapters" / "mcp" / "tests" / "smoke.sh"
    )
    if smoke_script.exists():
        result = subprocess.run(  # noqa: S603
            [str(smoke_script)],
            check=False,
        )  # nosec B603 - fixed repo-local smoke script.
        if result.returncode != 0:
            print(f"error: MCP protocol smoke failed with exit {result.returncode}")
            return result.returncode
    else:
        print("repo protocol smoke script not bundled; checked config and binary only")
    print(f"MCP smoke passed for {config.editor}")
    return 0


def catalog_asdict() -> list[dict[str, object]]:
    return [asdict(config) for config in EDITOR_CONFIGS.values()]
