"""
Stigmem v2.0 conformance suite.

Loads machine-readable test vectors from data/conformance/v2.0/*.json and
runs each against a fresh in-process test node. Any regression fails CI.

Vector file schema:
  { "spec_section": "...", "title": "...", "vectors": [ <Vector>, ... ] }

Vector fields (inherits all v1 types, plus v2.0 additions):
  id, description, method, path, body?,
  expected_status (or expected_status_in),
  expected_body_contains?, expected_body_has_keys?,
  expected_nested?, expected_body_list_contains?,
  expected_body_value_in?,
  expected_field_starts_with?,  # {field: prefix} — e.g. {"cid": "sha256:"}
  expected_field_length?,       # {field: int} — exact string length check
  expected_first_fact_has_keys?,          # keys to check in body["facts"][0]
  expected_first_fact_score_breakdown_keys?,  # keys in facts[0]["score_breakdown"]
  requires_setup?,   # id of another vector that must run first (same DB)
  requires_auth?     # bool: requires auth-enabled client (skipped for now)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

_REPO_ROOT = Path(__file__).resolve().parents[3]
_VECTOR_DIR = _REPO_ROOT / "data" / "conformance" / "v2.0"
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Load vectors — all *.json files in v2.0/
# ---------------------------------------------------------------------------


def _load_file_groups() -> list[tuple[str, list[dict[str, Any]]]]:
    """Return [(filename, [vector, ...]), ...] for each vector file."""
    groups: list[tuple[str, list[dict[str, Any]]]] = []
    for path in sorted(_VECTOR_DIR.glob("*.json")):
        with path.open() as f:
            data = json.load(f)
        required_plugin = data.get("requires_plugin")
        vectors = data.get("vectors", [])
        if required_plugin:
            for vector in vectors:
                vector.setdefault("requires_plugin", required_plugin)
        groups.append((path.name, vectors))
    return groups


_GROUPS = _load_file_groups()

_VECTOR_INDEX: dict[str, dict[str, Any]] = {}
for _fname, _vecs in _GROUPS:
    for _v in _vecs:
        _VECTOR_INDEX[_v["id"]] = _v


# ---------------------------------------------------------------------------
# Assertion helpers
# ---------------------------------------------------------------------------


def _assert_contains(actual: Any, expected: Any, *, path: str) -> None:
    """Recursively assert that actual contains the structure in expected."""
    if isinstance(expected, dict):
        assert isinstance(actual, dict), f"{path}: expected dict, got {type(actual)}"
        for k, v in expected.items():
            assert k in actual, f"{path}: missing key '{k}'"
            _assert_contains(actual[k], v, path=f"{path}.{k}")
    elif isinstance(expected, list):
        assert isinstance(actual, list), f"{path}: expected list, got {type(actual)}"
        for item in expected:
            if isinstance(item, dict):
                match = any(all(a.get(k) == v for k, v in item.items()) for a in actual)
                assert match, f"{path}: list missing item matching {item!r}"
    else:
        assert actual == expected, f"{path}: got {actual!r}, expected {expected!r}"


# ---------------------------------------------------------------------------
# Request execution
# ---------------------------------------------------------------------------


def _do_request(client: TestClient, vector: dict[str, Any]) -> Any:
    method = vector["method"].lower()
    path = vector["path"]
    body = vector.get("body")
    kwargs: dict[str, Any] = {}
    if body is not None:
        kwargs["json"] = body
    return getattr(client, method)(path, **kwargs)


def _run_setup_chain(
    client: TestClient,
    vector: dict[str, Any],
    *,
    seen: set[str] | None = None,
) -> None:
    if seen is None:
        seen = set()
    prereq_id = vector.get("requires_setup")
    if not prereq_id or prereq_id in seen:
        return
    prereq = _VECTOR_INDEX.get(prereq_id)
    if prereq is None:
        return
    _run_setup_chain(client, prereq, seen=seen)
    if prereq_id not in seen:
        seen.add(prereq_id)
        resp = _do_request(client, prereq)
        assert resp.status_code < 300, (
            f"Setup vector '{prereq_id}' failed: HTTP {resp.status_code}: {resp.text}"
        )


# ---------------------------------------------------------------------------
# Parametrised tests
# ---------------------------------------------------------------------------

_ALL_PARAMS: list[tuple[str, dict[str, Any]]] = []
for _fname, _vecs in _GROUPS:
    _ALL_PARAMS.extend([(f"{_fname}::{v['id']}", v) for v in _vecs])


def _v2_assert_status(resp: Any, vector: dict[str, Any], ctx: str) -> None:
    expected_status = vector.get("expected_status")
    status_in = vector.get("expected_status_in")
    if expected_status is not None:
        assert resp.status_code == expected_status, (
            f"{ctx}: expected HTTP {expected_status}, got {resp.status_code}. Body: {resp.text}"
        )
    elif status_in is not None:
        assert resp.status_code in status_in, (
            f"{ctx}: expected HTTP in {status_in}, got {resp.status_code}. Body: {resp.text}"
        )


def _v2_validate_error_nested(body: Any, vector: dict[str, Any], ctx: str) -> None:
    """Best-effort nested checks on an error response — bail early on missing keys."""
    for dotted_path, expected_val in vector.get("expected_nested", {}).items():
        current: Any = body
        for part in dotted_path.split("."):
            if not (isinstance(current, dict) and part in current):
                return
            current = current[part]
        assert current == expected_val, (
            f"{ctx}: {dotted_path} = {current!r}, expected {expected_val!r}"
        )


def _v2_assert_nested(body: dict[str, Any], expectations: dict[str, Any], ctx: str) -> None:
    for dotted_path, expected_val in expectations.items():
        current: Any = body
        for part in dotted_path.split("."):
            assert isinstance(current, dict) and part in current, (
                f"{ctx}: path '{dotted_path}' — missing key '{part}'"
            )
            current = current[part]
        assert current == expected_val, (
            f"{ctx}: {dotted_path} = {current!r}, expected {expected_val!r}"
        )


def _v2_assert_list_contains(
    body: dict[str, Any], list_expectations: dict[str, Any], ctx: str
) -> None:
    for list_key, expected_item in list_expectations.items():
        assert list_key in body, f"{ctx}: missing list key '{list_key}'"
        actual_list = body[list_key]
        assert isinstance(actual_list, list), f"{ctx}: '{list_key}' is not a list"
        if isinstance(expected_item, dict):
            assert any(all(a.get(k) == v for k, v in expected_item.items()) for a in actual_list), (
                f"{ctx}: list '{list_key}' missing item matching {expected_item!r}"
            )
        else:
            assert expected_item in actual_list, (
                f"{ctx}: '{expected_item}' not in {list_key}: {actual_list!r}"
            )


def _v2_assert_field_constraints(body: dict[str, Any], vector: dict[str, Any], ctx: str) -> None:
    """value-in / starts-with / length checks (v2.0 additions)."""
    if "expected_body_value_in" in vector:
        for field, allowed in vector["expected_body_value_in"].items():
            assert field in body, f"{ctx}: missing field '{field}'"
            assert body[field] in allowed, (
                f"{ctx}: {field} = {body[field]!r}, expected one of {allowed!r}"
            )
    for field, prefix in vector.get("expected_field_starts_with", {}).items():
        assert field in body, f"{ctx}: missing field '{field}' for starts-with check"
        assert isinstance(body[field], str) and body[field].startswith(prefix), (
            f"{ctx}: {field} = {body[field]!r}, expected to start with {prefix!r}"
        )
    for field, expected_len in vector.get("expected_field_length", {}).items():
        assert field in body, f"{ctx}: missing field '{field}' for length check"
        assert len(body[field]) == expected_len, (
            f"{ctx}: len({field}) = {len(body[field])}, expected {expected_len}"
        )


def _v2_assert_first_fact_shape(body: dict[str, Any], vector: dict[str, Any], ctx: str) -> None:
    """recall-response first-fact key + score_breakdown contract checks."""
    first_fact_keys = vector.get("expected_first_fact_has_keys", [])
    if first_fact_keys:
        facts = body.get("facts", [])
        if facts:
            for key in first_fact_keys:
                assert key in facts[0], f"{ctx}: facts[0] missing key '{key}'"

    bd_keys = vector.get("expected_first_fact_score_breakdown_keys", [])
    if bd_keys:
        facts = body.get("facts", [])
        if facts and "score_breakdown" in facts[0]:
            for key in bd_keys:
                assert key in facts[0]["score_breakdown"], (
                    f"{ctx}: facts[0].score_breakdown missing key '{key}'"
                )


def _v2_assert_body_expectations(body: dict[str, Any], vector: dict[str, Any], ctx: str) -> None:
    """Apply every body-shape expectation for a happy-path v2 response."""
    for key in vector.get("expected_body_has_keys", []):
        assert key in body, f"{ctx}: response missing required key '{key}'"

    if "expected_body_contains" in vector:
        _assert_contains(body, vector["expected_body_contains"], path=ctx)

    _v2_assert_nested(body, vector.get("expected_nested", {}), ctx)
    _v2_assert_list_contains(body, vector.get("expected_body_list_contains", {}), ctx)
    _v2_assert_field_constraints(body, vector, ctx)
    _v2_assert_first_fact_shape(body, vector, ctx)

    if vector.get("expected_response_is_list"):
        assert isinstance(body, list), f"{ctx}: expected list response, got {type(body)}"


@pytest.mark.parametrize(
    "vector",
    [p[1] for p in _ALL_PARAMS],
    ids=[p[0] for p in _ALL_PARAMS],
)
def test_conformance_vector_v2(client: TestClient, vector: dict[str, Any]) -> None:
    vec_id = vector["id"]
    ctx = f"[{vec_id}] {vector.get('description', '')}"

    if vector.get("requires_auth"):
        pytest.skip(f"{ctx}: skipped (requires_auth — covered by dedicated auth tests)")
    if vector.get("requires_plugin"):
        pytest.skip(f"{ctx}: skipped (requires plugin {vector['requires_plugin']!r})")

    _run_setup_chain(client, vector)

    resp = _do_request(client, vector)
    try:
        body = resp.json()
    except ValueError as exc:
        logger.debug("%s: response body is not JSON: %s", ctx, exc)
        body = {}

    _v2_assert_status(resp, vector, ctx)

    if resp.status_code >= 400:
        _v2_validate_error_nested(body, vector, ctx)
        return

    _v2_assert_body_expectations(body, vector, ctx)
