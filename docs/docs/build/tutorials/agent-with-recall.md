---
id: agent-with-recall
title: "Tutorial: Agent with Recall"
sidebar_label: Agent with Recall
description: Build a token-efficient agent that uses the recall endpoint to surface relevant memories per turn rather than preloading the full fact store.
---

# Tutorial: Agent with Recall

**Audience:** Agent developers integrating Stigmem as a memory substrate.
**Spec references:** §20.3 Recall API, §20.4 Memory Cards, §20.5 Subscriptions.
**Time:** ~30 minutes on a laptop with Python 3.11+ and Ollama installed.

---

This tutorial walks through building a small but complete Stigmem-backed agent that:

1. Stores project facts in a Stigmem node.
2. Calls `recall` at each turn to surface relevant memories within a token budget — instead of preloading the entire fact store.
3. Retrieves an entity memory card to bootstrap context when a known entity is involved.
4. Registers a subscription so the agent is notified when a fact it cares about changes.
5. Inspects the recall audit log to debug "why was this returned?"

By the end you will have a working pattern you can adapt for any agent framework.

---

## Prerequisites

- Python 3.11+
- [Ollama](https://ollama.com) running locally (for the embedding model)
- `pip install 'stigmem-node[embed]' stigmem httpx`

Pull the embedding model once:

```bash
ollama pull nomic-embed-text
```

---

## Step 1 — Start the node with embeddings enabled

Create a working directory and start the Stigmem reference node with vector embeddings turned on:

```bash
mkdir ~/stigmem-recall-demo && cd ~/stigmem-recall-demo

STIGMEM_EMBED_ENABLED=true \
STIGMEM_EMBED_MODEL_PROVIDER=local \
STIGMEM_EMBED_MODEL_ID=nomic-embed-text-v1.5 \
stigmem start
```

The node starts on `http://localhost:8765`. Confirm it is running:

```bash
curl -s http://localhost:8765/healthz
# {"status":"ok","version":"1.1.x"}
```

:::tip No Ollama?
If you do not have Ollama, use the stub provider for this tutorial — recall will use only lexical scoring since no vectors are stored:

```bash
STIGMEM_EMBED_ENABLED=true \
STIGMEM_EMBED_MODEL_PROVIDER=stub \
stigmem start
```
:::

---

## Step 2 — Seed the fact store

Write a small corpus of facts about a fictional project. In production your agent would write facts at runtime; for this tutorial we seed them directly.

```python
# seed_facts.py
import httpx

BASE = "http://localhost:8765"
HEADERS = {"Content-Type": "application/json"}

facts = [
    # Project status
    {"entity": "project:recall-demo", "relation": "memory:status", "value": {"type": "string", "v": "in progress"}, "scope": "local", "confidence": 1.0},
    {"entity": "project:recall-demo", "relation": "memory:owner", "value": {"type": "string", "v": "alice"}, "scope": "local", "confidence": 1.0},
    {"entity": "project:recall-demo", "relation": "memory:phase", "value": {"type": "string", "v": "implementation"}, "scope": "local", "confidence": 1.0},
    # Blockers
    {"entity": "project:recall-demo", "relation": "memory:blocker", "value": {"type": "text", "v": "Embedding reindex must complete before the recall endpoint goes live."}, "scope": "local", "confidence": 0.9},
    {"entity": "project:recall-demo", "relation": "memory:blocker", "value": {"type": "text", "v": "OpenAI provider config needs a secrets-manager integration."}, "scope": "local", "confidence": 0.8},
    # Team
    {"entity": "user:alice", "relation": "memory:role", "value": {"type": "string", "v": "lead engineer"}, "scope": "local", "confidence": 1.0},
    {"entity": "user:alice", "relation": "memory:project", "value": {"type": "ref", "v": "project:recall-demo"}, "scope": "local", "confidence": 1.0},
    {"entity": "user:bob", "relation": "memory:role", "value": {"type": "string", "v": "reviewer"}, "scope": "local", "confidence": 1.0},
    {"entity": "user:bob", "relation": "memory:project", "value": {"type": "ref", "v": "project:recall-demo"}, "scope": "local", "confidence": 1.0},
    # Decisions
    {"entity": "decision:embed-model", "relation": "memory:choice", "value": {"type": "string", "v": "nomic-embed-text-v1.5"}, "scope": "local", "confidence": 1.0},
    {"entity": "decision:embed-model", "relation": "memory:rationale", "value": {"type": "text", "v": "Apache-2.0 license, runs offline, 768-dim sufficient for this corpus size."}, "scope": "local", "confidence": 1.0},
    {"entity": "decision:embed-model", "relation": "memory:made_by", "value": {"type": "ref", "v": "user:alice"}, "scope": "local", "confidence": 1.0},
]

for fact in facts:
    resp = httpx.post(f"{BASE}/v1/facts", headers=HEADERS, json=fact)
    resp.raise_for_status()
    print(f"✓ {fact['entity']}  {fact['relation']}")

print(f"\n{len(facts)} facts written.")
```

Run it:

```bash
python seed_facts.py
```

---

## Step 3 — Call `recall` from the agent

The agent receives a user question and calls `recall` to surface relevant context before answering. This is the core pattern: **recall → pack context → respond**.

```python
# agent.py
from stigmem import StigmemClient

client = StigmemClient(base_url="http://localhost:8765")


def agent_turn(user_message: str, token_budget: int = 2000) -> str:
    """Simulate one agent turn: recall relevant memory, then respond."""

    # 1. Recall: fetch the most relevant facts for this user message
    result = client.recall(
        query=user_message,
        token_budget=token_budget,
        depth=1,   # expand one hop via graph edges
        scope="local",
    )

    # 2. Build a context block from the packed facts
    context_lines = []
    if result.memory_card:
        context_lines.append(f"## Entity summary\n{result.memory_card.value}\n")

    context_lines.append("## Relevant facts")
    for fact in result.results:
        val = fact.value.get("v", "")
        context_lines.append(
            f"- [{fact.entity}] {fact.relation}: {val}  "
            f"(score={fact.score:.2f}, trust={fact.source_trust:.2f})"
        )

    if result.truncated:
        context_lines.append(
            f"\n_Note: response truncated at {result.token_budget_used} tokens. "
            "Raise token_budget or narrow the query for more._"
        )

    context_block = "\n".join(context_lines)

    # 3. Compose the prompt (in production, pass to an LLM)
    prompt = f"""You are a project assistant. Answer using only the facts below.

{context_block}

User: {user_message}
Assistant:"""

    # For this tutorial, return the context block so we can inspect it.
    return prompt


if __name__ == "__main__":
    questions = [
        "What are the current blockers on the recall demo project?",
        "Who owns the project and what phase is it in?",
        "Why did the team choose nomic-embed-text-v1.5?",
    ]

    for q in questions:
        print(f"\n{'='*60}")
        print(f"Q: {q}")
        print("-"*60)
        print(agent_turn(q))
```

Run it:

```bash
python agent.py
```

You will see the recall pipeline surface the relevant facts for each question — different facts for blockers vs. ownership vs. model rationale — all within the token budget.

---

## Step 4 — Entity-centric recall with memory cards

When the agent is reasoning about a specific entity, use the `entity` parameter. The node returns the **memory card** first — a pre-synthesized summary — then ranked supporting facts. This gives the agent a compact entity overview before it sees individual facts.

```python
# entity_recall.py
from stigmem import StigmemClient

client = StigmemClient(base_url="http://localhost:8765")

# Entity-centric recall: memory card first, then supporting facts
result = client.recall(
    query="current status and blockers",
    entity="project:recall-demo",
    token_budget=3000,
    depth=1,
)

print("=== Memory Card ===")
if result.memory_card:
    print(result.memory_card.value)
    if result.memory_card.card_stale:
        print("(card is stale — refresh in progress)")
else:
    print("(no card yet — the node materializes it asynchronously on first access)")

print("\n=== Supporting Facts ===")
for fact in result.results:
    print(f"{fact.entity}  {fact.relation}  {fact.value.get('v', '')}")
```

The memory card is refreshed automatically when facts change. Use `force_refresh=True` in the `recall` call to block until a fresh card is ready (adds latency; use only when freshness matters).

---

## Step 5 — Subscribe to changes on a watched entity

Instead of polling for new facts, register a subscription so the node pushes a notification when the project entity changes.

```python
# subscribe.py
import httpx

BASE = "http://localhost:8765"
HEADERS = {"Content-Type": "application/json"}

# Register a webhook subscription on the project entity
resp = httpx.post(
    f"{BASE}/v1/subscriptions",
    headers=HEADERS,
    json={
        "target": "project:recall-demo",
        "target_type": "entity",
        "on_change": "webhook",
        "delivery_address": "http://localhost:9000/hook",   # your agent's webhook
        "idempotency_key": "agent-recall-demo-watcher-v1",
    },
)
resp.raise_for_status()
sub = resp.json()
print(f"Subscription created: {sub['id']}")
print(f"Target:              {sub['target']} ({sub['target_kind']})")
print(f"Delivery mode:       {sub['on_change']}")
print(f"Circuit open:        {sub['circuit_open']}")
```

When a new fact about `project:recall-demo` is asserted, the node posts a delivery event to your webhook. The event includes `event_type` (`fact_asserted` | `fact_retracted` | `conflict_opened` | `conflict_resolved`), the `fact_id`, and the `hlc` tick.

**What to do on receipt:** trigger a new `recall` call with the relevant query. The push event is a wake signal — not the new context itself.

:::tip Wake mode
For agents running inside a process that can read the node's stderr, use `"on_change": "wake"` instead of `"webhook"`. The node writes a JSON object to stderr on each delivery — no webhook server required. This is the low-ceremony option for local or embedded deployments. See the [Subscriptions guide](/docs/guides/subscriptions) for the wake payload shape.
:::

---

## Step 6 — Inspect the recall audit log

When an agent returns unexpected results, the first diagnostic step is checking what `recall` actually returned and why each fact scored the way it did.

```python
# audit_recall.py
import httpx
import json

BASE = "http://localhost:8765"
HEADERS = {"Authorization": "Bearer <api-key>", "Content-Type": "application/json"}

resp = httpx.post(
    f"{BASE}/v1/recall",
    headers=HEADERS,
    json={
        "query": "current blockers",
        "token_budget": 2000,
        "depth": 1,
        "weights": {"lexical": 0.30, "vector": 0.50, "graph": 0.20},
    },
)
resp.raise_for_status()
data = resp.json()

print(f"Truncated:        {data['truncated']}")
print(f"Tokens used:      {data['token_budget_used']}")
print(f"Facts returned:   {len(data['results'])}")
print()

for i, fact in enumerate(data["results"]):
    print(f"[{i+1}] score={fact['score']:.3f}  trust={fact['source_trust']:.2f}")
    print(f"    entity:   {fact['entity']}")
    print(f"    relation: {fact['relation']}")
    val = fact["value"].get("v", "")
    print(f"    value:    {val[:80]}")
    if fact.get("contradicted"):
        print("    ⚠ contradicted")
    print()
```

Each result includes:
- `score` — the fused salience score after MMR packing
- `source_trust` — the trust multiplier from the writing agent's identity (§19)
- `contradicted` — whether the fact has an unresolved contradiction with another fact
- `derived_from` — fact hashes this fact was derived from (provenance chain)

**Debugging tips:**

| Symptom | Check |
|---|---|
| Expected fact missing | Is `truncated: true`? Raise `token_budget` or add an `entity` filter |
| Wrong entity dominating | Lower `weights.graph` — graph expansion may be over-pulling related entities |
| Semantically related facts not surfaced | Is `STIGMEM_EMBED_ENABLED=true`? Check `weights.vector` is non-zero |
| Old facts outscoring new ones | Add `min_confidence` filter; check if decay has not yet run on stale facts |
| Result seems from wrong scope | Confirm the `scope` parameter matches where facts were written |

---

## Step 7 — Tune the token budget

Token budget sizing is the most common tuning lever. The right budget depends on:

- **Model context limit** — leave headroom for system prompt + conversation history
- **Average fact size** — a project status fact is 10–20 tokens; a long rationale text can be 200+
- **Recall result diversity** — with MMR at the default `lambda_mmr=0.7`, a 2 000-token budget typically returns 15–40 facts on a moderate fact store

Quick sizing check:

```python
result = client.recall(query="project status", token_budget=10_000)  # unconstrained
print(f"Full recall would use {result.token_budget_used} tokens across {len(result.results)} facts")
```

Set your production budget to 20–40% of the full recall size — this forces MMR to make meaningful diversity tradeoffs. For a multi-turn agent, a budget of 1 500–3 000 tokens per turn is a reasonable starting point.

---

## What you built

A Stigmem-backed agent that:

- Calls `recall` per turn instead of preloading the full fact store — token costs scale with the query, not the corpus.
- Uses entity memory cards for entity-centric reasoning — one fast read, then supporting facts.
- Receives push notifications via subscriptions — no polling loops.
- Exposes the score breakdown for debugging — understand why a fact was returned.

This pattern is the foundation for the **lazy instruction discovery** approach (coming in the next phase): agent instructions are stored as facts and loaded on demand via `recall`, so agents pay context costs only for the instructions relevant to the current task.

---

## Next steps

- [Recall guide](/docs/guides/recall) — weight tuning, MMR, full parameter reference
- [Embeddings guide](/docs/guides/embeddings) — model selection, reindexing, mixed-model safety
- [Subscriptions guide](/docs/guides/subscriptions) — webhook retries, circuit breaker, replay window
- [Memory Gardens guide](/docs/guides/memory-gardens) — multi-tenant scoping and recall across gardens
- [Querying facts guide](/docs/guides/querying-facts) — structured predicate queries when `recall` is overkill
