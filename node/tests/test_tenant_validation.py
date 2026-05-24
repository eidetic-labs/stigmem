from __future__ import annotations

import pytest

from stigmem_node.tenant import TenantIdError, validate_tenant_id


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("default", "default"),
        ("Default", "default"),
        ("  Customer-A  ", "customer-a"),
        ("UPPER", "upper"),
        ("ａｃｍｅ", "acme"),
    ],
)
def test_validate_tenant_id_normalizes_valid_values(raw: str, expected: str) -> None:
    assert validate_tenant_id(raw) == expected
    assert validate_tenant_id(validate_tenant_id(raw)) == expected


@pytest.mark.parametrize(
    "raw",
    [
        None,
        "",
        "   ",
    ],
)
def test_validate_tenant_id_rejects_empty_values(raw: str | None) -> None:
    with pytest.raises(TenantIdError, match="tenant_id_empty"):
        validate_tenant_id(raw)


@pytest.mark.parametrize(
    "raw",
    [
        "a" * 64,
        "-leading-hyphen",
        "contains spaces",
        "contains/slash",
        "contains_underscore",
    ],
)
def test_validate_tenant_id_rejects_invalid_values(raw: str) -> None:
    with pytest.raises(TenantIdError, match="tenant_id_invalid"):
        validate_tenant_id(raw)
