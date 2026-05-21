# `@eidetic-labs/stigmem-ts`

TypeScript / JavaScript client SDK for **[Stigmem](https://github.com/eidetic-labs/stigmem)** — a federated knowledge fabric for AI agents that stores facts as immutable, signed assertions and replicates them across peer nodes.

> **Status: preview alpha.** No stability guarantee on the wire format or public API until `v1.0.0` GA. See [LIMITATIONS.md](https://github.com/eidetic-labs/stigmem/blob/main/LIMITATIONS.md) and the [retraction post](https://dev.to/offbyonce/walking-back-our-v10-announcement-resetting-to-v090a1-as-the-first-build-al0) for context on why we reset to `v0.9.0a1` as the first build.

## Install

```bash
npm install @eidetic-labs/stigmem-ts
# or
pnpm add @eidetic-labs/stigmem-ts
# or
yarn add @eidetic-labs/stigmem-ts
```

Provenance is attested via npm + GitHub Actions OIDC. Verify with:

```bash
npm audit signatures
```

## Quick start

```ts
import { StigmemClient, sv, tv } from "@eidetic-labs/stigmem-ts";

const client = new StigmemClient({
  url: "http://localhost:8765",
  apiKey: process.env.STIGMEM_API_KEY,
});

// Assert a fact
const fact = await client.assertFact(
  "user:alice",            // entity URI
  "memory:role",           // relation
  sv("CEO"),               // value (string)
  "agent:cto",             // source
  { session_id: "session:example" },
);

// Query facts
const page = await client.queryFacts({ entity: "user:alice", scope: "company" });
console.log(page.facts);

// Semantic recall
const recall = await client.recall("Alice's current role", { token_budget: 500 });

// Memory card (synthesized snapshot for a single entity)
const card = await client.getCard("user:alice");
```

## Value constructors

Facts carry a typed `value`. Use these helpers to build well-formed values:

| Helper | TypeScript | Wire-format type |
|---|---|---|
| `sv(s)` | `(s: string)` | `StringValue` |
| `tv(s)` | `(s: string)` | `TextValue` (longer free-form) |
| `nv(n)` | `(n: number)` | `NumberValue` |
| `bv(b)` | `(b: boolean)` | `BooleanValue` |
| `dtv(s)` | `(iso8601: string)` | `DatetimeValue` |
| `rv(uri)` | `(entityURI: string)` | `RefValue` (entity reference) |
| `nullv()` | `()` | `NullValue` |

## API surface

The full client surface covers:

- **Facts**: `assertFact`, `getFact`, `queryFacts`, `retractFact`, `verifyCid`
- **Recall**: `recall` (semantic, weighted retrieval), `getCard` (synthesized memory card per entity)
- **Conflicts**: `listConflicts`, `resolveConflict`
- **Lint**: `lint` (validate facts before assert)
- **Federation**: `listPeers`, `registerPeer`, `getNodeInfo`
- **Subscriptions**: `subscribe` (push federation, opt-in)

Full TypeScript types are exported from the main package — your editor will autocomplete and check at compile time.

## Session and provenance options

Agent integrations should pass a stable `session_id` on reads and writes so the
node can enforce same-session read/write graph isolation. Writes that summarize
facts read earlier in the same session should use `write_mode:
"summarize_with_provenance"` and carry source facts in `derived_from`.

```ts
await client.assertFact(
  "handoff:session-123",
  "intent:handoff_summary",
  tv("Summarized context for the next agent."),
  "agent:openclaw",
  {
    session_id: "session:example",
    write_mode: "summarize_with_provenance",
    derived_from: [{ fact_id: "fact-source-001" }],
  },
);
```

## Compatibility

| `stigmem-node` server | `@eidetic-labs/stigmem-ts` SDK |
|---|---|
| `0.9.0a1` (preview alpha) | `0.9.0-alpha.1` |
| `0.9.0a2` (current published alpha) | `0.9.0-alpha.2` |
| `0.9.0aN` (alpha line) | `0.9.0-alpha.N` |
| Future beta / RC / GA lines | Versioned only when those release lines are explicitly opened and published. |

The SDK and server advance together along the version line; pin compatible versions in production-leaning environments.

## npm `latest` dist-tag — what it points at

Until a stable GA line ships, `latest` tracks the **most recent published version** regardless of stability tier. Today that's `0.9.0-alpha.2`; it walks forward through the active alpha line first. Future beta, RC, and GA dist-tags are created only when those release lines are explicitly opened and published. This is a deliberate deviation from the standard "`latest` = stable" npm convention; full rationale in [LIMITATIONS.md §npm `latest` dist-tag](https://github.com/eidetic-labs/stigmem/blob/main/LIMITATIONS.md).

Stability lives in the version string itself: any version ending in `-alpha.N`, `-beta.N`, or `-rc.N` is pre-stable and carries no compatibility guarantee.

## Documentation

- **[stigmem.dev](https://stigmem.dev)** — landing page
- **[docs.stigmem.dev](https://docs.stigmem.dev)** — full docs site (Learn / Build / Operate / Secure)
- **[Repository](https://github.com/eidetic-labs/stigmem)** — source, issue tracker, contributor guide
- **[Threat model](https://github.com/eidetic-labs/stigmem/blob/main/spec/security/threat-model.md)** — STRIDE risk register; read before deploying federation across organizational boundaries
- **[LIMITATIONS.md](https://github.com/eidetic-labs/stigmem/blob/main/LIMITATIONS.md)** — adopter-facing constraints, known gaps, deployment-pattern guidance

## License

[Apache-2.0](https://github.com/eidetic-labs/stigmem/blob/main/LICENSE).
