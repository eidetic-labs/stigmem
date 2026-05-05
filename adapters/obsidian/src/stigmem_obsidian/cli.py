"""stigmem-obsidian CLI — sync, watch, dry-run commands."""

from __future__ import annotations

import logging
import signal
import sys
import time
from pathlib import Path

import click

from .config import SyncConfig
from .syncer import VaultSyncer
from .vault_reader import VaultWatcher

_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(format=_LOG_FORMAT, level=level)


@click.group()
@click.version_option(package_name="stigmem-obsidian")
def main() -> None:
    """stigmem-obsidian — bidirectional sync between a markdown vault and stigmem."""


# ---------------------------------------------------------------------------
# sync
# ---------------------------------------------------------------------------

@main.command()
@click.argument("vault", default=".", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--config", "-c", "config_path", default=None, type=click.Path(path_type=Path), help="Path to .stigmem-sync.toml")
@click.option("--dry-run", is_flag=True, default=False, help="Preview changes without writing")
@click.option("--verbose", "-v", is_flag=True, default=False)
def sync(vault: Path, config_path: Path | None, dry_run: bool, verbose: bool) -> None:
    """Run a one-shot bidirectional sync against VAULT (default: current directory)."""
    _setup_logging(verbose)
    cfg = _load_config(vault, config_path)
    syncer = VaultSyncer(vault, cfg)

    mode = "[dry-run] " if dry_run else ""
    click.echo(f"{mode}Syncing vault: {vault}")
    result = syncer.sync(dry_run=dry_run)

    click.echo(f"vault → stigmem: {result.vault_to_stigmem} fact(s) asserted")
    click.echo(f"stigmem → vault: {result.stigmem_to_vault} fact(s) written")
    if result.conflicts:
        click.echo(f"conflicts: {result.conflicts}", err=True)
    if result.errors:
        for err in result.errors:
            click.echo(f"ERROR: {err}", err=True)
        sys.exit(1)


# ---------------------------------------------------------------------------
# watch
# ---------------------------------------------------------------------------

@main.command()
@click.argument("vault", default=".", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--config", "-c", "config_path", default=None, type=click.Path(path_type=Path))
@click.option("--interval", default=None, type=float, help="Override poll interval from config (seconds)")
@click.option("--verbose", "-v", is_flag=True, default=False)
def watch(vault: Path, config_path: Path | None, interval: float | None, verbose: bool) -> None:
    """Run a long-lived daemon that syncs on every vault file change."""
    _setup_logging(verbose)
    cfg = _load_config(vault, config_path)
    if interval is not None:
        cfg.watch_interval = interval

    syncer = VaultSyncer(vault, cfg)

    click.echo(f"Starting watch daemon on: {vault}")

    # Initial full sync
    result = syncer.sync(dry_run=False)
    click.echo(
        f"Initial sync complete — vault→stigmem: {result.vault_to_stigmem}, "
        f"stigmem→vault: {result.stigmem_to_vault}"
    )

    def _on_change(path: Path, event_type: str) -> None:
        click.echo(f"[watch] {event_type}: {path.relative_to(vault)}")
        sub = syncer.sync_note(path, dry_run=False)
        if sub.errors:
            for e in sub.errors:
                click.echo(f"  ERROR: {e}", err=True)
        else:
            click.echo(
                f"  vault→stigmem: {sub.vault_to_stigmem}, stigmem→vault: {sub.stigmem_to_vault}"
            )

    stop_requested = False

    def _handle_signal(sig: int, frame: object) -> None:
        nonlocal stop_requested
        stop_requested = True

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    with VaultWatcher(vault, cfg, _on_change):
        while not stop_requested:
            time.sleep(cfg.watch_interval)
            # Periodic full sync to catch stigmem-side changes
            try:
                r = syncer.sync(dry_run=False)
                if r.stigmem_to_vault:
                    click.echo(f"[watch] periodic pull: {r.stigmem_to_vault} fact(s) → vault")
            except Exception as exc:
                click.echo(f"[watch] periodic sync error: {exc}", err=True)

    click.echo("Watch daemon stopped.")


# ---------------------------------------------------------------------------
# dry-run (alias for sync --dry-run)
# ---------------------------------------------------------------------------

@main.command(name="dry-run")
@click.argument("vault", default=".", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--config", "-c", "config_path", default=None, type=click.Path(path_type=Path))
@click.option("--verbose", "-v", is_flag=True, default=False)
def dry_run_cmd(vault: Path, config_path: Path | None, verbose: bool) -> None:
    """Preview what a sync would do without making any changes."""
    _setup_logging(verbose)
    cfg = _load_config(vault, config_path)
    syncer = VaultSyncer(vault, cfg)

    click.echo(f"[dry-run] Vault: {vault}")
    result = syncer.sync(dry_run=True)
    click.echo(f"Would assert: {result.vault_to_stigmem} fact(s) to stigmem")
    click.echo(f"Would write:  {result.stigmem_to_vault} fact(s) to vault")


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _load_config(vault: Path, config_path: Path | None) -> SyncConfig:
    if config_path:
        return SyncConfig.from_toml(config_path)
    try:
        return SyncConfig.find_and_load(vault)
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
