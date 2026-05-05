/**
 * stigmem-ts — TypeScript client SDK for Stigmem (spec v1.0).
 *
 * @example
 * ```ts
 * import { StigmemClient, sv, tv } from "stigmem-ts";
 *
 * const client = new StigmemClient({ url: "http://localhost:8765", apiKey: "sk-..." });
 * const fact = await client.assertFact("user:alice", "memory:role", sv("CEO"), "agent:cto");
 * const result = await client.recall("Alice's current role", { token_budget: 500 });
 * const card  = await client.getCard("user:alice");
 * ```
 */

export {
  StigmemClient,
  StigmemError,
  StigmemHTTPError,
  StigmemAuthError,
  StigmemNotFoundError,
  StigmemConflictError,
} from "./client.js";

export type {
  AssertOptions,
  BooleanValue,
  CardOptions,
  Conflict,
  ConflictListOptions,
  ConflictPage,
  ConflictResolution,
  ConflictStatus,
  DatetimeValue,
  Fact,
  FactPage,
  FactScope,
  FactValue,
  FederationEndpoints,
  LintCheck,
  LintFinding,
  LintOptions,
  LintResult,
  LintSeverity,
  MemoryCard,
  NodeInfo,
  NullValue,
  NumberValue,
  Peer,
  PeerPage,
  PeerStatus,
  QueryOptions,
  RecallOptions,
  RecallResponse,
  RecallWeights,
  RefValue,
  ResolveOptions,
  ScoreBreakdown,
  ScoredFact,
  StringValue,
  SubscribeOptions,
  TextValue,
} from "./types.js";

export {
  sv,
  tv,
  nv,
  bv,
  dtv,
  rv,
  nullv,
} from "./types.js";
