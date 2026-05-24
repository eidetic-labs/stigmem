"""Verify MCP editor catalog consistency across public surfaces."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EDITOR_PATTERN = re.compile(r"docs/integrations/mcp/([a-z0-9-]+)")


def _readme_editors() -> set[str]:
    return set(EDITOR_PATTERN.findall((ROOT / "README.md").read_text()))


def _adapter_readme_editors() -> set[str]:
    return set(EDITOR_PATTERN.findall((ROOT / "adapters" / "mcp" / "README.md").read_text()))


def _docs_editors() -> set[str]:
    docs_dir = ROOT / "docs" / "docs" / "integrations" / "mcp"
    return {path.stem for path in docs_dir.glob("*.md") if path.stem != "index"}


def _cli_editors() -> set[str]:
    sys.path.insert(0, str(ROOT / "node" / "src"))
    from stigmem_node.cli.mcp import EDITOR_CONFIGS

    return set(EDITOR_CONFIGS)


def main() -> int:
    readme = _readme_editors()
    adapter_readme = _adapter_readme_editors()
    docs = _docs_editors()
    cli = _cli_editors()
    expected = cli
    failures: list[str] = []
    for name, observed in {
        "README.md": readme,
        "adapters/mcp/README.md": adapter_readme,
        "docs/docs/integrations/mcp": docs,
        "EDITOR_CONFIGS": cli,
    }.items():
        if observed != expected:
            failures.append(f"{name}: expected {sorted(expected)}, observed {sorted(observed)}")
    if failures:
        print("FAIL: MCP catalog inconsistency detected")
        for failure in failures:
            print(f"  {failure}")
        return 1
    print(f"mcp-readme-consistency: {len(expected)} editors aligned")
    return 0


if __name__ == "__main__":
    sys.exit(main())
