/**
 * Stigmem TypeScript SDK — type definitions (spec v0.4/v0.5).
 */

// ---------------------------------------------------------------------------
// FactValue
// ---------------------------------------------------------------------------

export interface StringValue  { type: "string";   v: string  }
export interface TextValue    { type: "text";      v: string  }
export interface NumberValue  { type: "number";    v: number  }
export interface BooleanValue { type: "boolean";   v: boolean }
export interface DatetimeValue{ type: "datetime";  v: string  }  // ISO 8601
export interface RefValue     { type: "ref";       v: string  }  // URI
export interface NullValue    { type: "null"                  }

export type FactValue =
  | StringValue
  | TextValue
  | NumberValue
  | BooleanValue
  | DatetimeValue
  | RefValue
  | NullValue;

export type FactScope = "local" | "team" | "company" | "public";

// Value constructors
export const sv  = (v: string):  StringValue   => ({ type: "string",   v });
export const tv  = (v: string):  TextValue     => ({ type: "text",     v });
export const nv  = (v: number):  NumberValue   => ({ type: "number",   v });
export const bv  = (v: boolean): BooleanValue  => ({ type: "boolean",  v });
export const dtv = (v: string):  DatetimeValue => ({ type: "datetime", v });
export const rv  = (v: string):  RefValue      => ({ type: "ref",      v });
export const nullv = ():         NullValue     => ({ type: "null"        });

// ---------------------------------------------------------------------------
// Fact
// ---------------------------------------------------------------------------

export interface Fact {
  id:           string;
  entity:       string;
  relation:     string;
  value:        FactValue;
  source:       string;
  timestamp:    string;
  hlc?:         string;
  valid_until?: string;
  confidence:   number;
  scope:        FactScope;
  contradicted: boolean;
  received_from?: string;
}

export interface FactPage {
  facts:   Fact[];
  total:   number;
  cursor?: string;
}

// ---------------------------------------------------------------------------
// Peer / Federation
// ---------------------------------------------------------------------------

export type PeerStatus = "pending_verification" | "active" | "rejected" | "revoked";

export interface Peer {
  peer_id:        string;
  node_id:        string;
  node_url:       string;
  status:         PeerStatus;
  allowed_scopes: FactScope[];
  established_at?: string;
}

export interface PeerPage {
  peers: Peer[];
}

// ---------------------------------------------------------------------------
// Node info
// ---------------------------------------------------------------------------

export interface FederationEndpoints {
  peers: string;
  facts: string;
  push?: string;
}

export interface NodeInfo {
  version:               string;
  node_id:               string;
  node_url:              string;
  auth:                  "none" | "required";
  federation:            "disabled" | "enabled";
  federation_pubkey?:    string;
  federation_version?:   string;
  federation_endpoints?: FederationEndpoints;
  namespaces:            string[];
  spec?:                 string;
}

// ---------------------------------------------------------------------------
// Conflicts
// ---------------------------------------------------------------------------

export type ConflictStatus = "unresolved" | "resolved";

export interface Conflict {
  conflict_id:   string;
  fact_a:        Fact;
  fact_b:        Fact;
  status:        ConflictStatus;
  resolved_by?:  string;
  detected_at:   string;
}

export interface ConflictPage {
  conflicts: Conflict[];
  cursor?:   string;
  has_more:  boolean;
}

export interface ConflictResolution {
  resolution_fact_id: string;
  conflict_status:    "resolved";
}

// ---------------------------------------------------------------------------
// Request / option shapes
// ---------------------------------------------------------------------------

export interface AssertOptions {
  confidence?: number;
  scope?:      FactScope;
  valid_until?: string;
}

export interface QueryOptions {
  entity?:               string;
  relation?:             string;
  source?:               string;
  scope?:                FactScope;
  min_confidence?:       number;
  include_contradicted?: boolean;
  include_expired?:      boolean;
  cursor?:               string;
  after?:                string;
  limit?:                number;
}

export interface ResolveOptions {
  winning_fact_id?: string;
  resolution_note?: string;
  new_value?:       FactValue;
}

export interface ConflictListOptions {
  status?: ConflictStatus;
  cursor?: string;
  limit?:  number;
}

export interface SubscribeOptions {
  intervalMs?: number;
  signal?:     AbortSignal;
}

// ---------------------------------------------------------------------------
// Lint — v0.7 (spec §14)
// ---------------------------------------------------------------------------

export type LintCheck = "contradiction" | "stale" | "orphan" | "broken_ref";
export type LintSeverity = "error" | "warning" | "info";

export interface LintFinding {
  check:    LintCheck;
  severity: LintSeverity;
  entity:   string;
  relation: string | null;
  fact_ids: string[];
  detail:   string;
}

export interface LintResult {
  findings:   LintFinding[];
  checked_at: string;
  scope:      FactScope;
  checks_run: LintCheck[];
  fact_count: number;
}

export interface LintOptions {
  checks?:            LintCheck[];
  entity?:            string;
  relation?:          string;
  stale_lookahead_s?: number;
}

// ---------------------------------------------------------------------------
// Recall (Phase 9 — spec §20)
// ---------------------------------------------------------------------------

export interface RecallWeights {
  lexical?:      number;
  semantic?:     number;
  graph?:        number;
  source_trust?: number;
  recency?:      number;
}

export interface RecallOptions {
  scope?:             FactScope;
  token_budget?:      number;
  depth?:             number;
  weights?:           RecallWeights;
  min_confidence?:    number;
  include_neighbors?: boolean;
  limit?:             number;
  legacy_format?:     boolean;
}

export interface ScoreBreakdown {
  lexical:        number;
  semantic:       number;
  graph:          number;
  source_trust:   number;
  recency:        number;
  weighted_total: number;
}

export interface ScoredFact {
  fact:            Fact;
  score:           number;
  score_breakdown: ScoreBreakdown;
  hop_distance:    number;
  token_estimate:  number;
  from_card?:      boolean;
}

export interface RecallResponse {
  recall_id:    string;
  query_hash:   string;
  facts:        ScoredFact[];
  content?:      ScoredFact[];
  instructions?: ScoredFact[];
  total_scored: number;
  token_budget: number;
  tokens_used:  number;
  truncated:    boolean;
}

// ---------------------------------------------------------------------------
// Memory cards (Phase 9 — spec §20)
// ---------------------------------------------------------------------------

export interface MemoryCard {
  entity_uri:        string;
  scope:             string;
  summary:           string;
  fact_hashes:       string[];
  avg_confidence:    number;
  refreshed_at?:     string;
  is_stale:          boolean;
  has_contradictions: boolean;
}

export interface CardOptions {
  scope?:   FactScope;
  refresh?: boolean;
}
