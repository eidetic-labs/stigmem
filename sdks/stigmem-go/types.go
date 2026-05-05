// Package stigmem is a Go client for the stigmem memory-node HTTP API (spec v0.4+).
//
// Construct a client with New, then call methods with a context:
//
//	c := stigmem.New("http://localhost:8765", stigmem.WithAPIKey("sk-..."))
//	fact, err := c.AssertFact(ctx, "user:alice", "memory:role", stigmem.StringValue("CEO"), "my-agent")
package stigmem

// FactScope is the visibility scope of a fact.
type FactScope string

const (
	ScopeLocal   FactScope = "local"
	ScopeTeam    FactScope = "team"
	ScopeCompany FactScope = "company"
	ScopePublic  FactScope = "public"
)

// FactValue is a tagged-union value. Use the constructor functions.
type FactValue struct {
	Type string `json:"type"`
	V    any    `json:"v,omitempty"`
}

// StringValue constructs a short-string FactValue.
func StringValue(v string) FactValue { return FactValue{Type: "string", V: v} }

// TextValue constructs a long-text FactValue.
func TextValue(v string) FactValue { return FactValue{Type: "text", V: v} }

// NumberValue constructs a numeric FactValue.
func NumberValue(v float64) FactValue { return FactValue{Type: "number", V: v} }

// BooleanValue constructs a boolean FactValue.
func BooleanValue(v bool) FactValue { return FactValue{Type: "boolean", V: v} }

// DatetimeValue constructs an ISO 8601 datetime FactValue.
func DatetimeValue(v string) FactValue { return FactValue{Type: "datetime", V: v} }

// RefValue constructs a URI-reference FactValue.
func RefValue(v string) FactValue { return FactValue{Type: "ref", V: v} }

// NullValue constructs a null FactValue.
func NullValue() FactValue { return FactValue{Type: "null"} }

// Fact is an immutable asserted triple (entity, relation, value).
type Fact struct {
	ID           string    `json:"id"`
	Entity       string    `json:"entity"`
	Relation     string    `json:"relation"`
	Value        FactValue `json:"value"`
	Source       string    `json:"source"`
	Timestamp    string    `json:"timestamp"`
	HLC          string    `json:"hlc,omitempty"`
	ValidUntil   string    `json:"valid_until,omitempty"`
	Confidence   float64   `json:"confidence"`
	Scope        FactScope `json:"scope"`
	Contradicted bool      `json:"contradicted"`
	ReceivedFrom string    `json:"received_from,omitempty"`
}

// FactPage is a paginated list of facts.
type FactPage struct {
	Facts  []Fact  `json:"facts"`
	Total  int     `json:"total"`
	Cursor *string `json:"cursor,omitempty"`
}

// FederationEndpoints holds the URLs for federation API endpoints.
type FederationEndpoints struct {
	Peers string  `json:"peers"`
	Facts string  `json:"facts"`
	Push  *string `json:"push,omitempty"`
}

// NodeInfo is returned by /.well-known/stigmem.
type NodeInfo struct {
	Version             string               `json:"version"`
	NodeID              string               `json:"node_id"`
	NodeURL             string               `json:"node_url"`
	Auth                string               `json:"auth"`
	Federation          string               `json:"federation"`
	FederationPubkey    *string              `json:"federation_pubkey,omitempty"`
	FederationVersion   *string              `json:"federation_version,omitempty"`
	FederationEndpoints *FederationEndpoints `json:"federation_endpoints,omitempty"`
	Namespaces          []string             `json:"namespaces"`
	Spec                *string              `json:"spec,omitempty"`
}

// Peer represents a federated stigmem peer node.
type Peer struct {
	PeerID        string      `json:"peer_id"`
	NodeID        string      `json:"node_id"`
	NodeURL       string      `json:"node_url"`
	Status        string      `json:"status"`
	AllowedScopes []FactScope `json:"allowed_scopes"`
	EstablishedAt *string     `json:"established_at,omitempty"`
}

// PeerPage is the response envelope for the federation/peers endpoint.
type PeerPage struct {
	Peers []Peer `json:"peers"`
}

// Conflict is a detected contradiction between two facts.
type Conflict struct {
	ConflictID string  `json:"conflict_id"`
	FactA      Fact    `json:"fact_a"`
	FactB      Fact    `json:"fact_b"`
	Status     string  `json:"status"`
	ResolvedBy *string `json:"resolved_by,omitempty"`
	DetectedAt string  `json:"detected_at"`
}

// ConflictPage is a paginated list of conflicts.
type ConflictPage struct {
	Conflicts []Conflict `json:"conflicts"`
	Cursor    *string    `json:"cursor,omitempty"`
	HasMore   bool       `json:"has_more"`
}

// ConflictResolution is the response from resolving a conflict.
type ConflictResolution struct {
	ResolutionFactID string `json:"resolution_fact_id"`
	ConflictStatus   string `json:"conflict_status"`
}

// RecallWeights controls the relative weight of each ranking signal.
type RecallWeights struct {
	Lexical     float64 `json:"lexical"`
	Semantic    float64 `json:"semantic"`
	Graph       float64 `json:"graph"`
	SourceTrust float64 `json:"source_trust"`
	Recency     float64 `json:"recency"`
}

// DefaultRecallWeights returns the server-default signal weights.
func DefaultRecallWeights() RecallWeights {
	return RecallWeights{Lexical: 0.35, Semantic: 0.35, Graph: 0.15, SourceTrust: 0.10, Recency: 0.05}
}

// ScoreBreakdown shows per-signal contributions to a fact's recall score.
type ScoreBreakdown struct {
	Lexical       float64 `json:"lexical"`
	Semantic      float64 `json:"semantic"`
	Graph         float64 `json:"graph"`
	SourceTrust   float64 `json:"source_trust"`
	Recency       float64 `json:"recency"`
	WeightedTotal float64 `json:"weighted_total"`
}

// ScoredFact pairs a Fact with its recall score metadata.
type ScoredFact struct {
	Fact           Fact           `json:"fact"`
	Score          float64        `json:"score"`
	ScoreBreakdown ScoreBreakdown `json:"score_breakdown"`
	HopDistance    int            `json:"hop_distance"`
	TokenEstimate  int            `json:"token_estimate"`
}

// RecallResponse is returned by the /v1/recall endpoint.
type RecallResponse struct {
	RecallID    string       `json:"recall_id"`
	QueryHash   string       `json:"query_hash"`
	Facts       []ScoredFact `json:"facts"`
	TotalScored int          `json:"total_scored"`
	TokenBudget int          `json:"token_budget"`
	TokensUsed  int          `json:"tokens_used"`
	Truncated   bool         `json:"truncated"`
}

// MemoryCard is a synthesized per-entity summary (spec §20).
type MemoryCard struct {
	EntityURI         string   `json:"entity_uri"`
	Scope             string   `json:"scope"`
	Summary           string   `json:"summary"`
	FactHashes        []string `json:"fact_hashes"`
	AvgConfidence     float64  `json:"avg_confidence"`
	RefreshedAt       *string  `json:"refreshed_at,omitempty"`
	IsStale           bool     `json:"is_stale"`
	HasContradictions bool     `json:"has_contradictions"`
}
