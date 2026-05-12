"""Integration tests for VaultSyncer — mocked stigmem node via respx.

Tests:
- Round-trip: write fact → assert appears in mock calls; edit note → push to stigmem
- Conflict resolution: stigmem-side wins, vault-side wins, comment policy
- Vault type smoke: Logseq-style journals/ vault, plain-folder vault (config-only diff)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import respx

from stigmem_obsidian.config import SyncConfig
from stigmem_obsidian.syncer import VaultSyncer

BASE = "http://test-stigmem"


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _cfg(vault_root: Path, **kwargs: Any) -> SyncConfig:
    return SyncConfig(node_url=BASE, vault_name="test-vault", **kwargs)


def _fact_resp(
    entity: str,
    relation: str,
    value: str,
    fact_id: str = "fact-001",
    source: str = "stigmem://other-agent",
    scope: str = "local",
) -> dict:
    return {
        "id": fact_id,
        "entity": entity,
        "relation": relation,
        "value": {"type": "string", "v": value},
        "source": source,
        "timestamp": "2026-05-04T00:00:00Z",
        "confidence": 1.0,
        "scope": scope,
        "contradicted": False,
    }


def _page(facts: list[dict], cursor: str | None = None) -> dict:
    return {"facts": facts, "total": len(facts), "cursor": cursor}


def _make_vault(tmp_path: Path, notes: dict[str, str]) -> Path:
    """Create a vault directory with the given filename → content mapping."""
    for rel, content in notes.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# Round-trip: vault → stigmem
# ---------------------------------------------------------------------------


@respx.mock
def test_round_trip_vault_to_stigmem(tmp_path: Path) -> None:
    """Writing a note with frontmatter should assert facts to stigmem."""
    vault = _make_vault(
        tmp_path,
        {"Alice.md": "---\ntitle: Alice Chen\ntags:\n  - engineer\n---\n\nBody.\n"},
    )

    asserted: list[dict] = []

    def capture_post(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        asserted.append(body)
        return httpx.Response(
            201,
            json=_fact_resp(
                entity=body["entity"],
                relation=body["relation"],
                value=str(body["value"].get("v", "")),
            ),
        )

    def empty_query(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_page([]))

    respx.post(f"{BASE}/v1/facts").mock(side_effect=capture_post)
    respx.get(f"{BASE}/v1/facts").mock(side_effect=empty_query)

    syncer = VaultSyncer(vault, _cfg(vault))
    result = syncer.sync(dry_run=False)

    assert result.vault_to_stigmem > 0
    relations = [a["relation"] for a in asserted]
    assert "note:title" in relations
    assert "note:tags" in relations
    # Entity URI derived from filename
    assert all(a["entity"] == "obsidian://vault/Alice" for a in asserted)


@respx.mock
def test_round_trip_stigmem_to_vault(tmp_path: Path) -> None:
    """Facts from stigmem (different source) should appear in the note's Stigmem section."""
    vault = _make_vault(tmp_path, {"Bob.md": "# Bob\n\nBody.\n"})
    entity = "obsidian://vault/Bob"

    stigmem_fact = _fact_resp(entity, "note:role", "Engineer", fact_id="f-001")

    call_count = {"n": 0}

    def multi_query(request: httpx.Request) -> httpx.Response:
        n = call_count["n"]
        call_count["n"] += 1
        # First call: Bob note query during pull → return fact
        # Subsequent calls: return empty
        if n == 0:
            return httpx.Response(200, json=_page([stigmem_fact]))
        return httpx.Response(200, json=_page([]))

    respx.post(f"{BASE}/v1/facts").mock(return_value=httpx.Response(201, json=stigmem_fact))
    respx.get(f"{BASE}/v1/facts").mock(side_effect=multi_query)

    syncer = VaultSyncer(vault, _cfg(vault))
    syncer.sync(dry_run=False)

    content = (vault / "Bob.md").read_text()
    assert "## Stigmem" in content
    assert "note:role" in content
    assert "Engineer" in content


@respx.mock
def test_round_trip_dry_run_does_not_modify_files(tmp_path: Path) -> None:
    vault = _make_vault(tmp_path, {"Carol.md": "# Carol\n\nBody.\n"})
    original = (vault / "Carol.md").read_text()

    stigmem_fact = _fact_resp("obsidian://vault/Carol", "note:role", "Manager")

    call_count = {"n": 0}

    def multi_query(request: httpx.Request) -> httpx.Response:
        n = call_count["n"]
        call_count["n"] += 1
        if n == 0:
            return httpx.Response(200, json=_page([stigmem_fact]))
        return httpx.Response(200, json=_page([]))

    respx.post(f"{BASE}/v1/facts").mock(return_value=httpx.Response(201, json=stigmem_fact))
    respx.get(f"{BASE}/v1/facts").mock(side_effect=multi_query)

    syncer = VaultSyncer(vault, _cfg(vault))
    syncer.sync(dry_run=True)

    assert (vault / "Carol.md").read_text() == original


# ---------------------------------------------------------------------------
# Conflict resolution
# ---------------------------------------------------------------------------


@respx.mock
def test_conflict_comment_policy(tmp_path: Path) -> None:
    """When conflict_policy=comment, conflicting facts surface as %% comments."""
    from stigmem_obsidian.parser import STIGMEM_SECTION_HEADER, build_stigmem_section_body

    existing_facts = [
        {"relation": "note:role", "value": "CEO", "source": "obsidian://vault/Dave.md"}
    ]
    existing_section = f"{STIGMEM_SECTION_HEADER}\n{build_stigmem_section_body(existing_facts)}\n"
    vault = _make_vault(tmp_path, {"Dave.md": f"# Dave\n\n{existing_section}"})

    entity = "obsidian://vault/Dave"
    stigmem_fact = _fact_resp(entity, "note:role", "CTO")

    call_count = {"n": 0}

    def multi_query(request: httpx.Request) -> httpx.Response:
        n = call_count["n"]
        call_count["n"] += 1
        if n == 0:
            return httpx.Response(200, json=_page([stigmem_fact]))
        return httpx.Response(200, json=_page([]))

    respx.post(f"{BASE}/v1/facts").mock(return_value=httpx.Response(201, json=stigmem_fact))
    respx.get(f"{BASE}/v1/facts").mock(side_effect=multi_query)

    cfg = _cfg(tmp_path, conflict_policy="comment")
    syncer = VaultSyncer(vault, cfg)
    syncer.sync(dry_run=False)

    content = (vault / "Dave.md").read_text()
    assert "%%stigmem-conflict:" in content
    assert "note:role" in content


@respx.mock
def test_conflict_stigmem_wins(tmp_path: Path) -> None:
    """When conflict_policy=stigmem_wins, stigmem value overwrites vault section."""
    from stigmem_obsidian.parser import STIGMEM_SECTION_HEADER, build_stigmem_section_body

    existing_facts = [
        {"relation": "note:role", "value": "CEO", "source": "obsidian://vault/Eve.md"}
    ]
    existing_section = f"{STIGMEM_SECTION_HEADER}\n{build_stigmem_section_body(existing_facts)}\n"
    vault = _make_vault(tmp_path, {"Eve.md": f"# Eve\n\n{existing_section}"})

    entity = "obsidian://vault/Eve"
    stigmem_fact = _fact_resp(entity, "note:role", "CTO")

    call_count = {"n": 0}

    def multi_query(request: httpx.Request) -> httpx.Response:
        n = call_count["n"]
        call_count["n"] += 1
        if n == 0:
            return httpx.Response(200, json=_page([stigmem_fact]))
        return httpx.Response(200, json=_page([]))

    respx.post(f"{BASE}/v1/facts").mock(return_value=httpx.Response(201, json=stigmem_fact))
    respx.get(f"{BASE}/v1/facts").mock(side_effect=multi_query)

    cfg = _cfg(tmp_path, conflict_policy="stigmem_wins")
    syncer = VaultSyncer(vault, cfg)
    syncer.sync(dry_run=False)

    content = (vault / "Eve.md").read_text()
    # stigmem value written in; no conflict comment
    assert "CTO" in content
    assert "%%stigmem-conflict:" not in content


@respx.mock
def test_conflict_vault_wins(tmp_path: Path) -> None:
    """When conflict_policy=vault_wins, conflicting stigmem facts are dropped."""
    from stigmem_obsidian.parser import STIGMEM_SECTION_HEADER, build_stigmem_section_body

    existing_facts = [
        {"relation": "note:role", "value": "CEO", "source": "obsidian://vault/Frank.md"}
    ]
    existing_section = f"{STIGMEM_SECTION_HEADER}\n{build_stigmem_section_body(existing_facts)}\n"
    vault = _make_vault(tmp_path, {"Frank.md": f"# Frank\n\n{existing_section}"})

    entity = "obsidian://vault/Frank"
    stigmem_fact = _fact_resp(entity, "note:role", "CTO")

    call_count = {"n": 0}

    def multi_query(request: httpx.Request) -> httpx.Response:
        n = call_count["n"]
        call_count["n"] += 1
        if n == 0:
            return httpx.Response(200, json=_page([stigmem_fact]))
        return httpx.Response(200, json=_page([]))

    respx.post(f"{BASE}/v1/facts").mock(return_value=httpx.Response(201, json=stigmem_fact))
    respx.get(f"{BASE}/v1/facts").mock(side_effect=multi_query)

    cfg = _cfg(tmp_path, conflict_policy="vault_wins")
    syncer = VaultSyncer(vault, cfg)
    syncer.sync(dry_run=False)

    content = (vault / "Frank.md").read_text()
    assert "%%stigmem-conflict:" not in content
    # CTO should NOT appear — vault value (CEO) wins
    assert "CTO" not in content


# ---------------------------------------------------------------------------
# Vault type smoke tests (config-only differences)
# ---------------------------------------------------------------------------


@respx.mock
def test_logseq_journals_vault_smoke(tmp_path: Path) -> None:
    """Logseq-style journals/ vault: daily notes should parse and push without error."""
    vault = _make_vault(
        tmp_path,
        {
            "journals/2026_05_04.md": "- [[Alice]] mentioned the roadmap\n- status:: in-review\n",
            "pages/Alice.md": "---\ntitle: Alice Chen\n---\n\nAlice's page.\n",
        },
    )

    asserted: list[dict] = []

    def capture(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        asserted.append(body)
        return httpx.Response(
            201, json=_fact_resp(entity=body["entity"], relation=body["relation"], value="")
        )

    respx.post(f"{BASE}/v1/facts").mock(side_effect=capture)
    respx.get(f"{BASE}/v1/facts").mock(return_value=httpx.Response(200, json=_page([])))

    syncer = VaultSyncer(vault, _cfg(vault))
    result = syncer.sync(dry_run=False)

    assert result.vault_to_stigmem > 0
    assert result.errors == []
    # Wikilink from journal note
    entities = {a["entity"] for a in asserted}
    assert "obsidian://vault/journals/2026_05_04" in entities


@respx.mock
def test_plain_folder_vault_smoke(tmp_path: Path) -> None:
    """Plain folder with nested markdown files — no Obsidian-specific features needed."""
    vault = _make_vault(
        tmp_path,
        {
            "people/alice.md": "# Alice\nSome notes.\n",
            "projects/roadmap.md": "# Roadmap\nSee [[alice]].\n",
        },
    )

    respx.post(f"{BASE}/v1/facts").mock(
        return_value=httpx.Response(201, json=_fact_resp("x", "note:title", "x"))
    )
    respx.get(f"{BASE}/v1/facts").mock(return_value=httpx.Response(200, json=_page([])))

    syncer = VaultSyncer(vault, _cfg(vault))
    result = syncer.sync(dry_run=False)

    assert result.vault_to_stigmem > 0
    assert result.errors == []


@respx.mock
def test_ignored_paths_not_synced(tmp_path: Path) -> None:
    """Files matching ignored_paths should not be asserted to stigmem."""
    vault = _make_vault(
        tmp_path,
        {
            ".obsidian/workspace.json": "",
            "templates/daily.md": "Template file",
            "notes/real-note.md": "# Real note",
        },
    )

    asserted: list[dict] = []

    def capture(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        asserted.append(body)
        return httpx.Response(
            201, json=_fact_resp(entity=body["entity"], relation=body["relation"], value="")
        )

    respx.post(f"{BASE}/v1/facts").mock(side_effect=capture)
    respx.get(f"{BASE}/v1/facts").mock(return_value=httpx.Response(200, json=_page([])))

    cfg = _cfg(vault, ignored_paths=[".obsidian/**", "templates/**"])
    syncer = VaultSyncer(vault, cfg)
    syncer.sync(dry_run=False)

    entities = {a["entity"] for a in asserted}
    assert "obsidian://vault/notes/real-note" in entities
    # These should not appear
    assert not any("templates" in e for e in entities)


@respx.mock
def test_sync_note_single_file(tmp_path: Path) -> None:
    """sync_note() should push and pull only the given note."""
    vault = _make_vault(tmp_path, {"Grace.md": "# Grace\n\nBody.\n"})
    note_path = vault / "Grace.md"

    respx.post(f"{BASE}/v1/facts").mock(
        return_value=httpx.Response(
            201, json=_fact_resp("obsidian://vault/Grace", "note:title", "Grace")
        )
    )
    respx.get(f"{BASE}/v1/facts").mock(return_value=httpx.Response(200, json=_page([])))

    syncer = VaultSyncer(vault, _cfg(vault))
    result = syncer.sync_note(note_path, dry_run=False)

    assert result.vault_to_stigmem > 0
    assert result.errors == []
