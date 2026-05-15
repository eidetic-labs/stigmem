"""Public runner: ``python -m stigmem_conformance --backend <name>``.

Runs the behavioral conformance suite against a stigmem node built on the
chosen backend and emits a Markdown report.

Examples::

    # In-process (default) — no external services required for sqlite/libsql
    python -m stigmem_conformance --backend sqlite
    python -m stigmem_conformance --backend libsql
    python -m stigmem_conformance --backend postgres --pg-dsn postgresql://localhost/stigmem_test

    # Save report for embedding in operator docs
    python -m stigmem_conformance --backend sqlite --report conformance-sqlite.md

Exit code 0 = all tests passed (skips allowed); 1 = one or more failures.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="python -m stigmem_conformance",
        description="Run the stigmem multi-backend conformance suite.",
    )
    parser.add_argument(
        "--backend",
        default="sqlite",
        choices=["sqlite", "libsql", "postgres"],
        help="Storage backend to test (default: sqlite)",
    )
    parser.add_argument(
        "--pg-dsn",
        default="",
        help="PostgreSQL DSN, e.g. postgresql://user:pw@localhost/dbname (postgres backend only)",
    )
    parser.add_argument(
        "--pg-schema",
        default="",
        help="PostgreSQL schema for table isolation (auto-generated if not set)",
    )
    parser.add_argument(
        "--report",
        default=None,
        metavar="PATH",
        help="Write Markdown report to this file (default: print to stdout)",
    )
    parser.add_argument(
        "--plugin-profile",
        default="default",
        choices=["default", "full"],
        help=(
            "Plugin install profile: default runs the v1.0 critical path with "
            "no plugins; full registers a representative signed plugin set."
        ),
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose pytest output",
    )
    args = parser.parse_args()

    # Propagate Postgres settings via env vars so the conformance conftest can
    # read them without requiring Settings to be importable at this point.
    if args.pg_dsn:
        os.environ["STIGMEM_TEST_PG_DSN"] = args.pg_dsn
    if args.pg_schema:
        os.environ["STIGMEM_TEST_PG_SCHEMA"] = args.pg_schema

    import pytest

    from stigmem_conformance.report import ConformanceReporter

    reporter = ConformanceReporter(backend=args.backend)

    tests_dir = Path(__file__).parent / "tests"
    pytest_args = [
        str(tests_dir),
        f"--conformance-backend={args.backend}",
        f"--conformance-plugin-profile={args.plugin_profile}",
        "--tb=short",
        "-p", "no:randomly",
    ]
    if args.verbose:
        pytest_args.append("-v")

    ret = pytest.main(pytest_args, plugins=[reporter])

    report_md = reporter.generate_markdown()
    if args.report:
        Path(args.report).write_text(report_md, encoding="utf-8")
        print(f"Report written to {args.report}", file=sys.stderr)
    else:
        print(report_md)

    sys.exit(0 if ret in (0, pytest.ExitCode.NO_TESTS_COLLECTED) else 1)


if __name__ == "__main__":
    main()
