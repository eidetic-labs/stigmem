#!/usr/bin/env python3
"""Fail when coverage drops below the staged-rollout baseline.

Sister script to check_ruff_baseline.py and check_mypy_baseline.py.

Reads the project-wide line-coverage percentage for ``node/src/`` from
the existing ``.coverage`` data file (no re-run; relies on whatever
``coverage run`` step ran earlier in the pipeline) and compares it to
the floor stored at ``.github/baselines/python-coverage.txt``.

Use ``--write-baseline`` to raise (or, rarely, lower) the floor after a
net coverage improvement has landed and is intentional.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASELINE = ROOT / ".github" / "baselines" / "python-coverage.txt"
INCLUDE_GLOB = "node/src/*"


def _measure_total() -> int:
    """Return current total line coverage as an int percentage."""
    result = subprocess.run(  # noqa: S603,S607  trusted CLI invocation
        ["coverage", "report", f"--include={INCLUDE_GLOB}", "--format=total"],  # noqa: S607
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        sys.stderr.write(
            "\nCoverage data not found. Run `coverage run -m pytest node/tests` first.\n"
        )
        raise SystemExit(2)
    raw = result.stdout.strip()
    try:
        return int(raw)
    except ValueError:
        sys.stderr.write(f"Unexpected coverage output: {raw!r}\n")
        raise SystemExit(2) from None


def _load_floor() -> int | None:
    if not BASELINE.exists():
        return None
    for line in BASELINE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            return int(line)
    return None


def _write_floor(percentage: int) -> None:
    header = [
        "# Coverage baseline for staged rollout.",
        "# Single integer percentage on a non-comment line.",
        "# Raise via: `python scripts/check_coverage_baseline.py --write-baseline`",
        "",
    ]
    BASELINE.parent.mkdir(parents=True, exist_ok=True)
    BASELINE.write_text("\n".join(header + [str(percentage)]) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help="Refresh the committed baseline from the current coverage measurement.",
    )
    args = parser.parse_args()

    current = _measure_total()

    if args.write_baseline:
        _write_floor(current)
        print(f"Wrote coverage baseline {current}% to {BASELINE.relative_to(ROOT)}.")
        return 0

    floor = _load_floor()
    if floor is None:
        sys.stderr.write(
            f"No baseline at {BASELINE.relative_to(ROOT)}. "
            "Establish one with `--write-baseline`.\n"
        )
        return 1

    if current < floor:
        sys.stderr.write(
            f"Coverage {current}% < baseline {floor}%. "
            "To raise the floor (after a net coverage improvement lands), "
            "re-run with --write-baseline.\n"
        )
        return 1

    delta = current - floor
    delta_str = f"+{delta}" if delta > 0 else "±0"
    print(f"Coverage baseline check passed: current={current}% baseline={floor}% ({delta_str}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
