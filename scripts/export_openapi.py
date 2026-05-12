#!/usr/bin/env python3
"""Generate or verify the committed OpenAPI artifact from the FastAPI app."""

from __future__ import annotations

import argparse
import difflib
import json
from pathlib import Path

from stigmem_node.main import create_app

ROOT = Path(__file__).resolve().parent.parent
OPENAPI_PATH = ROOT / "docs" / "openapi" / "stigmem.json"


def _render_openapi() -> str:
    spec = create_app().openapi()
    return json.dumps(spec, indent=2, sort_keys=True) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if the committed OpenAPI artifact does not match the generated app schema.",
    )
    args = parser.parse_args()

    rendered = _render_openapi()

    if args.check:
        current = OPENAPI_PATH.read_text(encoding="utf-8")
        if current == rendered:
            print("OpenAPI artifact is up to date.")
            return 0

        diff = difflib.unified_diff(
            current.splitlines(),
            rendered.splitlines(),
            fromfile=str(OPENAPI_PATH.relative_to(ROOT)),
            tofile="generated-openapi",
            lineterm="",
        )
        print("OpenAPI drift detected. Regenerate with `uv run python scripts/export_openapi.py`.")
        for line in diff:
            print(line)
        return 1

    OPENAPI_PATH.parent.mkdir(parents=True, exist_ok=True)
    OPENAPI_PATH.write_text(rendered, encoding="utf-8")
    print(f"Wrote OpenAPI artifact to {OPENAPI_PATH.relative_to(ROOT)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
