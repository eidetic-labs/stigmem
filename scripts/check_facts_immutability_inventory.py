"""Check the ADR-016 direct facts-mutation inventory."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / "node" / "src" / "stigmem_node"
INVENTORY_PATH = ROOT / "spec" / "security" / "facts-mutation-inventory.json"
MUTATION_RE = re.compile(r"\b(?:UPDATE\s+facts|DELETE\s+FROM\s+facts)\b", re.IGNORECASE)


def _load_inventory(path: Path = INVENTORY_PATH) -> dict[str, int]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected JSON object")
    entries: Any = data.get("remaining_direct_fact_mutations")
    if not isinstance(entries, dict):
        raise ValueError(f"{path}: missing remaining_direct_fact_mutations object")
    return {str(file_path): int(count) for file_path, count in entries.items()}


def _scan() -> dict[str, int]:
    counts: Counter[str] = Counter()
    for path in sorted(SRC_ROOT.rglob("*.py")):
        rel = path.relative_to(ROOT).as_posix()
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if rel.endswith("instruction_migrate.py") and "CREATE/UPDATE facts" in line:
                continue
            if MUTATION_RE.search(line):
                counts[rel] += 1
    return dict(counts)


def check() -> int:
    expected = _load_inventory()
    actual = _scan()
    if actual != expected:
        print("ERROR: direct facts mutation inventory changed", file=sys.stderr)
        print(f"expected: {json.dumps(expected, indent=2, sort_keys=True)}", file=sys.stderr)
        print(f"actual:   {json.dumps(actual, indent=2, sort_keys=True)}", file=sys.stderr)
        print(
            "Move new mutable state to projections, or update the inventory when "
            "a planned §5.2a slice removes an existing mutation path.",
            file=sys.stderr,
        )
        return 1
    print(f"OK: tracked {sum(actual.values())} remaining direct facts mutations")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(check())
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
