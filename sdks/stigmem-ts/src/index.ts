/**
 * stigmem-ts — TypeScript client SDK for Stigmem (spec v0.4/v0.5).
 *
 * @example
 * ```ts
 * import { StigmemClient, sv, tv } from "stigmem-ts";
 *
 * const client = new StigmemClient({ url: "http://localhost:8765", apiKey: "sk-..." });
 * const fact = await client.assertFact("user:alice", "memory:role", sv("CEO"), "agent:cto");
 * const page = await client.query({ entity: "user:alice" });
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
  NodeInfo,
  NullValue,
  NumberValue,
  Peer,
  PeerPage,
  PeerStatus,
  QueryOptions,
  RefValue,
  ResolveOptions,
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
