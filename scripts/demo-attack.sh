#!/usr/bin/env bash
# demo-attack.sh — demonstrate malicious federation push rejection.
#
# This intentionally runs the focused malicious-peer acceptance gate instead of
# starting a long-lived demo cluster. The tests exercise the reference node's
# federation push endpoint with a registered peer that is only allowed to write
# public scope, then verify that:
#   1. company-scope facts from that peer are rejected and audited; and
#   2. source-forged public facts are rejected, audited, and not stored.

set -euo pipefail

START_TIME=$(date +%s)

echo "Stigmem malicious-peer rejection demo"
echo ""
echo "Scenario 1: peer is authorized for public scope only, then pushes company data."
echo "Expected: rejected=1, accepted=0, federation_audit records scope_violation."
echo ""
echo "Scenario 2: peer pushes a public fact with a forged source identity."
echo "Expected: rejected=1, accepted=0, audit records source_not_owned, fact is not stored."
echo ""
echo "Running focused acceptance gate..."
echo ""

set +e
uv run pytest node/tests/federation/test_malicious_peer.py -q --tb=short
PYTEST_STATUS=$?
set -e

END_TIME=$(date +%s)
ELAPSED=$(( END_TIME - START_TIME ))

if [[ -n "${DEMO_ATTACK_TRANSCRIPT:-}" ]]; then
  export DEMO_ATTACK_TRANSCRIPT
  export DEMO_ATTACK_ELAPSED_S="${ELAPSED}"
  export DEMO_ATTACK_PYTEST_STATUS="${PYTEST_STATUS}"
  python3 - <<'PY'
from __future__ import annotations

import json
import os
from pathlib import Path

path = Path(os.environ["DEMO_ATTACK_TRANSCRIPT"])
path.parent.mkdir(parents=True, exist_ok=True)

pytest_status = int(os.environ["DEMO_ATTACK_PYTEST_STATUS"])
gate_passed = pytest_status == 0

transcript = {
    "demo": "demo-attack",
    "elapsed_s": int(os.environ["DEMO_ATTACK_ELAPSED_S"]),
    "acceptance_gate": {
        "command": "uv run pytest node/tests/federation/test_malicious_peer.py -q --tb=short",
        "exit_code": pytest_status,
        "passed": gate_passed,
    },
    "scenarios": [
        {
            "name": "unauthorized scope write",
            "expected": {
                "accepted": 0,
                "rejected": 1,
                "audit_event": "scope_violation",
            },
            "observed": {
                "accepted": 0 if gate_passed else None,
                "rejected": 1 if gate_passed else None,
                "audit_event": "scope_violation" if gate_passed else None,
                "verified": gate_passed,
            },
        },
        {
            "name": "source-forged public write",
            "expected": {
                "accepted": 0,
                "rejected": 1,
                "error": "source_not_owned",
                "stored": False,
            },
            "observed": {
                "accepted": 0 if gate_passed else None,
                "rejected": 1 if gate_passed else None,
                "error": "source_not_owned" if gate_passed else None,
                "stored": False if gate_passed else None,
                "verified": gate_passed,
            },
        },
    ],
}

path.write_text(json.dumps(transcript, indent=2, sort_keys=True) + "\n", encoding="utf-8")
PY
  echo "Transcript written to ${DEMO_ATTACK_TRANSCRIPT}"
fi

if [[ "${PYTEST_STATUS}" -ne 0 ]]; then
  exit "${PYTEST_STATUS}"
fi

echo ""
echo "========================================"
echo " malicious-peer demo PASSED (${ELAPSED}s)"
echo "========================================"
