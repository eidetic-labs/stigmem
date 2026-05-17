"""Repository-wide pytest marker taxonomy for staged test-suite organization."""

from __future__ import annotations

from pathlib import Path

import pytest


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        rel = Path(str(item.fspath)).as_posix()

        if rel.startswith("eval/"):
            item.add_marker(pytest.mark.eval)
            item.add_marker(pytest.mark.slow)

        if rel.startswith("node/src/stigmem_conformance/tests/") or "/conformance/" in rel:
            item.add_marker(pytest.mark.conformance)
            item.add_marker(pytest.mark.integration)

        if rel.endswith("node/tests/test_conformance_v1.py"):
            item.add_marker(pytest.mark.conformance)
            item.add_marker(pytest.mark.integration)
        elif rel.startswith("node/tests/"):
            item.add_marker(pytest.mark.integration)

        if rel.startswith("sdks/stigmem-py/tests/"):
            item.add_marker(pytest.mark.unit)

        if rel.startswith("adapters/") and "/tests/" in rel:
            item.add_marker(pytest.mark.unit)

        if rel.startswith("experimental/"):
            item.add_marker(pytest.mark.experimental)

        if (
            "security" in rel
            or "adversarial" in rel
            or rel.endswith("test_mtls.py")
            or rel.endswith("test_auth.py")
            or rel.endswith("test_argon2_auth.py")
        ):
            item.add_marker(pytest.mark.security)
