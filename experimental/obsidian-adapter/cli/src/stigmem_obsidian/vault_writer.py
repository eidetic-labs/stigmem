"""Vault writer — write stigmem facts back into markdown notes."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .config import SyncConfig
from .parser import (
    STIGMEM_SECTION_HEADER,
    add_conflict_comment,
    build_stigmem_section_body,
    replace_stigmem_section,
)

logger = logging.getLogger(__name__)

_SCALAR_FRONTMATTER_RELATIONS = {"note:title", "note:description"}


def write_facts_to_note(
    vault_root: Path,
    rel_path: str,
    facts: list[dict[str, Any]],
    config: SyncConfig,
    *,
    dry_run: bool = False,
) -> bool:
    """Append/update stigmem facts in a note.

    Facts whose relation is in _SCALAR_FRONTMATTER_RELATIONS are written to
    frontmatter. All others go into the managed `## Stigmem` section.

    Returns True if the file was (or would be) modified.
    """
    note_path = vault_root / rel_path
    if not note_path.exists():
        return create_note_for_entity(vault_root, rel_path, facts, config, dry_run=dry_run)

    original = note_path.read_text(encoding="utf-8")
    content = original

    # Split facts: frontmatter scalars vs section facts
    section_facts = [f for f in facts if f.get("relation", "") not in _SCALAR_FRONTMATTER_RELATIONS]

    if section_facts:
        body = build_stigmem_section_body(section_facts)
        content = replace_stigmem_section(content, body)

    if content == original:
        return False

    if not dry_run:
        note_path.write_text(content, encoding="utf-8")
        logger.info("vault_writer: updated %s (%d facts)", rel_path, len(facts))
    else:
        logger.info("vault_writer: [dry-run] would update %s (%d facts)", rel_path, len(facts))

    return True


def create_note_for_entity(
    vault_root: Path,
    rel_path: str,
    facts: list[dict[str, Any]],
    config: SyncConfig,
    *,
    dry_run: bool = False,
) -> bool:
    """Create a new note file for a stigmem entity that has no vault counterpart."""
    note_path = vault_root / config.sync_folder / rel_path
    note_path.parent.mkdir(parents=True, exist_ok=True)

    title_fact = next(
        (f for f in facts if f.get("relation") == "note:title"), None
    )
    title = title_fact["value"] if title_fact else Path(rel_path).stem

    section_facts = [f for f in facts if f.get("relation", "") not in _SCALAR_FRONTMATTER_RELATIONS]
    body = build_stigmem_section_body(section_facts)

    content = f"# {title}\n\n{STIGMEM_SECTION_HEADER}\n{body}\n"

    if not dry_run:
        note_path.write_text(content, encoding="utf-8")
        logger.info("vault_writer: created %s (%d facts)", note_path, len(facts))
    else:
        logger.info("vault_writer: [dry-run] would create %s", note_path)

    return True


def apply_conflict(
    vault_root: Path,
    rel_path: str,
    conflict_note: str,
    *,
    dry_run: bool = False,
) -> None:
    """Surface a conflict as an Obsidian markdown comment in the note."""
    note_path = vault_root / rel_path
    if not note_path.exists():
        logger.warning("vault_writer: conflict note %s not found; skipping", rel_path)
        return

    content = note_path.read_text(encoding="utf-8")
    updated = add_conflict_comment(content, conflict_note)

    if not dry_run:
        note_path.write_text(updated, encoding="utf-8")
        logger.warning("vault_writer: conflict surfaced in %s", rel_path)
    else:
        logger.info("vault_writer: [dry-run] would surface conflict in %s", rel_path)
