"""Core bidirectional sync logic — vault ↔ stigmem."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from stigmem import StigmemClient, ref_value, string_value, text_value
from stigmem.exceptions import StigmemError

from .config import SyncConfig
from .parser import ParsedNote, parse_note, parse_stigmem_section_body
from .vault_reader import scan_vault
from .vault_writer import apply_conflict, write_facts_to_note

logger = logging.getLogger(__name__)

# Source URIs
_SOURCE_VAULT_PREFIX = "obsidian://vault"
_SOURCE_STIGMEM_PREFIX = "stigmem://"


@dataclass
class SyncResult:
    """Summary of a single sync run."""

    vault_to_stigmem: int = 0
    stigmem_to_vault: int = 0
    conflicts: int = 0
    errors: list[str] = field(default_factory=list)
    dry_run: bool = False


class VaultSyncer:
    """Orchestrates bidirectional sync between a vault directory and a stigmem node.

    Usage::

        config = SyncConfig.find_and_load(vault_path)
        syncer = VaultSyncer(vault_path, config)
        result = syncer.sync(dry_run=False)
    """

    def __init__(self, vault_root: Path, config: SyncConfig) -> None:
        self._vault_root = vault_root
        self._config = config
        self._client = StigmemClient(
            url=config.node_url,
            api_key=config.api_key,
        )

    # ------------------------------------------------------------------
    # Public entry points
    # ------------------------------------------------------------------

    def sync(self, *, dry_run: bool = False) -> SyncResult:
        """Run a full bidirectional sync pass.

        1. Scan vault → assert facts into stigmem (vault → stigmem).
        2. Query stigmem for facts about known entities → write back (stigmem → vault).
        3. Surface conflicts per the configured conflict_policy.
        """
        result = SyncResult(dry_run=dry_run)
        notes = scan_vault(self._vault_root, self._config)

        # Pass 1: vault → stigmem
        for note in notes:
            try:
                pushed = self._push_note(note, dry_run=dry_run)
                result.vault_to_stigmem += pushed
            except StigmemError as exc:
                msg = f"vault→stigmem failed for {note.rel_path}: {exc}"
                logger.warning(msg)
                result.errors.append(msg)

        # Pass 2: stigmem → vault
        for note in notes:
            try:
                pulled = self._pull_entity(note, dry_run=dry_run)
                result.stigmem_to_vault += pulled
            except StigmemError as exc:
                msg = f"stigmem→vault failed for {note.rel_path}: {exc}"
                logger.warning(msg)
                result.errors.append(msg)

        return result

    def sync_note(self, note_path: Path, *, dry_run: bool = False) -> SyncResult:
        """Sync a single note file (used by the file-watch daemon)."""
        result = SyncResult(dry_run=dry_run)
        if not note_path.exists():
            logger.info("sync_note: %s was deleted; skipping", note_path)
            return result
        try:
            note = parse_note(note_path, self._vault_root)
        except Exception as exc:
            result.errors.append(f"parse failed for {note_path}: {exc}")
            return result

        try:
            result.vault_to_stigmem += self._push_note(note, dry_run=dry_run)
        except StigmemError as exc:
            result.errors.append(f"vault→stigmem push failed: {exc}")

        try:
            result.stigmem_to_vault += self._pull_entity(note, dry_run=dry_run)
        except StigmemError as exc:
            result.errors.append(f"stigmem→vault pull failed: {exc}")

        return result

    # ------------------------------------------------------------------
    # Internal: vault → stigmem
    # ------------------------------------------------------------------

    def _push_note(self, note: ParsedNote, *, dry_run: bool) -> int:
        """Assert facts derived from *note* into stigmem. Returns number asserted."""
        entity = note.entity_uri
        scope = self._config.scope_for_path(note.rel_path)
        source = f"{_SOURCE_VAULT_PREFIX}/{note.rel_path}"
        count = 0

        def _safe_assert(relation: str, value: Any) -> None:
            nonlocal count
            if dry_run:
                logger.info("[dry-run] assert %s %s = %r", entity, relation, value)
                count += 1
                return
            try:
                self._client.assert_fact(
                    entity=entity,
                    relation=relation,
                    value=value,
                    source=source,
                    scope=scope,
                )
                count += 1
            except StigmemError as exc:
                logger.warning("assert failed %s/%s: %s", entity, relation, exc)

        # Title
        _safe_assert("note:title", string_value(note.title))

        # Frontmatter — skip internal Obsidian/stigmem keys
        _SKIP_FM_KEYS = {"position", "cssclass", "publish"}
        for key, val in note.frontmatter.items():
            if key in _SKIP_FM_KEYS:
                continue
            relation = f"note:{key}"
            if isinstance(val, list):
                for item in val:
                    _safe_assert(relation, string_value(str(item)))
            elif isinstance(val, bool):
                from stigmem import boolean_value
                _safe_assert(relation, boolean_value(val))
            elif isinstance(val, (int, float)):
                from stigmem import number_value
                _safe_assert(relation, number_value(float(val)))
            else:
                _safe_assert(relation, string_value(str(val)))

        # Wikilinks → relations
        wikilink_relation = self._config.wikilink_relation
        for target in note.wikilinks:
            target_uri = f"obsidian://vault/{target}"
            # Check if any tag-level override applies
            rel = wikilink_relation
            _safe_assert(rel, ref_value(target_uri))

        # Dataview inline fields
        for key, val in note.dataview_fields.items():
            _safe_assert(f"dataview:{key}", string_value(val))

        # Content hash for rename tracking
        _safe_assert("note:content_hash", string_value(note.content_hash))

        return count

    # ------------------------------------------------------------------
    # Internal: stigmem → vault
    # ------------------------------------------------------------------

    def _fetch_remote_facts(
        self, entity: str, scope: str, vault_source: str,
    ) -> list[dict[str, Any]]:
        """Page through stigmem and collect facts that didn't originate from this note."""
        result: list[dict[str, Any]] = []
        cursor: str | None = None
        while True:
            page = self._client.query(entity=entity, scope=scope, cursor=cursor, limit=100)
            for fact in page.facts:
                if fact.source != vault_source and not fact.contradicted:
                    result.append({
                        "relation": fact.relation,
                        "value": _fact_value_str(fact.value),
                        "source": fact.source,
                        "id": fact.id,
                    })
            if page.cursor is None:
                return result
            cursor = page.cursor

    def _apply_conflict_policy(
        self,
        conflicts: list[dict[str, Any]],
        stigmem_facts: list[dict[str, Any]],
        rel_path: str,
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """Filter stigmem_facts and collect conflict comments per the configured policy.

        Returns (filtered_facts, conflict_messages_to_append).
        """
        policy = self._config.conflict_policy
        comments: list[str] = []
        for conflict in conflicts:
            msg = (
                f"relation={conflict['relation']} "
                f"vault={conflict['vault_value']} "
                f"stigmem={conflict['stigmem_value']}"
            )
            logger.info("conflict (%s): %s in %s", policy, msg, rel_path)
            if policy == "stigmem_wins":
                continue  # keep the stigmem-side fact in the write set
            # vault_wins or comment: drop the stigmem fact for this relation
            stigmem_facts = [
                f for f in stigmem_facts if f["relation"] != conflict["relation"]
            ]
            if policy == "comment":
                comments.append(msg)
        return stigmem_facts, comments

    def _pull_entity(self, note: ParsedNote, *, dry_run: bool) -> int:
        """Fetch facts for note's entity from stigmem; write new ones to vault.

        Returns number of facts written back.
        """
        scope = self._config.scope_for_path(note.rel_path)
        vault_source = f"{_SOURCE_VAULT_PREFIX}/{note.rel_path}"

        stigmem_facts = self._fetch_remote_facts(note.entity_uri, scope, vault_source)
        if not stigmem_facts:
            return 0

        # Read existing Stigmem section to detect conflicts
        note_path = self._vault_root / note.rel_path
        existing_content = note_path.read_text(encoding="utf-8") if note_path.exists() else ""
        from .parser import extract_stigmem_section
        existing_section = extract_stigmem_section(existing_content)
        existing_facts = parse_stigmem_section_body(existing_section) if existing_section else []

        conflicts = _detect_conflicts(existing_facts, stigmem_facts)
        stigmem_facts, conflict_messages = self._apply_conflict_policy(
            conflicts, stigmem_facts, note.rel_path,
        )

        modified = write_facts_to_note(
            self._vault_root, note.rel_path, stigmem_facts, self._config, dry_run=dry_run
        )

        # Append conflict comments AFTER writing so they aren't erased by section replace
        for msg in conflict_messages:
            apply_conflict(self._vault_root, note.rel_path, msg, dry_run=dry_run)
        return len(stigmem_facts) if modified else 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fact_value_str(value: Any) -> str:
    """Extract a string representation from a FactValue model."""
    v = getattr(value, "v", None)
    if v is None:
        return ""
    return str(v)


def _detect_conflicts(
    existing: list[dict[str, str]],
    incoming: list[dict[str, Any]],
) -> list[dict[str, str]]:
    """Return relations that appear in both sides with different values."""
    existing_map = {f["relation"]: f.get("value", "") for f in existing}
    conflicts: list[dict[str, str]] = []
    for fact in incoming:
        rel = fact["relation"]
        new_val = str(fact.get("value", ""))
        if rel in existing_map and existing_map[rel] != new_val:
            conflicts.append({
                "relation": rel,
                "vault_value": existing_map[rel],
                "stigmem_value": new_val,
            })
    return conflicts
