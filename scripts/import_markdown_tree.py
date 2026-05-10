#!/usr/bin/env python3
"""Markdown tree → Stigmem node import script.

Reads a directory containing an index file (default: MEMORY.md) with markdown links
to other markdown files, parses YAML frontmatter on each linked file, and writes
each as a Stigmem fact via the HTTP API.

Useful for importing structured markdown corpora into a stigmem deployment:
- Personal knowledge bases (Obsidian vaults, PARA-style memory, Zettelkasten).
- Team wikis and runbook collections.
- Documentation trees with consistent frontmatter.
- Anywhere you have a markdown index that points at other markdown files.

The script does NOT prescribe a specific markdown organization. Any structure
that has (a) an index file with markdown links and (b) optional YAML frontmatter
on the linked files will work.

Usage (minimum):
    python import_markdown_tree.py \\
        --source-dir <path> \\
        --entity <stigmem-entity-uri> \\
        --scope <local|team|company|public> \\
        --node-url http://localhost:8765

Usage (full):
    python import_markdown_tree.py \\
        --source-dir ~/notes \\
        --entity team:engineering \\
        --scope team \\
        --source agent:my-import-script \\
        --relation-prefix knowledge \\
        --default-type note \\
        --confidence 0.9 \\
        --index-file INDEX.md \\
        --node-url http://localhost:8765 \\
        --api-key $STIGMEM_API_KEY \\
        --dry-run

Frontmatter conventions (per linked file, optional):
    ---
    name: Display name (falls back to link text in index)
    description: Short description (used as fact value preamble)
    type: Category for the fact's relation (falls back to --default-type)
    ---

Fact model produced:
    entity     = <--entity argument>
    relation   = "<--relation-prefix>:<type>:<filename-slug>"
    value      = { type: "text", v: "# <name>\\n\\n<description>\\n\\n<body>" }
    source     = <--source argument>
    confidence = <--confidence argument>
    scope      = <--scope argument>

The filename slug suffix (the third segment of relation) prevents collisions when
multiple files share the same `type`. Without it, multiple "project"-typed
entries would all collide on relation "knowledge:project" and trigger Stigmem's
contradiction protocol on every run.

Output:
    - Prints each fact's identifier as it is written.
    - On success, performs a readback query against the entity and prints results.
    - Exit 0 on success; exit 1 if any write failed.

Re-running is safe under Stigmem's immutable fact model: each run appends new
facts. To identify facts produced by this script, query with
`source=<--source argument>`.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

VALID_SCOPES = {"local", "team", "company", "public"}


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


def load_markdown_tree(
    source_dir: Path, index_file: str, default_type: str
) -> list[dict[str, str]]:
    """Parse the index file and return a list of {name, description, type, body, filename} dicts."""
    index_path = source_dir / index_file
    if not index_path.exists():
        sys.exit(f"Index file not found at {index_path}")

    index_text = index_path.read_text()
    # Markdown link pattern: [text](file.md) — optionally followed by an em-dash description.
    link_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
    entries = []
    for match in link_pattern.finditer(index_text):
        title, filename = match.group(1), match.group(2)
        # Skip external links (http/https).
        if filename.startswith(("http://", "https://", "mailto:")):
            continue
        filepath = source_dir / filename
        if not filepath.exists():
            print(f"  [warn] {filename} not found, skipping", file=sys.stderr)
            continue
        text = filepath.read_text()
        fm, body = parse_frontmatter(text)
        entries.append(
            {
                "name": fm.get("name", title),
                "description": fm.get("description", ""),
                "type": fm.get("type", default_type),
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


def readback(
    node_url: str, entity: str, source: str, scope: str, api_key: str | None
) -> list[dict]:
    """Query the node for facts written by this run."""
    url = (
        f"{node_url.rstrip('/')}/v1/facts"
        f"?entity={entity}&source={source}&scope={scope}&limit=100"
    )
    req = urllib.request.Request(url)
    if api_key:
        req.add_header("Authorization", f"Bearer {api_key}")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())["facts"]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import a markdown tree into a Stigmem node as facts.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  # Personal knowledge base into a single-tenant deployment\n"
            "  import_markdown_tree.py --source-dir ~/notes --entity user:me --scope local\n\n"
            "  # Team runbooks into a team-scoped deployment\n"
            "  import_markdown_tree.py --source-dir ./runbooks --entity team:ops \\\n"
            "      --scope team --relation-prefix runbook --default-type runbook\n\n"
            "  # Dry-run preview before writing\n"
            "  import_markdown_tree.py --source-dir ./docs --entity company:acme \\\n"
            "      --scope company --dry-run\n"
        ),
    )
    parser.add_argument(
        "--source-dir",
        required=True,
        type=Path,
        help="Path to directory containing the index file and linked markdown files",
    )
    parser.add_argument(
        "--entity",
        required=True,
        help="Stigmem entity URI to write facts under (e.g., 'user:me', 'team:ops', 'company:acme')",
    )
    parser.add_argument(
        "--scope",
        required=True,
        choices=sorted(VALID_SCOPES),
        help="Stigmem scope for the imported facts",
    )
    parser.add_argument(
        "--node-url",
        default="http://localhost:8765",
        help="Stigmem node base URL (default: http://localhost:8765)",
    )
    parser.add_argument(
        "--source",
        default="agent:stigmem-import-markdown",
        help="Source identifier for written facts (default: 'agent:stigmem-import-markdown')",
    )
    parser.add_argument(
        "--relation-prefix",
        default="knowledge",
        help="Prefix for fact relations; relations have the form '<prefix>:<type>:<slug>' (default: 'knowledge')",
    )
    parser.add_argument(
        "--default-type",
        default="note",
        help="Default 'type' value when a linked file has no `type` in its frontmatter (default: 'note')",
    )
    parser.add_argument(
        "--confidence",
        type=float,
        default=1.0,
        help="Confidence score for written facts; must be in [0.0, 1.0] (default: 1.0)",
    )
    parser.add_argument(
        "--index-file",
        default="MEMORY.md",
        help="Name of the index file inside --source-dir (default: 'MEMORY.md')",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Bearer token for stigmem API (omit for unauthenticated dev nodes)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print facts without writing them",
    )
    args = parser.parse_args()

    if not (0.0 <= args.confidence <= 1.0):
        sys.exit(f"--confidence must be in [0.0, 1.0]; got {args.confidence}")

    entries = load_markdown_tree(args.source_dir, args.index_file, args.default_type)
    if not entries:
        print("No markdown entries found.")
        sys.exit(0)

    print(f"Found {len(entries)} entries. Target: {args.node_url}")
    print(
        f"  entity={args.entity} scope={args.scope} source={args.source} "
        f"relation_prefix={args.relation_prefix} confidence={args.confidence}"
    )
    written = 0
    errors = 0

    for entry in entries:
        # Filename slug as a sub-key prevents intra-type relation collisions.
        slug = Path(entry["filename"]).stem.lower().replace(" ", "_")
        relation = f"{args.relation_prefix}:{entry['type']}:{slug}"
        fact_value = (
            f"# {entry['name']}\n\n"
            f"{entry['description']}\n\n"
            f"{entry['body']}"
        ).strip()
        fact = {
            "entity": args.entity,
            "relation": relation,
            "value": {"type": "text", "v": fact_value},
            "source": args.source,
            "confidence": args.confidence,
            "scope": args.scope,
        }
        label = f"{entry['filename']} → {args.entity} | {relation}"
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
        facts = readback(
            args.node_url, args.entity, args.source, args.scope, args.api_key
        )
        print(f"  Node returned {len(facts)} fact(s) for {args.entity}:")
        for f in facts:
            snippet = f["value"]["v"][:80].replace("\n", " ")
            print(f"    [{f['id'][:8]}] {f['relation']} — {snippet}…")
    except Exception as exc:
        print(f"  [warn] Readback failed: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
