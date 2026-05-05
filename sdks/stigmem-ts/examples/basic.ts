/**
 * stigmem-ts basic example — assert, recall, and subscribe.
 *
 * Run with tsx (after `pnpm build` from the SDK root):
 *   STIGMEM_URL=http://localhost:8000 STIGMEM_API_KEY=sk-... npx tsx examples/basic.ts
 */

import { StigmemClient, sv, tv, nv } from "../src/index.js";

const STIGMEM_URL = process.env["STIGMEM_URL"] ?? "http://localhost:8000";
const STIGMEM_API_KEY = process.env["STIGMEM_API_KEY"];

const ENTITY = "user:alice";
const SOURCE = "agent:example";

async function main() {
  const client = new StigmemClient({ url: STIGMEM_URL, apiKey: STIGMEM_API_KEY });

  // ── Node info ─────────────────────────────────────────────────────────────
  const info = await client.nodeInfo();
  console.log(`Connected to node ${info.node_id} (spec ${info.version})`);

  // ── Assert facts ──────────────────────────────────────────────────────────
  const roleFact = await client.assertFact(ENTITY, "memory:role", sv("engineer"), SOURCE, {
    scope: "local",
  });
  console.log(`Asserted: ${roleFact.id}  ${ENTITY} memory:role = "engineer"`);

  const noteFact = await client.assertFact(
    ENTITY,
    "memory:note",
    tv("Alice joined the platform team in Q1 2026 and focuses on distributed systems."),
    SOURCE,
    { scope: "local" },
  );
  console.log(`Asserted: ${noteFact.id}  ${ENTITY} memory:note (text)`);

  const levelFact = await client.assertFact(ENTITY, "memory:level", nv(4), SOURCE, { scope: "local" });
  console.log(`Asserted: ${levelFact.id}  ${ENTITY} memory:level = 4`);

  // ── Recall ────────────────────────────────────────────────────────────────
  console.log("\n── Hybrid recall ──");
  const recall = await client.recall("Alice's background and expertise", {
    scope: "local",
    token_budget: 500,
  });
  console.log(`Recall id: ${recall.recall_id}  tokens used: ${recall.tokens_used}/${recall.token_budget}`);
  for (const sf of recall.facts) {
    const val = sf.fact.value.type !== "null" ? String((sf.fact.value as { v: unknown }).v) : "null";
    console.log(`  [${sf.score.toFixed(3)}] ${sf.fact.relation}: ${val}`);
  }

  // ── Memory card ───────────────────────────────────────────────────────────
  console.log("\n── Memory card ──");
  try {
    const card = await client.getCard(ENTITY, { scope: "local" });
    console.log(`Summary for ${card.entity_uri}:\n  ${card.summary}`);
    console.log(`  avg_confidence=${card.avg_confidence.toFixed(3)}  stale=${card.is_stale}`);
  } catch (err) {
    // getCard 404s until the node has built the card index for this entity
    console.log(`  (card not yet available — ${String(err)})`);
  }

  // ── Subscribe ─────────────────────────────────────────────────────────────
  console.log("\n── Subscribe (3 ticks, 1s interval) ──");
  const ac = new AbortController();
  setTimeout(() => ac.abort(), 5_000);

  let ticks = 0;
  try {
    for await (const batch of client.subscribeScope("local", {
      intervalMs: 1_000,
      signal: ac.signal,
    })) {
      console.log(`  tick ${++ticks}: ${batch.length} fact(s)`);
      if (ticks >= 3) ac.abort();
    }
  } catch {
    // aborted — expected
  }

  console.log("\nDone.");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
