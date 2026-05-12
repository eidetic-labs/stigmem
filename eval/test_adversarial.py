"""Pytest entry-point for the adversarial corpus (79 scenarios).

Run via:
    pytest eval/test_adversarial.py -v

Or as part of make eval-fast.
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

import pytest

from eval.harness.adversarial import (
    run_capability_token,
    run_contradiction_floods,
    run_sanitizer_bypass,
    run_tombstone_bypass,
    run_typo_squatted,
)
from eval.harness.utils import load_adversarial_class, load_all_adversarial

RESULTS_DIR = pathlib.Path(__file__).parent / "results"


# ---------------------------------------------------------------------------
# Parametrised scenario tests
# ---------------------------------------------------------------------------


def _adv_scenarios(class_name: str) -> list[dict[str, Any]]:
    return load_adversarial_class(class_name)


@pytest.mark.parametrize(
    "scenario",
    _adv_scenarios("typo_squatted"),
    ids=lambda s: s["id"],
)
def test_typo_squatted(eval_node, scenario):
    results = run_typo_squatted(eval_node, [scenario])
    r = results[0]
    assert r["passed"], f"FAIL {r['id']}: {r['description']}\n{json.dumps(r['detail'], indent=2)}"


@pytest.mark.parametrize(
    "scenario",
    _adv_scenarios("contradiction_floods"),
    ids=lambda s: s["id"],
)
def test_contradiction_floods(eval_node, scenario):
    results = run_contradiction_floods(eval_node, [scenario])
    r = results[0]
    assert r["passed"], f"FAIL {r['id']}: {r['description']}\n{json.dumps(r['detail'], indent=2)}"


@pytest.mark.parametrize(
    "scenario",
    _adv_scenarios("tombstone_bypass"),
    ids=lambda s: s["id"],
)
def test_tombstone_bypass(eval_node, scenario):
    results = run_tombstone_bypass(eval_node, [scenario])
    r = results[0]
    assert r["passed"], f"FAIL {r['id']}: {r['description']}\n{json.dumps(r['detail'], indent=2)}"


@pytest.mark.parametrize(
    "scenario",
    _adv_scenarios("capability_token"),
    ids=lambda s: s["id"],
)
def test_capability_token(auth_eval_node, scenario):
    results = run_capability_token(auth_eval_node, [scenario])
    r = results[0]
    assert r["passed"], f"FAIL {r['id']}: {r['description']}\n{json.dumps(r['detail'], indent=2)}"


@pytest.mark.parametrize(
    "scenario",
    _adv_scenarios("sanitizer_bypass"),
    ids=lambda s: s["id"],
)
def test_sanitizer_bypass(eval_node, scenario):
    results = run_sanitizer_bypass(eval_node, [scenario])
    r = results[0]
    assert r["passed"], f"FAIL {r['id']}: {r['description']}\n{json.dumps(r['detail'], indent=2)}"


# ---------------------------------------------------------------------------
# Full-run timing guard (≤ 5 min total)
# ---------------------------------------------------------------------------


def test_adversarial_total_count():
    """All 79 scenarios are present in the corpus."""
    corpus = load_all_adversarial()
    total = sum(len(v) for v in corpus.values())
    assert total == 79, f"Expected 79 scenarios, got {total}"
