#!/usr/bin/env python3
"""Generate CLI reference markdown from `stigmem --help` output.

Usage:
    python docs/scripts/gen-cli-docs.py          # writes to docs/docs/reference/cli/
    make gen-cli-docs                             # same, via Makefile target

Requires the stigmem package to be installed (e.g. `uv pip install -e node/`).
"""

from __future__ import annotations

import argparse
import importlib
import sys
import textwrap
from io import StringIO
from pathlib import Path

DOCS_CLI_DIR = Path(__file__).resolve().parent.parent / "docs" / "reference" / "cli"

FRONTMATTER_STIGMEM = """\
---
title: "stigmem"
sidebar_label: "stigmem"
sidebar_position: 1
description: "CLI reference for the stigmem command — capability tokens, federation, snapshots, decay, instructions, audit, identity, and CID backfill."
audience: Operator
---

"""

FRONTMATTER_NODE = """\
---
title: "stigmem-node"
sidebar_label: "stigmem-node"
sidebar_position: 2
description: "CLI reference for the stigmem-node command — starts the Stigmem HTTP server."
audience: Operator
---

"""


def _capture_help(parser: argparse.ArgumentParser) -> str:
    buf = StringIO()
    parser.print_help(buf)
    return buf.getvalue()


def _collect_subcommands(parser: argparse.ArgumentParser, prefix: str = "") -> list[tuple[str, str]]:
    """Walk the parser tree and collect (full_command, help_text) pairs."""
    results: list[tuple[str, str]] = []
    results.append((prefix or parser.prog, _capture_help(parser)))

    for action in parser._actions:
        if isinstance(action, argparse._SubParsersAction):
            for name, subparser in action.choices.items():
                sub_prefix = f"{prefix} {name}" if prefix else f"{parser.prog} {name}"
                results.extend(_collect_subcommands(subparser, sub_prefix))

    return results


def _help_to_markdown(command: str, help_text: str, level: int = 2) -> str:
    hashes = "#" * level
    lines = [f"{hashes} `{command}`", "", "```", help_text.rstrip(), "```", ""]
    return "\n".join(lines)


def generate_stigmem_docs() -> str:
    from stigmem_node.cli import _build_parser
    parser = _build_parser()
    entries = _collect_subcommands(parser)

    parts = [FRONTMATTER_STIGMEM]
    parts.append("# stigmem CLI\n\n")
    parts.append("Auto-generated from `stigmem --help`. Regenerate with `make gen-cli-docs`.\n\n")

    for command, help_text in entries:
        depth = command.count(" ") + 2
        level = min(depth, 4)
        parts.append(_help_to_markdown(command, help_text, level))

    return "\n".join(parts)


def generate_node_docs() -> str:
    parts = [FRONTMATTER_NODE]
    parts.append("# stigmem-node CLI\n\n")
    parts.append("Auto-generated from `stigmem-node --help`. Regenerate with `make gen-cli-docs`.\n\n")
    parts.append("The `stigmem-node` command starts the Stigmem reference node HTTP server.\n\n")

    parts.append("## Usage\n\n")
    parts.append("```\n")
    parts.append("stigmem-node [--host HOST] [--port PORT]\n")
    parts.append("```\n\n")

    parts.append("## Environment Variables\n\n")
    parts.append("| Variable | Default | Description |\n")
    parts.append("|----------|---------|-------------|\n")
    parts.append("| `STIGMEM_HOST` | `0.0.0.0` | Bind address |\n")
    parts.append("| `STIGMEM_PORT` | `8765` | Listen port |\n")
    parts.append("| `STIGMEM_DB_PATH` | `stigmem.db` | SQLite database path |\n")
    parts.append("| `STIGMEM_AUTH_REQUIRED` | `false` | Require API key authentication |\n")
    parts.append("| `STIGMEM_SOURCE_ATTESTATION_MODE` | `warn` | Source attestation: `enforce`, `warn`, or `off` |\n")
    parts.append("| `STIGMEM_FEDERATION_PULL_INTERVAL` | `30` | Seconds between federation pull cycles |\n")
    parts.append("| `STIGMEM_EMBED_DIMENSIONS` | `768` | Embedding dimensions (Matryoshka truncation) |\n")
    parts.append("| `STIGMEM_CARD_MAX_AGE_S` | `86400` | Memory card staleness threshold (seconds) |\n")

    return "\n".join(parts)


def main() -> None:
    DOCS_CLI_DIR.mkdir(parents=True, exist_ok=True)

    stigmem_md = generate_stigmem_docs()
    (DOCS_CLI_DIR / "stigmem.md").write_text(stigmem_md)
    print(f"wrote {DOCS_CLI_DIR / 'stigmem.md'}")

    node_md = generate_node_docs()
    (DOCS_CLI_DIR / "stigmem-node.md").write_text(node_md)
    print(f"wrote {DOCS_CLI_DIR / 'stigmem-node.md'}")


if __name__ == "__main__":
    main()
