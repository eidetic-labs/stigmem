// Command assert_recall_subscribe demonstrates the stigmem Go SDK:
// assert a fact, run a hybrid recall, and subscribe to scope updates.
package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"time"

	stigmem "github.com/eidetic-labs/stigmem-go"
)

func main() {
	nodeURL := os.Getenv("STIGMEM_URL")
	if nodeURL == "" {
		nodeURL = "http://localhost:8765"
	}
	apiKey := os.Getenv("STIGMEM_API_KEY")

	c := stigmem.New(nodeURL, stigmem.WithAPIKey(apiKey))
	ctx := context.Background()

	// 1. Node info — verify connectivity
	info, err := c.NodeInfo(ctx)
	if err != nil {
		log.Fatalf("node info: %v", err)
	}
	fmt.Printf("Connected to %s (v%s)\n", info.NodeID, info.Version)

	// 2. Assert a fact
	fact, err := c.AssertFact(ctx,
		"user:alice", "memory:role",
		stigmem.StringValue("lead engineer"),
		"example/assert_recall_subscribe",
		stigmem.WithScope(stigmem.ScopeCompany),
	)
	if err != nil {
		log.Fatalf("assert: %v", err)
	}
	fmt.Printf("Asserted fact %s\n", fact.ID)

	// 3. Hybrid recall
	recall, err := c.Recall(ctx, "alice engineering role",
		stigmem.RecallInScope(stigmem.ScopeCompany),
		stigmem.RecallTokenBudget(2000),
	)
	if err != nil {
		log.Fatalf("recall: %v", err)
	}
	fmt.Printf("Recall: %d facts packed (tokens %d/%d)\n",
		len(recall.Facts), recall.TokensUsed, recall.TokenBudget)
	for _, sf := range recall.Facts {
		fmt.Printf("  [%.3f] %s  %s\n", sf.Score, sf.Fact.Entity, sf.Fact.Relation)
	}

	// 4. Subscribe — cancel after 5 seconds
	subCtx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()

	fmt.Println("Subscribing to company scope (5s)…")
	ch := c.Subscribe(subCtx, stigmem.ScopeCompany,
		stigmem.SubscribeInterval(2*time.Second),
	)
	for batch := range ch {
		fmt.Printf("  received %d fact(s)\n", len(batch))
	}
	fmt.Println("Done.")
}
