"""Compatibility smoke tests for the historical stigmem_node.models import surface."""

from __future__ import annotations


def test_models_compat_surface_still_reexports_core_shapes() -> None:
    from stigmem_node.models import (
        VALID_SCOPES,
        AssertRequest,
        FactRecord,
        FactValue,
        QueryResponse,
        TombstoneRecord,
    )

    assert AssertRequest.__name__ == "AssertRequest"
    assert FactRecord.__name__ == "FactRecord"
    assert FactValue.__name__ == "FactValue"
    assert QueryResponse.__name__ == "QueryResponse"
    assert TombstoneRecord.__name__ == "TombstoneRecord"
    assert "local" in VALID_SCOPES
