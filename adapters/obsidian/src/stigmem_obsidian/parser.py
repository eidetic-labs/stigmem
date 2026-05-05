"""Markdown note parser — frontmatter, wikilinks, and Dataview inline fields."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Data shapes
# ---------------------------------------------------------------------------

@dataclass
class ParsedNote:
    """Structured representation of a parsed markdown note."""

    rel_path: str
    title: str
    frontmatter: dict[str, Any]
    wikilinks: list[str]
    dataview_fields: dict[str, str]
    body: str
    content_hash: str

    @property
    def entity_uri(self) -> str:
        """Stable entity URI derived from vault-relative path (no extension)."""
        stem = self.rel_path.removesuffix(".md")
        return f"obsidian://vault/{stem}"


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# [[wikilink]] or [[wikilink|alias]]
_WIKILINK_RE = re.compile(r"\[\[([^\]|#]+?)(?:[|#][^\]]*?)?\]\]")

# Dataview inline field: key:: value (anywhere on line, not in code blocks)
_DATAVIEW_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_ -]*)::[ \t]*(.+)$", re.MULTILINE)

# The managed Stigmem section header
STIGMEM_SECTION_HEADER = "## Stigmem"
STIGMEM_SECTION_RE = re.compile(
    r"(^## Stigmem\n)(.*?)(?=^## |\Z)",
    re.MULTILINE | re.DOTALL,
)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def parse_note(path: Path, vault_root: Path) -> ParsedNote:
    """Parse a single markdown note file into a ParsedNote.

    Handles YAML frontmatter (via python-frontmatter), wikilinks, and
    Dataview inline fields. Skips code-block content for Dataview extraction.
    """
    import frontmatter as fm
    import hashlib

    raw_text = path.read_text(encoding="utf-8", errors="replace")
    post = fm.loads(raw_text)

    meta: dict[str, Any] = dict(post.metadata)
    body: str = post.content

    title = str(meta.get("title", "") or path.stem)

    wikilinks = _extract_wikilinks(body)

    body_no_code = _strip_code_blocks(body)
    dataview_fields = _extract_dataview(body_no_code)

    content_hash = hashlib.sha256(raw_text.encode()).hexdigest()[:16]

    rel_path = str(path.relative_to(vault_root)).replace("\\", "/")

    return ParsedNote(
        rel_path=rel_path,
        title=title,
        frontmatter=meta,
        wikilinks=wikilinks,
        dataview_fields=dataview_fields,
        body=body,
        content_hash=content_hash,
    )


def _extract_wikilinks(text: str) -> list[str]:
    """Return deduplicated list of wikilink targets from text."""
    seen: set[str] = set()
    result: list[str] = []
    for m in _WIKILINK_RE.finditer(text):
        target = m.group(1).strip()
        if target and target not in seen:
            seen.add(target)
            result.append(target)
    return result


def _extract_dataview(text: str) -> dict[str, str]:
    """Extract Dataview inline fields (key:: value) from text."""
    return {m.group(1).strip(): m.group(2).strip() for m in _DATAVIEW_RE.finditer(text)}


def _strip_code_blocks(text: str) -> str:
    """Remove fenced code blocks so Dataview regex doesn't match inside them."""
    return re.sub(r"```.*?```", "", text, flags=re.DOTALL)


# ---------------------------------------------------------------------------
# Stigmem-section helpers
# ---------------------------------------------------------------------------

def extract_stigmem_section(content: str) -> str | None:
    """Return the body of the `## Stigmem` section, or None if absent."""
    m = STIGMEM_SECTION_RE.search(content)
    if m:
        return m.group(2).strip()
    return None


def replace_stigmem_section(content: str, new_body: str) -> str:
    """Replace the `## Stigmem` section body, or append the section if absent."""
    section_text = f"{STIGMEM_SECTION_HEADER}\n{new_body}\n"
    if STIGMEM_SECTION_RE.search(content):
        return STIGMEM_SECTION_RE.sub(
            lambda m: section_text,
            content,
            count=1,
        )
    sep = "\n" if content.endswith("\n") else "\n\n"
    return content + sep + section_text


def build_stigmem_section_body(facts: list[dict[str, Any]]) -> str:
    """Render a list of fact dicts as a YAML-ish block for the Stigmem section."""
    lines: list[str] = []
    for fact in facts:
        relation = fact.get("relation", "")
        value = fact.get("value", "")
        source = fact.get("source", "")
        lines.append(f"- relation: {relation}")
        lines.append(f"  value: {value}")
        if source:
            lines.append(f"  source: {source}")
    return "\n".join(lines)


def parse_stigmem_section_body(body: str) -> list[dict[str, str]]:
    """Parse the YAML-ish Stigmem section body back into a list of fact dicts."""
    facts: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("- relation:"):
            if current:
                facts.append(current)
            current = {"relation": stripped[len("- relation:"):].strip()}
        elif stripped.startswith("value:") and current:
            current["value"] = stripped[len("value:"):].strip()
        elif stripped.startswith("source:") and current:
            current["source"] = stripped[len("source:"):].strip()
    if current:
        facts.append(current)
    return facts


def add_conflict_comment(content: str, conflict_note: str) -> str:
    """Append an Obsidian markdown comment surfacing a conflict."""
    comment = f"\n%%stigmem-conflict: {conflict_note}%%\n"
    return content + comment
