#!/usr/bin/env python3
"""Register full-mesh peers on all 4 soak nodes.

Run after all 4 containers are healthy:
    python soak/setup_peers.py --env soak/.env

For each of the 12 (node, peer) pairs, this script:
  1. Reads the peer's pubkey + node_id from its /.well-known/stigmem
  2. Creates a PeerDeclaration signed by the peer's own private key
  3. Calls POST /v1/federation/peers on the registering node using a
     federate API key created via docker exec

The anon identity lacks federate permission, so we create a per-node
API key with read+write+federate via docker exec before registration.
"""

from __future__ import annotations

import argparse
import base64
import json
import subprocess
import sys
import time
from datetime import UTC, datetime

import requests
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

# ---------------------------------------------------------------------------
# Node configuration
# ---------------------------------------------------------------------------

NODES = [
    {
        "letter": "A",
        "name": "node-a",
        "host_url": "http://localhost:8765",
        "internal_url": "http://node-a:8765",
        "container": "soak-node-a",
    },
    {
        "letter": "B",
        "name": "node-b",
        "host_url": "http://localhost:8766",
        "internal_url": "http://node-b:8765",
        "container": "soak-node-b",
    },
    {
        "letter": "C",
        "name": "node-c",
        "host_url": "http://localhost:8767",
        "internal_url": "http://node-c:8765",
        "container": "soak-node-c",
    },
    {
        "letter": "D",
        "name": "node-d",
        "host_url": "http://localhost:8768",
        "internal_url": "http://node-d:8765",
        "container": "soak-node-d",
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_env(path: str) -> dict[str, str]:
    env: dict[str, str] = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip()
    return env


def pad(s: str) -> str:
    return s + "=" * (-len(s) % 4)


def sign_declaration(priv_b64: str, fields: dict) -> str:
    raw = base64.urlsafe_b64decode(pad(priv_b64))
    privkey = Ed25519PrivateKey.from_private_bytes(raw)
    canonical = json.dumps(fields, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(privkey.sign(canonical)).decode().rstrip("=")


def get_well_known(host_url: str) -> dict:
    r = requests.get(f"{host_url}/.well-known/stigmem", timeout=10)
    r.raise_for_status()
    return r.json()


def create_federate_key(container: str) -> str:
    """Create a federate API key on a node via docker exec."""
    result = subprocess.run(
        [
            "docker",
            "exec",
            container,
            "python",
            "-c",
            (
                "from stigmem_node.auth import create_api_key; "
                "print(create_api_key('soak:admin', ['read','write','federate']))"
            ),
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    return result.stdout.strip()


def wait_healthy(host_url: str, name: str, retries: int = 30, delay: float = 2.0) -> None:
    last_error: requests.RequestException | None = None
    for i in range(retries):
        try:
            r = requests.get(f"{host_url}/healthz", timeout=5)
            if r.status_code == 200:
                print(f"  {name} healthy")
                return
        except requests.RequestException as exc:
            last_error = exc
        print(f"  {name} not ready, retry {i + 1}/{retries}...")
        time.sleep(delay)
    if last_error is not None:
        print(f"  {name} last health check error: {last_error}", file=sys.stderr)
    raise RuntimeError(f"{name} did not become healthy after {retries} retries")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Register full-mesh federation peers for soak test"
    )
    parser.add_argument("--env", default="soak/.env", help="Path to soak/.env file with keypairs")
    args = parser.parse_args()

    env = load_env(args.env)

    print("=== Phase 1: Waiting for all nodes to be healthy ===")
    for node in NODES:
        wait_healthy(node["host_url"], node["name"])

    print("\n=== Phase 2: Creating federate API keys ===")
    federate_keys: dict[str, str] = {}
    for node in NODES:
        key = create_federate_key(node["container"])
        federate_keys[node["name"]] = key
        print(f"  {node['name']}: key created")

    print("\n=== Phase 3: Fetching node identities ===")
    node_info: dict[str, dict] = {}
    for node in NODES:
        wk = get_well_known(node["host_url"])
        node_info[node["name"]] = {
            "node_id": wk["node_id"],
            "federation_pubkey": wk["federation_pubkey"],
            "internal_url": node["internal_url"],
        }
        print(f"  {node['name']}: node_id={wk['node_id'][:40]}...")

    print("\n=== Phase 4: Registering full-mesh peers (12 registrations) ===")
    success = 0
    skipped = 0
    failed = 0

    for registrar in NODES:
        r_name = registrar["name"]
        r_key = federate_keys[r_name]

        for peer in NODES:
            if peer["name"] == r_name:
                continue

            p_name = peer["name"]
            p_letter = peer["letter"]
            p_info = node_info[p_name]
            p_priv = env[f"NODE_{p_letter}_PRIVKEY"]

            signed_at = datetime.now(UTC).isoformat()
            allowed_scopes = ["public", "company"]

            signed_fields = {
                "allowed_scopes": sorted(allowed_scopes),
                "federation_pubkey": p_info["federation_pubkey"],
                "node_id": p_info["node_id"],
                "node_url": p_info["internal_url"],
                "signed_at": signed_at,
            }
            declaration_sig = sign_declaration(p_priv, signed_fields)

            payload = {
                "node_url": p_info["internal_url"],
                "node_id": p_info["node_id"],
                "federation_pubkey": p_info["federation_pubkey"],
                "allowed_scopes": sorted(allowed_scopes),
                "declaration_sig": declaration_sig,
                "signed_at": signed_at,
            }

            try:
                resp = requests.post(
                    f"{registrar['host_url']}/v1/federation/peers",
                    json=payload,
                    headers={"Authorization": f"Bearer {r_key}"},
                    timeout=15,
                )
                if resp.status_code == 201:
                    data = resp.json()
                    if data["status"] == "active":
                        print(f"  {r_name} ← {p_name}: active (peer_id={data['peer_id'][:8]}...)")
                        success += 1
                    else:
                        print(
                            f"  {r_name} ← {p_name}: WARNING status={data['status']}",
                            file=sys.stderr,
                        )
                        failed += 1
                elif resp.status_code == 409:
                    print(f"  {r_name} ← {p_name}: already registered (skip)")
                    skipped += 1
                else:
                    print(
                        f"  {r_name} ← {p_name}: FAILED {resp.status_code} {resp.text[:120]}",
                        file=sys.stderr,
                    )
                    failed += 1
            except Exception as exc:
                print(f"  {r_name} ← {p_name}: ERROR {exc}", file=sys.stderr)
                failed += 1

    print(f"\nRegistration complete: {success} active, {skipped} skipped, {failed} failed")
    if failed:
        print(
            "Some registrations failed — check container logs and verify well-known endpoints",
            file=sys.stderr,
        )
        sys.exit(1)

    print("\nFull-mesh federation ready. Pull replication will begin on the next 10s interval.")

    print("\n=== Saving federate keys for seed/metrics scripts ===")
    keys_out: dict[str, str] = {}
    for node in NODES:
        keys_out[node["name"]] = federate_keys[node["name"]]
    with open("soak/federate_keys.json", "w") as f:
        json.dump(keys_out, f, indent=2)
    print("  Wrote soak/federate_keys.json")


if __name__ == "__main__":
    main()
