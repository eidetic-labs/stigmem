#!/usr/bin/env python3
"""CEO MEMORY.md → Stigmem node migration script.

Reads the CEO's PARA-style memory files (MEMORY.md index + linked .md files),
converts each entry to a Stigmem fact, and POSTs to the running node via HTTP.

Usage:
    python migrate_ceo_memory.py \\
        --memory-dir ~/.claude/projects/<proj>/memory \\
        --node-url http://localhost:8765 \\
        [--api-key <key>] \\
        [--dry-run]

Output:
    - Prints each fact as it is written.
    - On success, POSTs a final readback query and prints matching facts.
    - Exit 0 on success, 1 on any write failure.

Fact model used:
    entity    = "user:ceo"
    relation  = "memory:{type}"  (type from frontmatter)
    value     = { type: "text", v: <full file body> }
    source    = "agent:stigmem-migrator"
    scope     = "company"
    confidence= 1.0
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import urllib.request
import urllib.error

ENTITY = "user:ceo"
SOURCE = "agent:stigmem-migrator"
SCOPE = "company"


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Return (frontmatter_dict, body). Handles --- delimited YAML frontmatter."""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, text
    fm_block = text[3:end].strip()
    body = text[end + 4:].strip()
    fm: dict[str, str] = {}
    for line in fm_block.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    return fm, body


def load_memory_files(memory_dir: Path) -> list[dict[str, str]]:
    """Parse MEMORY.md index and return list of {name, description, type, body} dicts."""
    index_path = memory_dir / "MEMORY.md"
    if not index_path.exists():
        sys.exit(f"MEMORY.md not found at {index_path}")

    index_text = index_path.read_text()
    # Links look like: - [Title](file.md) — description
    link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
    entries = []
    for match in link_pattern.finditer(index_text):
        title, filename = match.group(1), match.group(2)
        filepath = memory_dir / filename
        if not filepath.exists():
            print(f"  [warn] {filename} not found, skipping", file=sys.stderr)
            continue
        text = filepath.read_text()
        fm, body = parse_frontmatter(text)
        entries.append(
            {
                "name": fm.get("name", title),
                "description": fm.get("description", ""),
                "type": fm.get("type", "project"),
                "body": body,
                "filename": filename,
            }
        )
    return entries


def post_fact(node_url: str, fact: dict, api_key: str | None) -> dict:
    data = json.dumps(fact).encode()
    req = urllib.request.Request(
        f"{node_url.rstrip('/')}/v1/facts",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    if api_key:
        req.add_header("Authorization", f"Bearer {api_key}")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def readback(node_url: str, api_key: str | None) -> list[dict]:
    url = f"{node_url.rstrip('/')}/v1/facts?entity={ENTITY}&source={SOURCE}&scope={SCOPE}&limit=100"
    req = urllib.request.Request(url)
    if api_key:
        req.add_header("Authorization", f"Bearer {api_key}")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())["facts"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Migrate CEO memory to Stigmem node")
    parser.add_argument(
        "--memory-dir",
        required=True,
        type=Path,
        help="Path to directory containing MEMORY.md",
    )
    parser.add_argument(
        "--node-url",
        default="http://localhost:8765",
        help="Stigmem node base URL (default: http://localhost:8765)",
    )
    parser.add_argument("--api-key", default=None, help="Bearer token if auth is required")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print facts without writing them",
    )
    args = parser.parse_args()

    entries = load_memory_files(args.memory_dir)
    if not entries:
        print("No memory entries found.")
        sys.exit(0)

    print(f"Found {len(entries)} memory entries. Target: {args.node_url}")
    written = 0
    errors = 0

    for entry in entries:
        relation = f"memory:{entry['type']}"
        fact = {
            "entity": ENTITY,
            "relation": relation,
            "value": {
                "type": "text",
                "v": f"# {entry['name']}\n\n{entry['description']}\n\n{entry['body']}".strip(),
            },
            "source": SOURCE,
            "confidence": 1.0,
            "scope": SCOPE,
        }
        label = f"{entry['filename']} → {ENTITY} | {relation}"
        if args.dry_run:
            print(f"  [dry-run] {label}")
            continue
        try:
            result = post_fact(args.node_url, fact, args.api_key)
            print(f"  [ok] {label} → id={result['id']}")
            written += 1
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            print(f"  [err] {label}: HTTP {e.code} — {body}", file=sys.stderr)
            errors += 1
        except Exception as exc:
            print(f"  [err] {label}: {exc}", file=sys.stderr)
            errors += 1

    if args.dry_run:
        print(f"\nDry run complete. Would have written {len(entries)} facts.")
        return

    print(f"\nWrote {written} facts. Errors: {errors}.")
    if errors:
        sys.exit(1)

    # Readback verification
    print("\nReadback verification:")
    try:
        facts = readback(args.node_url, args.api_key)
        print(f"  Node returned {len(facts)} fact(s) for {ENTITY}:")
        for f in facts:
            snippet = f["value"]["v"][:80].replace("\n", " ")
            print(f"    [{f['id'][:8]}] {f['relation']} — {snippet}…")
    except Exception as exc:
        print(f"  [warn] Readback failed: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
