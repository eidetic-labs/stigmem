#!/usr/bin/env python3
"""Build a per-package coverage summary from Python XML and TypeScript lcov."""

from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "coverage" / "summary.md"
PYTHON_XML = ROOT / "coverage" / "python" / "coverage.xml"


@dataclass
class Totals:
    lines_hit: int = 0
    lines_found: int = 0
    branches_hit: int = 0
    branches_found: int = 0

    def add(self, *, lines_hit: int, lines_found: int, branches_hit: int = 0, branches_found: int = 0) -> None:
        self.lines_hit += lines_hit
        self.lines_found += lines_found
        self.branches_hit += branches_hit
        self.branches_found += branches_found

    def line_rate(self) -> str:
        if not self.lines_found:
            return "n/a"
        return f"{(self.lines_hit / self.lines_found) * 100:.1f}%"

    def branch_rate(self) -> str:
        if not self.branches_found:
            return "n/a"
        return f"{(self.branches_hit / self.branches_found) * 100:.1f}%"


def parse_python() -> dict[str, Totals]:
    packages = {
        "node/src": Totals(),
        "sdks/stigmem-py/src": Totals(),
    }
    if not PYTHON_XML.exists():
        return packages

    root = ET.parse(PYTHON_XML).getroot()
    for class_el in root.findall(".//class"):
        filename = class_el.attrib.get("filename", "")
        for prefix in packages:
            if not filename.startswith(prefix):
                continue
            totals = packages[prefix]
            for line_el in class_el.findall("./lines/line"):
                totals.lines_found += 1
                if int(line_el.attrib.get("hits", "0")) > 0:
                    totals.lines_hit += 1
                if line_el.attrib.get("branch") == "true":
                    match = re.search(r"\((\d+)/(\d+)\)", line_el.attrib.get("condition-coverage", ""))
                    if match:
                        totals.branches_hit += int(match.group(1))
                        totals.branches_found += int(match.group(2))
            break
    return packages


def parse_lcov(path: Path) -> Totals:
    totals = Totals()
    if not path.exists():
        return totals
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("DA:"):
            _, data = line.split(":", 1)
            _lineno, hits = data.split(",", 1)
            totals.lines_found += 1
            if int(hits) > 0:
                totals.lines_hit += 1
        elif line.startswith("BRDA:"):
            _, data = line.split(":", 1)
            _line, _block, _branch, taken = data.split(",", 3)
            totals.branches_found += 1
            if taken != "-" and int(taken) > 0:
                totals.branches_hit += 1
    return totals


def main() -> int:
    rows: list[tuple[str, Totals]] = []
    python = parse_python()
    rows.extend(python.items())
    rows.extend(
        [
            ("sdks/stigmem-ts", parse_lcov(ROOT / "sdks" / "stigmem-ts" / "coverage" / "lcov.info")),
            ("adapters/mcp", parse_lcov(ROOT / "adapters" / "mcp" / "coverage" / "lcov.info")),
            ("apps/dashboard", parse_lcov(ROOT / "apps" / "dashboard" / "coverage" / "lcov.info")),
        ]
    )

    lines = [
        "# Coverage Summary",
        "",
        "| Package | Line Coverage | Branch Coverage |",
        "|---------|---------------|-----------------|",
    ]
    for name, totals in rows:
        lines.append(f"| `{name}` | {totals.line_rate()} | {totals.branch_rate()} |")
    text = "\n".join(lines) + "\n"
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(text, encoding="utf-8")
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
