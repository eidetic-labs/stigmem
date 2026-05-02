# Muninn Design Partner Outreach — Draft Messages

**Status:** Draft — week 1 outreach for Phase 1  
**Targets:** Chalef (Zep), Packer (Letta), topoteretes (Cognee)  
**Ask:** 30-min interview + async spec review + named co-author credit on federation section

---

## 1. Daniel Chalef — Zep (daniel@getzep.com)

**Subject:** Muninn spec — your temporal edge model is in it, want to co-author federation?

Hi Daniel,

I built a spec called Muninn — an open federated knowledge fabric for AI agents. While researching prior art, Zep's temporal edge model (`valid_at`/`invalid_at`) stood out as the cleanest solution to the "historical fact vs uncertain fact" conflation problem. I borrowed the pattern directly and cited Zep in the design decisions.

Muninn is now v0.2 and going public. The federation section (§6) is the least-developed part — it's a sketch with the right intuitions but missing the operational detail that comes from actually running a multi-node system at scale.

I'd like to co-author that section with you if you're interested. The ask is: a 30-minute call, async review of a PR with the proposed federation design, and your name on the spec.

Spec: [link once public]

Worth 30 minutes?

---

## 2. Charles Packer — Letta (charles@letta.com)

**Subject:** Muninn — federated agent memory spec, looking for co-authors on the federation section

Hi Charles,

I've been building a spec for federated agent memory called Muninn. The core primitive is an atomic fact: `(entity, relation, value, source, timestamp, confidence, scope)` — immutable, provenance-first, contradiction-surfacing. It's what I'd want underneath a system like Letta if I needed memory to travel across agent boundaries and org boundaries without losing provenance.

The intent envelope (§4) is directly inspired by the coordination problems MemGPT surfaced — how do you hand off in-flight context from one agent to another without the receiver having to re-infer everything from scratch?

We're going public with v0.2 this week and I'm looking for 3 design partners to co-author the federation section in v0.3. Your experience with multi-agent memory architectures would make the federation design significantly more honest. The ask is a 30-minute call and async PR review.

Spec: [link once public]

---

## 3. topoteretes — Cognee (GitHub: topoteretes)

**Subject:** Muninn spec — interested in co-authoring the federation and namespace governance sections?

Hey,

Building an open spec for federated agent memory called Muninn — atomic facts with provenance, scopes, contradiction detection, and eventually federation. Going public this week with v0.2.

Two sections where Cognee's experience would be most useful:

1. **Federation (§6)** — the gossip/sync model is a sketch. You've shipped a knowledge graph system at scale; I'd want your input on what the real failure modes are.
2. **Namespace governance (§8, Q1)** — who owns `memory:*`, `intent:*`, `rel:*`? IANA-style registry vs. community PRs? This decision shapes the whole ecosystem.

Looking for ~3 design partners for v0.3 co-authorship. The ask is a 30-min call and async PR review.

Spec: [link once public]

---

## Send sequence

| Day | Action |
|-----|--------|
| Day 1 (repo goes live) | Replace `[link once public]` with actual GitHub URL, send all 3 |
| Day 5 | One follow-up if no response (single follow-up only) |
| Day 10 | Close out; note non-responses in ACM-23 |

## Notes

- Don't send before the repo is public — the link needs to be live
- If any of these turn into calls, record key decisions as new facts in the Muninn node and update the spec design decisions log (§7)
- Co-author credit goes in the spec header: `## Co-authors\n- [Name], [Affiliation] — federation section`
