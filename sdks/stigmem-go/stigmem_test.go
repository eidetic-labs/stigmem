package stigmem_test

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync/atomic"
	"testing"
	"time"

	stigmem "github.com/eidetic-labs/stigmem-go"
)

// ---------------------------------------------------------------------------
// Shared test fixtures
// ---------------------------------------------------------------------------

var sampleFactMap = map[string]any{
	"id":           "fact-001",
	"entity":       "user:alice",
	"relation":     "memory:role",
	"value":        map[string]any{"type": "string", "v": "CEO"},
	"source":       "agent:test",
	"timestamp":    "2026-05-04T00:00:00Z",
	"hlc":          "1746403200000.001",
	"confidence":   1.0,
	"scope":        "company",
	"contradicted": false,
}

var sampleNodeInfoMap = map[string]any{
	"version":    "0.5",
	"node_id":    "stigmem://node.acme",
	"node_url":   "http://test-node",
	"auth":       "required",
	"federation": "disabled",
	"namespaces": []string{"memory:", "intent:"},
}

func jsonResp(w http.ResponseWriter, code int, body any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	_ = json.NewEncoder(w).Encode(body)
}

func newMux() (*http.ServeMux, *stigmem.Client, func()) {
	mux := http.NewServeMux()
	srv := httptest.NewServer(mux)
	c := stigmem.New(srv.URL, stigmem.WithAPIKey("sk-test"))
	return mux, c, srv.Close
}

// ---------------------------------------------------------------------------
// NodeInfo
// ---------------------------------------------------------------------------

func TestNodeInfo(t *testing.T) {
	mux, c, stop := newMux()
	defer stop()

	mux.HandleFunc("/.well-known/stigmem", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			t.Errorf("unexpected method %s", r.Method)
		}
		if !strings.HasPrefix(r.Header.Get("Authorization"), "Bearer ") {
			t.Errorf("missing bearer token")
		}
		jsonResp(w, 200, sampleNodeInfoMap)
	})

	info, err := c.NodeInfo(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if info.Version != "0.5" {
		t.Errorf("version = %q, want 0.5", info.Version)
	}
	if info.NodeID != "stigmem://node.acme" {
		t.Errorf("node_id = %q, want stigmem://node.acme", info.NodeID)
	}
}

// ---------------------------------------------------------------------------
// AssertFact
// ---------------------------------------------------------------------------

func TestAssertFact(t *testing.T) {
	mux, c, stop := newMux()
	defer stop()

	mux.HandleFunc("/v1/facts", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			jsonResp(w, 405, map[string]any{"detail": "method not allowed"})
			return
		}
		jsonResp(w, 201, sampleFactMap)
	})

	fact, err := c.AssertFact(context.Background(),
		"user:alice", "memory:role",
		stigmem.StringValue("CEO"), "agent:test",
	)
	if err != nil {
		t.Fatal(err)
	}
	if fact.ID != "fact-001" {
		t.Errorf("id = %q, want fact-001", fact.ID)
	}
	if fact.Value.Type != "string" {
		t.Errorf("value.type = %q, want string", fact.Value.Type)
	}
}

func TestAssertFactOptions(t *testing.T) {
	mux, c, stop := newMux()
	defer stop()

	var gotBody map[string]any
	mux.HandleFunc("/v1/facts", func(w http.ResponseWriter, r *http.Request) {
		b, _ := io.ReadAll(r.Body)
		_ = json.Unmarshal(b, &gotBody)
		jsonResp(w, 201, sampleFactMap)
	})

	_, err := c.AssertFact(context.Background(),
		"user:bob", "memory:dept",
		stigmem.StringValue("eng"), "agent:hr",
		stigmem.WithConfidence(0.8),
		stigmem.WithScope(stigmem.ScopeTeam),
		stigmem.WithValidUntil("2027-01-01T00:00:00Z"),
	)
	if err != nil {
		t.Fatal(err)
	}
	if gotBody["scope"] != "team" {
		t.Errorf("scope = %v, want team", gotBody["scope"])
	}
	if gotBody["confidence"] != 0.8 {
		t.Errorf("confidence = %v, want 0.8", gotBody["confidence"])
	}
	if gotBody["valid_until"] != "2027-01-01T00:00:00Z" {
		t.Errorf("valid_until = %v, want 2027-01-01T00:00:00Z", gotBody["valid_until"])
	}
}

// ---------------------------------------------------------------------------
// Retract
// ---------------------------------------------------------------------------

func TestRetract(t *testing.T) {
	mux, c, stop := newMux()
	defer stop()

	var gotBody map[string]any
	mux.HandleFunc("/v1/facts", func(w http.ResponseWriter, r *http.Request) {
		b, _ := io.ReadAll(r.Body)
		_ = json.Unmarshal(b, &gotBody)
		retracted := map[string]any{
			"id": "fact-002", "entity": "user:alice", "relation": "memory:role",
			"value": map[string]any{"type": "string", "v": "retracted"},
			"source": "agent:test", "timestamp": "2026-05-04T00:00:00Z",
			"confidence": 0.0, "scope": "company", "contradicted": false,
		}
		jsonResp(w, 201, retracted)
	})

	fact, err := c.Retract(context.Background(), "user:alice", "memory:role", stigmem.ScopeCompany, "agent:test")
	if err != nil {
		t.Fatal(err)
	}
	if fact.Confidence != 0.0 {
		t.Errorf("confidence = %v, want 0.0", fact.Confidence)
	}
	if gotBody["confidence"] != 0.0 {
		t.Errorf("request confidence = %v, want 0.0", gotBody["confidence"])
	}
	if gotBody["scope"] != "company" {
		t.Errorf("request scope = %v, want company", gotBody["scope"])
	}
}

// ---------------------------------------------------------------------------
// GetFact
// ---------------------------------------------------------------------------

func TestGetFact(t *testing.T) {
	mux, c, stop := newMux()
	defer stop()

	mux.HandleFunc("/v1/facts/fact-001", func(w http.ResponseWriter, r *http.Request) {
		jsonResp(w, 200, sampleFactMap)
	})

	fact, err := c.GetFact(context.Background(), "fact-001")
	if err != nil {
		t.Fatal(err)
	}
	if fact.ID != "fact-001" {
		t.Errorf("id = %q, want fact-001", fact.ID)
	}
}

// ---------------------------------------------------------------------------
// QueryFacts
// ---------------------------------------------------------------------------

func TestQueryFacts(t *testing.T) {
	mux, c, stop := newMux()
	defer stop()

	var gotQuery string
	mux.HandleFunc("/v1/facts", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodGet {
			jsonResp(w, 405, nil)
			return
		}
		gotQuery = r.URL.RawQuery
		jsonResp(w, 200, map[string]any{
			"facts": []any{sampleFactMap},
			"total": 1,
			"cursor": nil,
		})
	})

	page, err := c.QueryFacts(context.Background(),
		stigmem.QueryEntity("user:alice"),
		stigmem.QueryScope(stigmem.ScopeCompany),
		stigmem.QueryLimit(25),
	)
	if err != nil {
		t.Fatal(err)
	}
	if len(page.Facts) != 1 {
		t.Fatalf("len(facts) = %d, want 1", len(page.Facts))
	}
	if page.Facts[0].Entity != "user:alice" {
		t.Errorf("entity = %q, want user:alice", page.Facts[0].Entity)
	}
	if !strings.Contains(gotQuery, "entity=user%3Aalice") {
		t.Errorf("query missing entity param: %s", gotQuery)
	}
	if !strings.Contains(gotQuery, "scope=company") {
		t.Errorf("query missing scope param: %s", gotQuery)
	}
	if !strings.Contains(gotQuery, "limit=25") {
		t.Errorf("query missing limit param: %s", gotQuery)
	}
}

// ---------------------------------------------------------------------------
// ListConflicts
// ---------------------------------------------------------------------------

func TestListConflicts(t *testing.T) {
	mux, c, stop := newMux()
	defer stop()

	mux.HandleFunc("/v1/conflicts", func(w http.ResponseWriter, r *http.Request) {
		jsonResp(w, 200, map[string]any{
			"conflicts": []any{},
			"cursor":    nil,
			"has_more":  false,
		})
	})

	page, err := c.ListConflicts(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if len(page.Conflicts) != 0 {
		t.Errorf("expected 0 conflicts, got %d", len(page.Conflicts))
	}
}

// ---------------------------------------------------------------------------
// ResolveConflict
// ---------------------------------------------------------------------------

func TestResolveConflict(t *testing.T) {
	mux, c, stop := newMux()
	defer stop()

	var gotBody map[string]any
	mux.HandleFunc("/v1/conflicts/c-001/resolve", func(w http.ResponseWriter, r *http.Request) {
		b, _ := io.ReadAll(r.Body)
		_ = json.Unmarshal(b, &gotBody)
		jsonResp(w, 200, map[string]any{
			"resolution_fact_id": "fact-999",
			"conflict_status":    "resolved",
		})
	})

	result, err := c.ResolveConflict(context.Background(), "c-001",
		stigmem.WinningFactID("fact-001"),
		stigmem.ResolutionNote("prefer fact-001"),
	)
	if err != nil {
		t.Fatal(err)
	}
	if result.ConflictStatus != "resolved" {
		t.Errorf("conflict_status = %q, want resolved", result.ConflictStatus)
	}
	if result.ResolutionFactID != "fact-999" {
		t.Errorf("resolution_fact_id = %q, want fact-999", result.ResolutionFactID)
	}
	if gotBody["winning_fact_id"] != "fact-001" {
		t.Errorf("winning_fact_id = %v, want fact-001", gotBody["winning_fact_id"])
	}
	if gotBody["resolution_note"] != "prefer fact-001" {
		t.Errorf("resolution_note = %v", gotBody["resolution_note"])
	}
}

// ---------------------------------------------------------------------------
// FederationStatus
// ---------------------------------------------------------------------------

func TestFederationStatus(t *testing.T) {
	mux, c, stop := newMux()
	defer stop()

	mux.HandleFunc("/v1/federation/peers", func(w http.ResponseWriter, r *http.Request) {
		jsonResp(w, 200, map[string]any{"peers": []any{}})
	})

	peers, err := c.FederationStatus(context.Background())
	if err != nil {
		t.Fatal(err)
	}
	if len(peers) != 0 {
		t.Errorf("expected 0 peers, got %d", len(peers))
	}
}

// ---------------------------------------------------------------------------
// Recall
// ---------------------------------------------------------------------------

func TestRecall(t *testing.T) {
	mux, c, stop := newMux()
	defer stop()

	var gotBody map[string]any
	mux.HandleFunc("/v1/recall", func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			t.Errorf("unexpected method %s", r.Method)
		}
		b, _ := io.ReadAll(r.Body)
		_ = json.Unmarshal(b, &gotBody)
		jsonResp(w, 200, map[string]any{
			"recall_id":    "rc-abc",
			"query_hash":   "h1",
			"facts":        []any{},
			"total_scored": 0,
			"token_budget": 4000,
			"tokens_used":  0,
			"truncated":    false,
		})
	})

	resp, err := c.Recall(context.Background(), "alice role",
		stigmem.RecallInScope(stigmem.ScopeCompany),
		stigmem.RecallTokenBudget(2000),
	)
	if err != nil {
		t.Fatal(err)
	}
	if resp.RecallID != "rc-abc" {
		t.Errorf("recall_id = %q, want rc-abc", resp.RecallID)
	}
	if gotBody["query"] != "alice role" {
		t.Errorf("query = %v, want 'alice role'", gotBody["query"])
	}
	if gotBody["scope"] != "company" {
		t.Errorf("scope = %v, want company", gotBody["scope"])
	}
	if gotBody["token_budget"] != float64(2000) {
		t.Errorf("token_budget = %v, want 2000", gotBody["token_budget"])
	}
}

// ---------------------------------------------------------------------------
// GetCard
// ---------------------------------------------------------------------------

func TestGetCard(t *testing.T) {
	mux, c, stop := newMux()
	defer stop()

	var gotQuery string
	mux.HandleFunc("/v1/cards/user:alice", func(w http.ResponseWriter, r *http.Request) {
		gotQuery = r.URL.RawQuery
		jsonResp(w, 200, map[string]any{
			"entity_uri":         "user:alice",
			"scope":              "company",
			"summary":            "Alice is a lead engineer.",
			"fact_hashes":        []string{"h1", "h2"},
			"avg_confidence":     0.95,
			"is_stale":           false,
			"has_contradictions": false,
		})
	})

	card, err := c.GetCard(context.Background(), "user:alice",
		stigmem.CardInScope(stigmem.ScopeCompany),
		stigmem.CardForceRefresh(),
	)
	if err != nil {
		t.Fatal(err)
	}
	if card.EntityURI != "user:alice" {
		t.Errorf("entity_uri = %q, want user:alice", card.EntityURI)
	}
	if card.Summary != "Alice is a lead engineer." {
		t.Errorf("summary = %q", card.Summary)
	}
	if !strings.Contains(gotQuery, "scope=company") {
		t.Errorf("query missing scope: %s", gotQuery)
	}
	if !strings.Contains(gotQuery, "refresh=true") {
		t.Errorf("query missing refresh: %s", gotQuery)
	}
}

// ---------------------------------------------------------------------------
// Subscribe
// ---------------------------------------------------------------------------

func TestSubscribe(t *testing.T) {
	mux, c, stop := newMux()
	defer stop()

	var callCount atomic.Int32
	mux.HandleFunc("/v1/facts", func(w http.ResponseWriter, r *http.Request) {
		callCount.Add(1)
		jsonResp(w, 200, map[string]any{
			"facts":  []any{sampleFactMap},
			"total":  1,
			"cursor": nil,
		})
	})

	ctx, cancel := context.WithTimeout(context.Background(), 200*time.Millisecond)
	defer cancel()

	ch := c.Subscribe(ctx, stigmem.ScopeCompany,
		stigmem.SubscribeInterval(50*time.Millisecond),
		stigmem.SubscribePageSize(10),
	)

	var received int
	for batch := range ch {
		received += len(batch)
	}

	if received == 0 {
		t.Error("subscribe received no facts")
	}
	if n := callCount.Load(); n < 2 {
		t.Errorf("expected at least 2 poll calls, got %d", n)
	}
}

func TestSubscribeContextCancel(t *testing.T) {
	mux, c, stop := newMux()
	defer stop()

	mux.HandleFunc("/v1/facts", func(w http.ResponseWriter, r *http.Request) {
		jsonResp(w, 200, map[string]any{
			"facts": []any{},
			"total": 0,
			"cursor": nil,
		})
	})

	ctx, cancel := context.WithCancel(context.Background())
	ch := c.Subscribe(ctx, stigmem.ScopeLocal, stigmem.SubscribeInterval(10*time.Millisecond))
	cancel()

	// channel must close; drain it with a timeout guard
	select {
	case _, ok := <-ch:
		if ok {
			// drain remaining
			for range ch {
			}
		}
	case <-time.After(500 * time.Millisecond):
		t.Fatal("channel did not close after context cancel")
	}
}

// ---------------------------------------------------------------------------
// Error handling
// ---------------------------------------------------------------------------

func TestErrorTypes(t *testing.T) {
	mux, c, stop := newMux()
	defer stop()

	cases := []struct {
		code    int
		path    string
		errType any
	}{
		{401, "/v1/facts/e401", &stigmem.StigmemAuthError{}},
		{403, "/v1/facts/e403", &stigmem.StigmemAuthError{}},
		{404, "/v1/facts/e404", &stigmem.StigmemNotFoundError{}},
		{409, "/v1/facts/e409", &stigmem.StigmemConflictError{}},
		{500, "/v1/facts/e500", &stigmem.StigmemError{}},
	}

	for _, tc := range cases {
		code := tc.code
		mux.HandleFunc(tc.path, func(w http.ResponseWriter, r *http.Request) {
			jsonResp(w, code, map[string]any{"detail": http.StatusText(code)})
		})
	}

	t.Run("401_auth", func(t *testing.T) {
		_, err := c.GetFact(context.Background(), "e401")
		var target *stigmem.StigmemAuthError
		if !errors.As(err, &target) {
			t.Errorf("expected StigmemAuthError, got %T: %v", err, err)
		}
		if target.StatusCode != 401 {
			t.Errorf("StatusCode = %d, want 401", target.StatusCode)
		}
	})
	t.Run("403_auth", func(t *testing.T) {
		_, err := c.GetFact(context.Background(), "e403")
		var target *stigmem.StigmemAuthError
		if !errors.As(err, &target) {
			t.Errorf("expected StigmemAuthError, got %T: %v", err, err)
		}
	})
	t.Run("404_not_found", func(t *testing.T) {
		_, err := c.GetFact(context.Background(), "e404")
		var target *stigmem.StigmemNotFoundError
		if !errors.As(err, &target) {
			t.Errorf("expected StigmemNotFoundError, got %T: %v", err, err)
		}
	})
	t.Run("409_conflict", func(t *testing.T) {
		_, err := c.GetFact(context.Background(), "e409")
		var target *stigmem.StigmemConflictError
		if !errors.As(err, &target) {
			t.Errorf("expected StigmemConflictError, got %T: %v", err, err)
		}
	})
	t.Run("500_generic", func(t *testing.T) {
		_, err := c.GetFact(context.Background(), "e500")
		var auth *stigmem.StigmemAuthError
		if errors.As(err, &auth) {
			t.Errorf("500 should not be StigmemAuthError")
		}
		var base *stigmem.StigmemError
		if !errors.As(err, &base) {
			t.Errorf("expected StigmemError, got %T: %v", err, err)
		}
		if base.StatusCode != 500 {
			t.Errorf("StatusCode = %d, want 500", base.StatusCode)
		}
	})
}

// ---------------------------------------------------------------------------
// FactValue constructors
// ---------------------------------------------------------------------------

func TestFactValueConstructors(t *testing.T) {
	cases := []struct {
		v    stigmem.FactValue
		typ  string
		wantV any
	}{
		{stigmem.StringValue("hello"), "string", "hello"},
		{stigmem.TextValue("long text"), "text", "long text"},
		{stigmem.NumberValue(3.14), "number", 3.14},
		{stigmem.BooleanValue(true), "boolean", true},
		{stigmem.DatetimeValue("2026-05-04T00:00:00Z"), "datetime", "2026-05-04T00:00:00Z"},
		{stigmem.RefValue("stigmem://other"), "ref", "stigmem://other"},
		{stigmem.NullValue(), "null", nil},
	}
	for _, tc := range cases {
		if tc.v.Type != tc.typ {
			t.Errorf("Type = %q, want %q", tc.v.Type, tc.typ)
		}
		if tc.v.V != tc.wantV {
			t.Errorf("V = %v (%T), want %v (%T)", tc.v.V, tc.v.V, tc.wantV, tc.wantV)
		}
	}
}
