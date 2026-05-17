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

uv run pytest node/tests/federation/test_malicious_peer.py -q --tb=short

END_TIME=$(date +%s)
ELAPSED=$(( END_TIME - START_TIME ))

echo ""
echo "========================================"
echo " malicious-peer demo PASSED (${ELAPSED}s)"
echo "========================================"
