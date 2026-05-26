"""Demo: stigmem → Zep federation.

Asserts a fact via the stigmem REST API, mirrors it into Zep memory via
StigmemZepAdapter, then reads back the session's episodic facts from Zep.

Requirements:
    pip install zep-cloud httpx

Environment:
    STIGMEM_URL=http://localhost:8765        # stigmem node base URL
    STIGMEM_API_KEY=sk-...                   # optional; required if auth enabled
    ZEP_API_KEY=your-key                     # required for Zep Cloud
    ZEP_BASE_URL=http://localhost:8000       # required for self-hosted Zep
    SESSION_ID=demo-session-001              # optional; auto-generated if unset

Usage:
    cd stigmem
    STIGMEM_URL=http://localhost:8765 \\
    ZEP_BASE_URL=http://localhost:8000 \\
    SESSION_ID=demo-001 \\
    uv run python experimental/zep-adapter/demo.py
"""

import os
import uuid

import httpx
from stigmem_plugin_zep import StigmemZepAdapter


def main() -> None:
    stigmem_url = os.environ.get("STIGMEM_URL", "http://localhost:8765")
    stigmem_key = os.environ.get("STIGMEM_API_KEY")
    session_id = os.environ.get("SESSION_ID", f"demo-{uuid.uuid4().hex[:8]}")

    print(f"stigmem node : {stigmem_url}")
    print(f"Zep session  : {session_id}")
    print()

    # 1. Assert a fact via the stigmem REST API
    print("Step 1 — assert fact in stigmem...")
    headers: dict[str, str] = {"Content-Type": "application/json"}
    if stigmem_key:
        headers["Authorization"] = f"Bearer {stigmem_key}"

    resp = httpx.post(
        f"{stigmem_url}/v1/facts",
        headers=headers,
        json={
            "entity": "user:demo-alice",
            "relation": "memory:role",
            "value": {"type": "string", "v": "principal-engineer"},
            "source": "agent:stigmem-zep-demo",
            "scope": "company",
        },
    )
    resp.raise_for_status()
    fact = resp.json()
    print(f"  fact id : {fact['id']}")
    print(f"  content : {fact['entity']} {fact['relation']} = {fact['value']['v']}")
    print()

    # 2. Mirror the fact into Zep
    print("Step 2 — mirror fact into Zep...")
    adapter = StigmemZepAdapter.from_env()
    result = adapter.assert_to_zep(fact, session_id)
    print(f"  written : {result['content']}")
    print()

    # 3. Read back from Zep
    print("Step 3 — query Zep for session facts...")
    records = adapter.query_from_zep("company", session_id)
    if records:
        for r in records:
            print(f"  [{r['relation']}] {r['value']['v']}")
    else:
        print("  (no facts extracted yet — Zep extracts asynchronously; re-run in a few seconds)")
    print()

    # 4. Verdict
    found = any("principal-engineer" in r["value"]["v"] for r in records)
    if found:
        print("OK — stigmem fact is visible in Zep memory.")
    else:
        print("NOTE — fact written to Zep; run again after a moment to see it extracted.")


if __name__ == "__main__":
    main()
