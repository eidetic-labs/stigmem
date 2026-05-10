"""Instruction file migration — spec §21, Phase 10 (ACM-226).

Converts markdown instruction files into atomic stigmem facts and a manifest.
Used by the `stigmem instruction migrate` CLI command.

Public API:
    parse_instruction_chunks(path)   → list[Chunk]
    compute_diff(chunks, ...)        → list[DiffEntry]
    load_existing_facts(diff, ...)   → dict[str, str]
    load_prev_manifest_names(...)    → set[str]
    format_preview(diff, tombstones, ...)  → str
"""

from __future__ import annotations

import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger("stigmem.instruction_migrate")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Chunk:
    filename: str
    heading_text: str
    slug: str
    content: str
    keywords: list[str]
    token_estimate: int


@dataclass
class DiffEntry:
    action: str          # CREATE | UPDATE | NOOP | TOMBSTONE
    unit_name: str
    fact_uri: str
    content: str
    heading_text: str
    keywords: list[str]
    token_estimate: int
    existing_content: str | None = None


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------


_HEADING_RE = re.compile(r"(?m)^(#{1,3}\s+.+)$")
_HEADING_PREFIX_RE = re.compile(r"^#{1,3}\s+")
_FRONTMATTER_RE = re.compile(r"^---\r?\n.*?\r?\n---\r?\n", re.DOTALL)


def _strip_frontmatter(text: str) -> str:
    m = _FRONTMATTER_RE.match(text)
    return text[m.end():].lstrip("\n") if m else text


def _to_slug(text: str, fallback: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or fallback


def _extract_keywords(heading: str, body_prefix: str) -> list[str]:
    words = re.findall(r"\b[a-zA-Z]{4,}\b", heading + " " + body_prefix)
    seen: set[str] = set()
    result: list[str] = []
    for w in words:
        lw = w.lower()
        if lw not in seen:
            seen.add(lw)
            result.append(lw)
        if len(result) == 8:
            break
    return result


def _collect_md_files(path: Path) -> list[Path]:
    """Return ordered list of markdown files under *path* (file or directory)."""
    if path.is_file():
        return [path]
    seen_paths: set[Path] = set()
    md_files: list[Path] = []
    for p in sorted(path.glob("*.md")):
        if p not in seen_paths:
            seen_paths.add(p)
            md_files.append(p)
    for p in sorted(path.glob("**/*.md")):
        if p not in seen_paths:
            seen_paths.add(p)
            md_files.append(p)
    return md_files


def _split_into_section_pairs(text: str, md_file: Path) -> list[tuple[str, str]]:
    """Split markdown text into (heading, body) pairs; fall back to single chunk."""
    sections = _HEADING_RE.split(text)
    file_pairs: list[tuple[str, str]] = []
    i = 0
    while i < len(sections):
        part = sections[i]
        if _HEADING_RE.match(part.strip()):
            heading = part.strip()
            body = sections[i + 1].strip() if i + 1 < len(sections) else ""
            file_pairs.append((heading, body))
            i += 2
        else:
            if part.strip():
                fallback_heading = "# " + md_file.stem.replace("-", " ").title()
                file_pairs.append((fallback_heading, part.strip()))
            i += 1

    if not file_pairs and text.strip():
        file_pairs = [("# " + md_file.stem.replace("-", " ").title(), text.strip())]
    return file_pairs


def _disambiguate_slug(
    base_slug: str, md_file: Path, seen_slugs: dict[str, int]
) -> str:
    """Return a unique slug, prefixing with the file stem and a counter on collision."""
    if base_slug not in seen_slugs:
        return base_slug
    slug = f"{md_file.stem}-{base_slug}"
    # Still might collide; append counter
    if slug in seen_slugs:
        seen_slugs[slug] = seen_slugs.get(slug, 0) + 1
        slug = f"{slug}-{seen_slugs[slug]}"
    return slug


def _build_chunk(
    heading: str, body: str, slug: str, md_file: Path
) -> Chunk:
    """Assemble a Chunk from a parsed (heading, body) pair."""
    heading_text = _HEADING_PREFIX_RE.sub("", heading).strip()
    content = f"{heading}\n\n{body}".strip() if body else heading.strip()
    keywords = _extract_keywords(heading_text, body[:200])
    token_estimate = max(1, len(content) // 4)
    return Chunk(
        filename=md_file.stem,
        heading_text=heading_text,
        slug=slug,
        content=content,
        keywords=keywords,
        token_estimate=token_estimate,
    )


def parse_instruction_chunks(path: Path) -> list[Chunk]:
    """Parse *.md files under *path* into atomic instruction chunks.

    One chunk per H1/H2/H3 heading (or one chunk per file if no headings).
    Strips YAML frontmatter. Deduplicates slugs across files.
    """
    md_files = _collect_md_files(path)

    chunks: list[Chunk] = []
    seen_slugs: dict[str, int] = {}

    for md_file in md_files:
        try:
            text = md_file.read_text(encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            print(f"warning: skipping {md_file}: {exc}", file=sys.stderr)
            continue

        text = _strip_frontmatter(text)
        file_pairs = _split_into_section_pairs(text, md_file)

        for heading, body in file_pairs:
            heading_text = _HEADING_PREFIX_RE.sub("", heading).strip()
            base_slug = _to_slug(heading_text, md_file.stem)
            slug = _disambiguate_slug(base_slug, md_file, seen_slugs)
            seen_slugs[slug] = seen_slugs.get(slug, 0) + 1

            chunks.append(_build_chunk(heading, body, slug, md_file))

    return chunks


# ---------------------------------------------------------------------------
# Fact URI building
# ---------------------------------------------------------------------------


def build_fact_uri(scope_prefix: str, slug: str, version: str) -> str:
    return f"{scope_prefix}/{slug}/{version}"


def scope_prefix_for_role(deployment: str, agent_id: str) -> str:
    return f"instruction:{deployment}/agent/{agent_id}"


def scope_prefix_for_skill(deployment: str, skill_name: str) -> str:
    return f"instruction:{deployment}/skill/{skill_name}"


# ---------------------------------------------------------------------------
# Diff computation
# ---------------------------------------------------------------------------


def compute_diff(
    chunks: list[Chunk],
    scope_prefix: str,
    version: str,
    existing_content: dict[str, str],
    prev_manifest_names: set[str],
) -> list[DiffEntry]:
    """Build a diff: CREATE / UPDATE / NOOP for each chunk, plus TOMBSTONE entries."""
    diff: list[DiffEntry] = []
    new_names: set[str] = set()

    for chunk in chunks:
        fact_uri = build_fact_uri(scope_prefix, chunk.slug, version)
        unit_name = chunk.slug
        new_names.add(unit_name)
        existing = existing_content.get(fact_uri)

        if existing is None:
            action = "CREATE"
        elif existing.strip() == chunk.content.strip():
            action = "NOOP"
        else:
            action = "UPDATE"

        diff.append(DiffEntry(
            action=action,
            unit_name=unit_name,
            fact_uri=fact_uri,
            content=chunk.content,
            heading_text=chunk.heading_text,
            keywords=chunk.keywords,
            token_estimate=chunk.token_estimate,
            existing_content=existing,
        ))

    # Tombstone: manifest names present before but not in new set
    for name in sorted(prev_manifest_names - new_names):
        diff.append(DiffEntry(
            action="TOMBSTONE",
            unit_name=name,
            fact_uri="",
            content="",
            heading_text=name,
            keywords=[],
            token_estimate=0,
        ))

    return diff


# ---------------------------------------------------------------------------
# Existing state loaders
# ---------------------------------------------------------------------------


def load_existing_facts_from_db(
    diff: list[DiffEntry],
    db_path: str,
) -> dict[str, str]:
    """Query local SQLite for existing fact content keyed by fact_uri."""
    import sqlite3

    result: dict[str, str] = {}
    uris = [d.fact_uri for d in diff if d.fact_uri]
    if not uris:
        return result
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        for uri in uris:
            row = conn.execute(
                "SELECT value_v FROM facts WHERE entity = ? ORDER BY timestamp DESC LIMIT 1",
                (uri,),
            ).fetchone()
            if row:
                result[uri] = str(row["value_v"])
        conn.close()
    except Exception as exc:
        print(f"warning: db query failed ({db_path}): {exc}", file=sys.stderr)
    return result


def load_existing_facts_from_api(
    diff: list[DiffEntry],
    node_url: str,
    api_key: str,
) -> dict[str, str]:
    """Query the stigmem facts API for existing fact content keyed by fact_uri."""
    try:
        import httpx
    except ImportError:
        print("warning: httpx not installed — skipping existing-fact check", file=sys.stderr)
        return {}

    result: dict[str, str] = {}
    headers = {"Authorization": f"Bearer {api_key}"}
    url = node_url.rstrip("/") + "/v1/facts"
    for d in diff:
        if not d.fact_uri:
            continue
        try:
            r = httpx.get(
                url,
                params={"entity": d.fact_uri, "limit": 1},
                headers=headers,
                timeout=10.0,
            )
            if r.status_code == 200:
                facts = r.json().get("facts", [])
                if facts:
                    result[d.fact_uri] = str(facts[0]["value"]["v"])
        except Exception as exc:  # noqa: BLE001  # nosec B110 — best-effort pre-flight; node may not be reachable
            logger.debug("load_existing_facts_from_api failed for %s: %s", d.fact_uri, exc)
    return result


def load_prev_manifest_names_from_db(agent_id: str, db_path: str) -> set[str]:
    """Return unit names from the current manifest in local SQLite."""
    import json
    import sqlite3

    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT body FROM instruction_manifests WHERE agent_id = ? AND superseded_at IS NULL"
            " ORDER BY created_at DESC LIMIT 1",
            (agent_id,),
        ).fetchone()
        conn.close()
        if row:
            entries = json.loads(row["body"])
            return {e["name"] for e in entries}
    except Exception as exc:  # noqa: BLE001  # nosec B110 — best-effort read; DB may be absent or schema may differ
        logger.debug("load_prev_manifest_names_from_db failed for %s: %s", agent_id, exc)
    return set()


def load_prev_manifest_names_from_api(agent_id: str, node_url: str, api_key: str) -> set[str]:
    """Return unit names from the current manifest via API."""
    try:
        import httpx
    except ImportError:
        return set()

    try:
        r = httpx.get(
            f"{node_url.rstrip('/')}/v1/agents/{agent_id}/instruction-manifest",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10.0,
        )
        if r.status_code == 200:
            return {e["name"] for e in r.json().get("entries", [])}
    except Exception as exc:  # noqa: BLE001  # nosec B110 — best-effort pre-flight; node may not be reachable
        logger.debug("load_prev_manifest_names_from_api failed for %s: %s", agent_id, exc)
    return set()


# ---------------------------------------------------------------------------
# Preview / formatting
# ---------------------------------------------------------------------------


def format_preview(
    diff: list[DiffEntry],
    scope_label: str,
    path: Path,
    version: str,
) -> str:
    """Return a human-readable migration preview string."""
    lines: list[str] = []
    lines.append("=== Migration Preview ===")
    lines.append(f"Path:    {path}")
    lines.append(f"Scope:   {scope_label}")
    lines.append(f"Version: {version}")
    lines.append("")

    creates = [d for d in diff if d.action == "CREATE"]
    updates = [d for d in diff if d.action == "UPDATE"]
    noops = [d for d in diff if d.action == "NOOP"]
    tombstones = [d for d in diff if d.action == "TOMBSTONE"]

    lines.append(
        f"Facts: {len(creates)} create, {len(updates)} update, "
        f"{len(noops)} noop, {len(tombstones)} tombstone"
    )
    lines.append("")

    for d in diff:
        if d.action == "TOMBSTONE":
            continue
        symbol = {"CREATE": "+", "UPDATE": "~", "NOOP": "="}[d.action]
        lines.append(f"  [{symbol}] {d.unit_name}")
        lines.append(f"       URI:    {d.fact_uri}")
        lines.append(f"       tokens: ~{d.token_estimate}")
        if d.action == "UPDATE" and d.existing_content is not None:
            old_lines = d.existing_content.count("\n")
            new_lines = d.content.count("\n")
            lines.append(f"       lines:  {old_lines} → {new_lines}")
        lines.append("")

    for d in tombstones:
        lines.append(f"  [T] {d.unit_name} (removed — existing facts kept for history)")
    if tombstones:
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# HTTP writers
# ---------------------------------------------------------------------------


def write_facts(
    diff: list[DiffEntry],
    node_url: str,
    api_key: str,
) -> tuple[int, int]:
    """Write CREATE/UPDATE facts via HTTP. Returns (written, failed)."""
    try:
        import httpx
    except ImportError:
        print("error: httpx not installed", file=sys.stderr)
        return 0, len([d for d in diff if d.action in ("CREATE", "UPDATE")])

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    url = node_url.rstrip("/") + "/v1/facts"
    written = 0
    failed = 0
    for d in diff:
        if d.action not in ("CREATE", "UPDATE"):
            continue
        payload: dict[str, Any] = {
            "entity": d.fact_uri,
            "relation": "instruction:content",
            "value": {"type": "text", "v": d.content},
            "source": "instruction-migration",
            "scope": "local",
        }
        try:
            r = httpx.post(url, json=payload, headers=headers, timeout=15.0)
            if r.status_code == 201:
                written += 1
                print(f"  [{d.action}] {d.unit_name} ✓")
            else:
                print(
                    f"  [{d.action}] {d.unit_name} FAILED: "
                    f"{r.status_code} {r.text[:120]}",
                    file=sys.stderr,
                )
                failed += 1
        except Exception as exc:
            print(f"  [{d.action}] {d.unit_name} FAILED: {exc}", file=sys.stderr)
            failed += 1
    return written, failed


def publish_manifest(
    agent_id: str,
    diff: list[DiffEntry],
    manifest_version: str,
    node_url: str,
    api_key: str,
) -> bool:
    """Publish a new manifest via HTTP. Returns True on success."""
    try:
        import httpx
    except ImportError:
        print("error: httpx not installed", file=sys.stderr)
        return False

    entries = []
    for d in diff:
        if d.action == "TOMBSTONE":
            continue
        entries.append({
            "name": d.unit_name,
            "description": d.heading_text[:120],
            "fact_uri": d.fact_uri,
            "load_triggers": {
                "intents": [d.heading_text.lower()],
                "keywords": d.keywords,
                "task_types": [],
            },
            "token_estimate": d.token_estimate,
        })

    payload = {
        "version": manifest_version,
        "entries": entries,
        "skip_coverage_gate": False,
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    url = node_url.rstrip("/") + f"/v1/agents/{agent_id}/instruction-manifest"
    try:
        r = httpx.put(url, json=payload, headers=headers, timeout=30.0)
        if r.status_code == 200:
            return True
        print(f"Manifest publish FAILED: {r.status_code} {r.text[:200]}", file=sys.stderr)
        return False
    except Exception as exc:
        print(f"Manifest publish FAILED: {exc}", file=sys.stderr)
        return False
