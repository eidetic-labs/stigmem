package stigmem

import (
	"bytes"
	"context"
	"crypto/tls"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"strconv"
	"strings"
	"time"
)

const defaultTimeout = 10 * time.Second

// Client is a stigmem HTTP client. Construct with New.
type Client struct {
	baseURL string
	http    *http.Client
	apiKey  string
}

// Option configures a Client at construction time.
type Option func(*clientConfig)

type clientConfig struct {
	timeout    time.Duration
	tlsCfg     *tls.Config
	apiKey     string
	httpClient *http.Client
}

// WithAPIKey sets the bearer capability token sent on every request.
func WithAPIKey(key string) Option {
	return func(c *clientConfig) { c.apiKey = key }
}

// WithTimeout sets the per-request HTTP timeout (default 10s).
func WithTimeout(d time.Duration) Option {
	return func(c *clientConfig) { c.timeout = d }
}

// WithTLSConfig configures mTLS or custom TLS settings on the transport.
func WithTLSConfig(tlsCfg *tls.Config) Option {
	return func(c *clientConfig) { c.tlsCfg = tlsCfg }
}

// WithHTTPClient replaces the underlying *http.Client entirely.
func WithHTTPClient(h *http.Client) Option {
	return func(c *clientConfig) { c.httpClient = h }
}

// New constructs a Client targeting the given stigmem node URL.
func New(nodeURL string, opts ...Option) *Client {
	cfg := &clientConfig{timeout: defaultTimeout}
	for _, o := range opts {
		o(cfg)
	}

	httpClient := cfg.httpClient
	if httpClient == nil {
		var transport http.RoundTripper = http.DefaultTransport
		if cfg.tlsCfg != nil {
			transport = &http.Transport{TLSClientConfig: cfg.tlsCfg}
		}
		httpClient = &http.Client{Timeout: cfg.timeout, Transport: transport}
	}

	return &Client{
		baseURL: strings.TrimRight(nodeURL, "/"),
		http:    httpClient,
		apiKey:  cfg.apiKey,
	}
}

// doJSON executes an HTTP request and JSON-decodes the response body into out (when non-nil).
func (c *Client) doJSON(ctx context.Context, method, path string, body, out any) error {
	var bodyReader io.Reader
	if body != nil {
		b, err := json.Marshal(body)
		if err != nil {
			return fmt.Errorf("stigmem: marshal: %w", err)
		}
		bodyReader = bytes.NewReader(b)
	}

	req, err := http.NewRequestWithContext(ctx, method, c.baseURL+path, bodyReader)
	if err != nil {
		return fmt.Errorf("stigmem: new request: %w", err)
	}
	req.Header.Set("Accept", "application/json")
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	if c.apiKey != "" {
		req.Header.Set("Authorization", "Bearer "+c.apiKey)
	}

	resp, err := c.http.Do(req)
	if err != nil {
		return fmt.Errorf("stigmem: request: %w", err)
	}
	defer resp.Body.Close()

	raw, err := io.ReadAll(resp.Body)
	if err != nil {
		return fmt.Errorf("stigmem: read body: %w", err)
	}

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		var errEnv struct {
			Detail string `json:"detail"`
		}
		_ = json.Unmarshal(raw, &errEnv)
		detail := errEnv.Detail
		if detail == "" {
			detail = strings.TrimSpace(string(raw))
		}
		return newHTTPError(resp.StatusCode, detail)
	}

	if out != nil {
		if err := json.Unmarshal(raw, out); err != nil {
			return fmt.Errorf("stigmem: decode: %w", err)
		}
	}
	return nil
}

// doGet executes a GET with optional query parameters.
func (c *Client) doGet(ctx context.Context, path string, params url.Values, out any) error {
	fullPath := path
	if enc := params.Encode(); enc != "" {
		fullPath += "?" + enc
	}
	return c.doJSON(ctx, http.MethodGet, fullPath, nil, out)
}

// ---------------------------------------------------------------------------
// Node info
// ---------------------------------------------------------------------------

// NodeInfo fetches node metadata from /.well-known/stigmem.
func (c *Client) NodeInfo(ctx context.Context) (*NodeInfo, error) {
	var out NodeInfo
	if err := c.doJSON(ctx, http.MethodGet, "/.well-known/stigmem", nil, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// ---------------------------------------------------------------------------
// Facts
// ---------------------------------------------------------------------------

// AssertOption configures an AssertFact call.
type AssertOption func(*assertConfig)

type assertConfig struct {
	confidence float64
	scope      FactScope
	validUntil string
}

// WithConfidence sets the confidence level (0.0–1.0; default 1.0).
func WithConfidence(v float64) AssertOption {
	return func(c *assertConfig) { c.confidence = v }
}

// WithScope sets the fact scope (default: company).
func WithScope(s FactScope) AssertOption {
	return func(c *assertConfig) { c.scope = s }
}

// WithValidUntil sets an ISO 8601 expiry timestamp for the fact.
func WithValidUntil(t string) AssertOption {
	return func(c *assertConfig) { c.validUntil = t }
}

type assertBody struct {
	Entity     string    `json:"entity"`
	Relation   string    `json:"relation"`
	Value      FactValue `json:"value"`
	Source     string    `json:"source"`
	Confidence float64   `json:"confidence"`
	Scope      FactScope `json:"scope"`
	ValidUntil string    `json:"valid_until,omitempty"`
}

// AssertFact asserts a new fact triple and returns the stored Fact.
func (c *Client) AssertFact(ctx context.Context, entity, relation string, value FactValue, source string, opts ...AssertOption) (*Fact, error) {
	cfg := assertConfig{confidence: 1.0, scope: ScopeCompany}
	for _, o := range opts {
		o(&cfg)
	}
	body := assertBody{
		Entity:     entity,
		Relation:   relation,
		Value:      value,
		Source:     source,
		Confidence: cfg.confidence,
		Scope:      cfg.scope,
		ValidUntil: cfg.validUntil,
	}
	var out Fact
	if err := c.doJSON(ctx, http.MethodPost, "/v1/facts", body, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// Retract asserts a retraction (confidence=0.0) for the given triple.
func (c *Client) Retract(ctx context.Context, entity, relation string, scope FactScope, source string) (*Fact, error) {
	return c.AssertFact(ctx, entity, relation, StringValue("retracted"), source,
		WithConfidence(0.0),
		WithScope(scope),
	)
}

// GetFact fetches a single fact by ID.
func (c *Client) GetFact(ctx context.Context, factID string) (*Fact, error) {
	var out Fact
	if err := c.doJSON(ctx, http.MethodGet, "/v1/facts/"+factID, nil, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// QueryOption configures a QueryFacts call.
type QueryOption func(*queryConfig)

type queryConfig struct {
	entity              string
	relation            string
	source              string
	scope               FactScope
	minConfidence       *float64
	includeContradicted bool
	includeExpired      bool
	cursor              string
	limit               int
	after               string
}

// QueryEntity filters results to the given entity URI.
func QueryEntity(v string) QueryOption { return func(c *queryConfig) { c.entity = v } }

// QueryRelation filters results to the given relation URI.
func QueryRelation(v string) QueryOption { return func(c *queryConfig) { c.relation = v } }

// QuerySource filters results to the given source URI.
func QuerySource(v string) QueryOption { return func(c *queryConfig) { c.source = v } }

// QueryScope filters results to the given scope.
func QueryScope(s FactScope) QueryOption { return func(c *queryConfig) { c.scope = s } }

// QueryMinConfidence sets the minimum confidence threshold.
func QueryMinConfidence(v float64) QueryOption {
	return func(c *queryConfig) { c.minConfidence = &v }
}

// QueryIncludeContradicted includes contradicted facts in results.
func QueryIncludeContradicted() QueryOption {
	return func(c *queryConfig) { c.includeContradicted = true }
}

// QueryIncludeExpired includes expired facts in results.
func QueryIncludeExpired() QueryOption { return func(c *queryConfig) { c.includeExpired = true } }

// QueryCursor sets the opaque pagination cursor from a previous response.
func QueryCursor(v string) QueryOption { return func(c *queryConfig) { c.cursor = v } }

// QueryLimit sets the page size (default 50).
func QueryLimit(v int) QueryOption { return func(c *queryConfig) { c.limit = v } }

// QueryAfter returns only facts asserted after the given HLC timestamp.
func QueryAfter(v string) QueryOption { return func(c *queryConfig) { c.after = v } }

// QueryFacts fetches a paginated list of facts matching the given filters.
func (c *Client) QueryFacts(ctx context.Context, opts ...QueryOption) (*FactPage, error) {
	cfg := queryConfig{limit: 50}
	for _, o := range opts {
		o(&cfg)
	}
	v := url.Values{}
	v.Set("limit", strconv.Itoa(cfg.limit))
	if cfg.entity != "" {
		v.Set("entity", cfg.entity)
	}
	if cfg.relation != "" {
		v.Set("relation", cfg.relation)
	}
	if cfg.source != "" {
		v.Set("source", cfg.source)
	}
	if cfg.scope != "" {
		v.Set("scope", string(cfg.scope))
	}
	if cfg.minConfidence != nil {
		v.Set("min_confidence", strconv.FormatFloat(*cfg.minConfidence, 'f', -1, 64))
	}
	if cfg.includeContradicted {
		v.Set("include_contradicted", "true")
	}
	if cfg.includeExpired {
		v.Set("include_expired", "true")
	}
	if cfg.cursor != "" {
		v.Set("cursor", cfg.cursor)
	}
	if cfg.after != "" {
		v.Set("after", cfg.after)
	}
	var out FactPage
	if err := c.doGet(ctx, "/v1/facts", v, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// ---------------------------------------------------------------------------
// Conflicts
// ---------------------------------------------------------------------------

// ConflictListOption configures a ListConflicts call.
type ConflictListOption func(*conflictListConfig)

type conflictListConfig struct {
	status string
	cursor string
	limit  int
}

// ConflictFilterStatus filters conflicts by status (default "unresolved").
func ConflictFilterStatus(s string) ConflictListOption {
	return func(c *conflictListConfig) { c.status = s }
}

// ConflictFilterCursor sets the opaque pagination cursor.
func ConflictFilterCursor(v string) ConflictListOption {
	return func(c *conflictListConfig) { c.cursor = v }
}

// ConflictFilterLimit sets the page size.
func ConflictFilterLimit(n int) ConflictListOption {
	return func(c *conflictListConfig) { c.limit = n }
}

// ListConflicts fetches a paginated list of conflicts.
func (c *Client) ListConflicts(ctx context.Context, opts ...ConflictListOption) (*ConflictPage, error) {
	cfg := conflictListConfig{status: "unresolved", limit: 50}
	for _, o := range opts {
		o(&cfg)
	}
	v := url.Values{}
	v.Set("limit", strconv.Itoa(cfg.limit))
	if cfg.status != "" {
		v.Set("status", cfg.status)
	}
	if cfg.cursor != "" {
		v.Set("cursor", cfg.cursor)
	}
	var out ConflictPage
	if err := c.doGet(ctx, "/v1/conflicts", v, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// ResolveOption configures a ResolveConflict call.
type ResolveOption func(*resolveConfig)

type resolveConfig struct {
	winningFactID  string
	resolutionNote string
	newValue       *FactValue
}

// WinningFactID sets the ID of the fact to treat as authoritative.
func WinningFactID(id string) ResolveOption {
	return func(c *resolveConfig) { c.winningFactID = id }
}

// ResolutionNote attaches a human-readable explanation to the resolution.
func ResolutionNote(n string) ResolveOption {
	return func(c *resolveConfig) { c.resolutionNote = n }
}

// NewConflictValue supplies a synthesized replacement value for both conflicting facts.
func NewConflictValue(v FactValue) ResolveOption {
	return func(c *resolveConfig) { c.newValue = &v }
}

type resolveBody struct {
	WinningFactID  string     `json:"winning_fact_id,omitempty"`
	ResolutionNote string     `json:"resolution_note"`
	NewValue       *FactValue `json:"new_value,omitempty"`
}

// ResolveConflict resolves a detected conflict by conflict ID.
func (c *Client) ResolveConflict(ctx context.Context, conflictID string, opts ...ResolveOption) (*ConflictResolution, error) {
	cfg := resolveConfig{}
	for _, o := range opts {
		o(&cfg)
	}
	body := resolveBody{
		WinningFactID:  cfg.winningFactID,
		ResolutionNote: cfg.resolutionNote,
		NewValue:       cfg.newValue,
	}
	var out ConflictResolution
	if err := c.doJSON(ctx, http.MethodPost, "/v1/conflicts/"+conflictID+"/resolve", body, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// ---------------------------------------------------------------------------
// Federation
// ---------------------------------------------------------------------------

// FederationStatus returns the list of known federation peers.
func (c *Client) FederationStatus(ctx context.Context) ([]Peer, error) {
	var out PeerPage
	if err := c.doGet(ctx, "/v1/federation/peers", nil, &out); err != nil {
		return nil, err
	}
	return out.Peers, nil
}

// ---------------------------------------------------------------------------
// Subscribe (channel-based polling)
// ---------------------------------------------------------------------------

// SubscribeOption configures a Subscribe call.
type SubscribeOption func(*subscribeConfig)

type subscribeConfig struct {
	interval time.Duration
	limit    int
}

// SubscribeInterval sets the polling interval (default 30s).
func SubscribeInterval(d time.Duration) SubscribeOption {
	return func(c *subscribeConfig) { c.interval = d }
}

// SubscribePageSize sets the maximum facts fetched per poll (default 100).
func SubscribePageSize(n int) SubscribeOption {
	return func(c *subscribeConfig) { c.limit = n }
}

// Subscribe returns a channel that receives batches of new facts in scope.
//
// A background goroutine polls the node at the configured interval and sends
// each non-empty page to the channel. The channel is closed when ctx is
// cancelled or a non-retryable error occurs. Drain the channel promptly to
// avoid blocking the background goroutine.
func (c *Client) Subscribe(ctx context.Context, scope FactScope, opts ...SubscribeOption) <-chan []Fact {
	cfg := subscribeConfig{interval: 30 * time.Second, limit: 100}
	for _, o := range opts {
		o(&cfg)
	}
	ch := make(chan []Fact, 1)
	go func() {
		defer close(ch)
		var cursor *string
		for {
			qopts := []QueryOption{QueryScope(scope), QueryLimit(cfg.limit)}
			if cursor != nil {
				qopts = append(qopts, QueryCursor(*cursor))
			}
			page, err := c.QueryFacts(ctx, qopts...)
			if err != nil {
				return
			}
			if len(page.Facts) > 0 {
				select {
				case ch <- page.Facts:
				case <-ctx.Done():
					return
				}
			}
			cursor = page.Cursor
			select {
			case <-time.After(cfg.interval):
			case <-ctx.Done():
				return
			}
		}
	}()
	return ch
}

// ---------------------------------------------------------------------------
// Recall (spec §20)
// ---------------------------------------------------------------------------

// RecallOption configures a Recall call.
type RecallOption func(*recallConfig)

type recallConfig struct {
	scope            FactScope
	tokenBudget      int
	depth            int
	weights          *RecallWeights
	minConfidence    float64
	includeNeighbors bool
	limit            int
}

// RecallInScope sets the scope to search (default: local).
func RecallInScope(s FactScope) RecallOption {
	return func(c *recallConfig) { c.scope = s }
}

// RecallTokenBudget sets the maximum token budget for packed results (default 4000).
func RecallTokenBudget(n int) RecallOption {
	return func(c *recallConfig) { c.tokenBudget = n }
}

// RecallDepth sets the graph-traversal depth 1–3 (default 2).
func RecallDepth(n int) RecallOption { return func(c *recallConfig) { c.depth = n } }

// RecallWithWeights overrides the default signal weights.
func RecallWithWeights(w RecallWeights) RecallOption {
	return func(c *recallConfig) { c.weights = &w }
}

// RecallMinConfidence sets the minimum fact confidence threshold (default 0.1).
func RecallMinConfidence(v float64) RecallOption {
	return func(c *recallConfig) { c.minConfidence = v }
}

// RecallExcludeNeighbors disables graph-neighbour expansion.
func RecallExcludeNeighbors() RecallOption {
	return func(c *recallConfig) { c.includeNeighbors = false }
}

// RecallPageSize sets the maximum candidate count before token-budget packing (default 100).
func RecallPageSize(n int) RecallOption { return func(c *recallConfig) { c.limit = n } }

type recallBody struct {
	Query            string        `json:"query"`
	Scope            FactScope     `json:"scope"`
	TokenBudget      int           `json:"token_budget"`
	Depth            int           `json:"depth"`
	Weights          RecallWeights `json:"weights"`
	MinConfidence    float64       `json:"min_confidence"`
	IncludeNeighbors bool          `json:"include_neighbors"`
	Limit            int           `json:"limit"`
}

// Recall executes a hybrid (BM25 + vector + graph) recall query against the node.
func (c *Client) Recall(ctx context.Context, query string, opts ...RecallOption) (*RecallResponse, error) {
	cfg := recallConfig{
		scope: ScopeLocal, tokenBudget: 4000, depth: 2,
		minConfidence: 0.1, includeNeighbors: true, limit: 100,
	}
	for _, o := range opts {
		o(&cfg)
	}
	weights := DefaultRecallWeights()
	if cfg.weights != nil {
		weights = *cfg.weights
	}
	body := recallBody{
		Query: query, Scope: cfg.scope, TokenBudget: cfg.tokenBudget,
		Depth: cfg.depth, Weights: weights, MinConfidence: cfg.minConfidence,
		IncludeNeighbors: cfg.includeNeighbors, Limit: cfg.limit,
	}
	var out RecallResponse
	if err := c.doJSON(ctx, http.MethodPost, "/v1/recall", body, &out); err != nil {
		return nil, err
	}
	return &out, nil
}

// ---------------------------------------------------------------------------
// Memory cards (spec §20)
// ---------------------------------------------------------------------------

// CardOption configures a GetCard call.
type CardOption func(*cardConfig)

type cardConfig struct {
	scope   FactScope
	refresh bool
}

// CardInScope sets the scope the card was materialised from (default: local).
func CardInScope(s FactScope) CardOption { return func(c *cardConfig) { c.scope = s } }

// CardForceRefresh forces a server-side refresh even if the card is fresh.
func CardForceRefresh() CardOption { return func(c *cardConfig) { c.refresh = true } }

// GetCard fetches the synthesized memory card for the given entity URI.
func (c *Client) GetCard(ctx context.Context, entityURI string, opts ...CardOption) (*MemoryCard, error) {
	cfg := cardConfig{scope: ScopeLocal}
	for _, o := range opts {
		o(&cfg)
	}
	v := url.Values{}
	v.Set("scope", string(cfg.scope))
	if cfg.refresh {
		v.Set("refresh", "true")
	}
	var out MemoryCard
	if err := c.doGet(ctx, "/v1/cards/"+entityURI, v, &out); err != nil {
		return nil, err
	}
	return &out, nil
}
