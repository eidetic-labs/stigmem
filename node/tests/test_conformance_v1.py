"""
Stigmem v1.0 conformance suite.

Loads machine-readable test vectors from data/conformance/v1.0/0*.json and
runs each against a fresh in-process test node. Any regression fails CI.

Vector file schema:
  { "spec_section": "...", "title": "...", "vectors": [ <Vector>, ... ] }

Vector fields:
  id, description, method, path, body?,
  expected_status (or expected_status_in),
  expected_body_contains?, expected_body_has_keys?,
  expected_nested?, expected_body_list_contains?,
  expected_body_value_in?,
  expected_members_contain_role?, expected_response_is_list?,
  requires_setup?,   # id of another vector that must run first (same DB)
  requires_garden?,  # slug of garden to create before this test
  requires_auth?     # bool: requires auth-enabled client (skipped for now)

Adding a new spec feature? Add at least one vector to data/conformance/v1.0/
and ensure the test runner handles any new assertion types.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

_REPO_ROOT = Path(__file__).resolve().parents[2]
_VECTOR_DIR = _REPO_ROOT / "data" / "conformance" / "v1.0"


# ---------------------------------------------------------------------------
# Load vectors — only from the numbered 0*.json files (canonical set)
# ---------------------------------------------------------------------------

def _load_file_groups() -> list[tuple[str, list[dict[str, Any]]]]:
    """Return [(filename, [vector, ...]), ...] for each numbered vector file."""
    groups: list[tuple[str, list[dict[str, Any]]]] = []
    for path in sorted(_VECTOR_DIR.glob("0*.json")):
        with path.open() as f:
            data = json.load(f)
        groups.append((path.name, data.get("vectors", [])))
    return groups


_GROUPS = _load_file_groups()

# Build a flat index: vector_id -> vector (for setup lookups)
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
                match = any(
                    all(a.get(k) == v for k, v in item.items())
                    for a in actual
                )
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


def _setup_garden(client: TestClient, slug: str) -> None:
    resp = client.post("/v1/gardens", json={"slug": slug, "name": slug, "scope": "local"})
    assert resp.status_code in (201, 409), (
        f"Garden setup for '{slug}' failed: {resp.status_code}: {resp.text}"
    )


# ---------------------------------------------------------------------------
# Parametrised tests — one per file group to allow shared setup within a file
# ---------------------------------------------------------------------------

def _make_vectors_for_file(fname: str, vectors: list[dict[str, Any]]) -> list[Any]:
    return [(fname, v) for v in vectors]


_ALL_PARAMS: list[tuple[str, dict[str, Any]]] = []
for _fname, _vecs in _GROUPS:
    _ALL_PARAMS.extend([(f"{_fname}::{v['id']}", v) for v in _vecs])


@pytest.mark.parametrize(
    "vector",
    [p[1] for p in _ALL_PARAMS],
    ids=[p[0] for p in _ALL_PARAMS],
)
def test_conformance_vector(client: TestClient, vector: dict[str, Any]) -> None:
    vec_id = vector["id"]
    ctx = f"[{vec_id}] {vector.get('description', '')}"

    # Skip auth-requiring vectors (auth tests are covered by test_oidc.py etc.)
    if vector.get("requires_auth"):
        pytest.skip(f"{ctx}: skipped (requires_auth — covered by dedicated auth tests)")

    # Set up any garden prerequisite
    garden_slug = vector.get("requires_garden")
    if garden_slug:
        _setup_garden(client, garden_slug)

    # Run dependency chain setup
    _run_setup_chain(client, vector)

    # Execute the vector
    resp = _do_request(client, vector)
    body: dict[str, Any] = {}
    try:
        body = resp.json()
    except Exception:
        pass

    # Status assertion
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

    # Short-circuit on error responses
    if resp.status_code >= 400:
        return

    # Required keys
    for key in vector.get("expected_body_has_keys", []):
        assert key in body, f"{ctx}: response missing required key '{key}'"

    # Body contains subset
    if "expected_body_contains" in vector:
        _assert_contains(body, vector["expected_body_contains"], path=ctx)

    # Nested assertion — dotted-path dict: {"value.type": "number", "value.v": 42.5}
    for dotted_path, expected_val in vector.get("expected_nested", {}).items():
        parts = dotted_path.split(".")
        current: Any = body
        for part in parts:
            assert isinstance(current, dict) and part in current, (
                f"{ctx}: path '{dotted_path}' — missing key '{part}'"
            )
            current = current[part]
        assert current == expected_val, (
            f"{ctx}: {dotted_path} = {current!r}, expected {expected_val!r}"
        )

    # List contains — dict where value is item to find in body[key] (primitive or dict)
    for list_key, expected_item in vector.get("expected_body_list_contains", {}).items():
        assert list_key in body, f"{ctx}: missing list key '{list_key}'"
        actual_list = body[list_key]
        assert isinstance(actual_list, list), f"{ctx}: '{list_key}' is not a list"
        if isinstance(expected_item, dict):
            assert any(
                all(a.get(k) == v for k, v in expected_item.items())
                for a in actual_list
            ), f"{ctx}: list '{list_key}' missing item matching {expected_item!r}"
        else:
            assert expected_item in actual_list, (
                f"{ctx}: '{expected_item}' not in {list_key}: {actual_list!r}"
            )

    # Value in set
    if "expected_body_value_in" in vector:
        for field, allowed in vector["expected_body_value_in"].items():
            assert field in body, f"{ctx}: missing field '{field}'"
            assert body[field] in allowed, (
                f"{ctx}: {field} = {body[field]!r}, expected one of {allowed!r}"
            )

    # Response is list
    if vector.get("expected_response_is_list"):
        assert isinstance(body, list), f"{ctx}: expected list response, got {type(body)}"

    # Members contain role (garden-specific)
    if "expected_members_contain_role" in vector:
        expected_role = vector["expected_members_contain_role"]
        members = body.get("members", [])
        assert any(m.get("role") == expected_role for m in members), (
            f"{ctx}: no member with role '{expected_role}' in {members!r}"
        )
