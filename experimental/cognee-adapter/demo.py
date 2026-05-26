"""Stigmem ↔ Cognee demo.

Asserts a set of related facts via stigmem, pushes them into Cognee's knowledge
graph, then queries the graph to verify the relationships are discoverable.

Prerequisites::

    pip install stigmem-py cognee

Environment variables::

    STIGMEM_URL            stigmem node URL  (default: http://localhost:8765)
    STIGMEM_API_KEY        optional bearer key
    STIGMEM_SOURCE_ENTITY  asserting agent   (default: agent:cognee-demo)

    COGNEE_LLM_PROVIDER    LLM backend       (default: openai)
    COGNEE_LLM_MODEL       model name        (default: gpt-4o-mini)
    COGNEE_LLM_API_KEY     LLM API key
    COGNEE_VECTOR_DB_PATH  LanceDB path      (default: .cognee_db)
    COGNEE_STIGMEM_DATASET dataset name      (default: stigmem)

Run::

    python demo.py

"""

from __future__ import annotations

import asyncio
import os
import sys

# ---------------------------------------------------------------------------
# Resolve paths so the demo works whether run from the adapter directory or
# the repo root.
# ---------------------------------------------------------------------------
from pathlib import Path

_HERE = Path(__file__).parent
_REPO_ROOT = _HERE.parent.parent.parent
sys.path.insert(0, str(_HERE / "src"))
sys.path.insert(0, str(_REPO_ROOT / "sdks" / "stigmem-py" / "src"))

from stigmem_plugin_cognee.adapter import StigmemCogneeAdapter  # noqa: E402
from stigmem import StigmemClient  # noqa: E402

# ---------------------------------------------------------------------------
# Demo facts — a small knowledge graph about the Loom project
# ---------------------------------------------------------------------------

DEMO_FACTS = [
    {
        "entity": "project:loom",
        "relation": "roadmap:phase",
        "value": {"type": "string", "v": "phase-6"},
        "source": "agent:cognee-demo",
        "scope": "company",
        "confidence": 1.0,
    },
    {
        "entity": "project:loom",
        "relation": "roadmap:focus",
        "value": {"type": "string", "v": "federation-protocol"},
        "source": "agent:cognee-demo",
        "scope": "company",
        "confidence": 1.0,
    },
    {
        "entity": "agent:distsyseng",
        "relation": "team:owns",
        "value": {"type": "ref", "v": "project:loom"},
        "source": "agent:cognee-demo",
        "scope": "company",
        "confidence": 1.0,
    },
    {
        "entity": "agent:distsyseng",
        "relation": "memory:role",
        "value": {"type": "string", "v": "distributed-systems-engineer"},
        "source": "agent:cognee-demo",
        "scope": "company",
        "confidence": 1.0,
    },
    {
        "entity": "protocol:loom-federation",
        "relation": "spec:status",
        "value": {"type": "string", "v": "rfc-draft"},
        "source": "agent:cognee-demo",
        "scope": "company",
        "confidence": 1.0,
    },
    {
        "entity": "protocol:loom-federation",
        "relation": "spec:consistency-model",
        "value": {"type": "string", "v": "PACELC-AP-eventual"},
        "source": "agent:cognee-demo",
        "scope": "company",
        "confidence": 1.0,
    },
]

DEMO_QUERIES = [
    ("company", "What phase is the Loom project in?"),
    ("company", "Who owns the Loom project?"),
    ("company", "What is the consistency model of the Loom federation protocol?"),
]


async def run_demo() -> None:
    stigmem_url = os.environ.get("STIGMEM_URL", "http://localhost:8765")
    stigmem_key = os.environ.get("STIGMEM_API_KEY")
    source = os.environ.get("STIGMEM_SOURCE_ENTITY", "agent:cognee-demo")

    print("=" * 60)
    print("Stigmem ↔ Cognee federation demo")
    print("=" * 60)

    # ------------------------------------------------------------------
    # 1. Assert facts in stigmem
    # ------------------------------------------------------------------
    print(f"\n[1/3] Asserting {len(DEMO_FACTS)} facts in stigmem at {stigmem_url}")
    client = StigmemClient(url=stigmem_url, api_key=stigmem_key)
    asserted = []
    for raw in DEMO_FACTS:
        try:
            fact = client.assert_fact(
                entity=raw["entity"],
                relation=raw["relation"],
                value=raw["value"],
                source=source,
                confidence=raw.get("confidence", 1.0),
                scope=raw.get("scope", "company"),
            )
            asserted.append(fact.model_dump())
            print(f"  ✓  {raw['entity']}  →  {raw['relation']}  =  {raw['value'].get('v', '')}")
        except Exception as exc:
            print(f"  ✗  {raw['entity']} / {raw['relation']}: {exc}")

    if not asserted:
        print("\n  No facts asserted — check STIGMEM_URL / STIGMEM_API_KEY.")
        return

    # ------------------------------------------------------------------
    # 2. Push asserted facts into Cognee
    # ------------------------------------------------------------------
    print(f"\n[2/3] Pushing {len(asserted)} facts into Cognee (batch cognify)")
    bridge = StigmemCogneeAdapter.from_env()
    await bridge.batch_assert_to_cognee_async(asserted)
    print("  ✓  Cognee graph updated")

    # ------------------------------------------------------------------
    # 3. Query Cognee graph and verify facts are discoverable
    # ------------------------------------------------------------------
    print(f"\n[3/3] Querying Cognee graph — {len(DEMO_QUERIES)} queries")
    for scope, query in DEMO_QUERIES:
        print(f"\n  Query: {query!r}")
        results = await bridge.query_from_cognee_async(scope=scope, query=query)
        if results:
            for rec in results:
                print(
                    f"    entity={rec['entity']!r}  relation={rec['relation']!r}  value={rec['value']}"
                )
        else:
            print("    (no results)")

    print("\n" + "=" * 60)
    print("Demo complete.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_demo())
