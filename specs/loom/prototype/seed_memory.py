"""Shadow-migrate CTO MEMORY.md facts into the Loom prototype node.

Markdown stays source of truth. This writes a parallel copy into the
running prototype at http://localhost:8000. Run after `docker run` or
`uvicorn main:app`.

Usage:
    python seed_memory.py [--url http://localhost:8000]
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

import urllib.request
import urllib.error
import json


def post_fact(url: str, entity: str, relation: str, value: dict[str, Any],
              source: str, confidence: float = 1.0, scope: str = "company") -> dict[str, Any]:
    payload = json.dumps({
        "entity": entity,
        "relation": relation,
        "value": value,
        "source": source,
        "confidence": confidence,
        "scope": scope,
    }).encode()
    req = urllib.request.Request(
        f"{url}/v1/facts",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"  ERROR {e.code}: {e.read().decode()}", file=sys.stderr)
        return {}


def sv(v: str) -> dict[str, Any]:
    return {"type": "string", "v": v}


def bv(v: bool) -> dict[str, Any]:
    return {"type": "boolean", "v": v}


def seed(url: str) -> None:
    src = "agent:cto"
    print(f"Seeding Loom node at {url} ...")

    # --- project: Acme vs Giganomix boundary ---
    facts = [
        ("company:acme", "org:role", sv("agent platform / federated knowledge fabric"), src, 1.0),
        ("company:giganomix", "org:role", sv("GRC / compliance-as-a-service (Comply)"), src, 1.0),
        ("company:acme", "product:boundary", sv("no in-house compliance engine; route GRC to Giganomix Comply"), src, 1.0),
        ("company:acme", "product:comply_copilot_phase", sv("Phase 5"), src, 1.0),
    ]

    # --- project: roadmap v4 (Loom) ---
    facts += [
        ("roadmap:v4", "roadmap:status", sv("committed thesis — pending board sign-off rev 4"), src, 1.0),
        ("roadmap:v4", "roadmap:name", sv("Loom"), src, 1.0),
        ("roadmap:v4", "roadmap:layer", sv("above Paperclip/company, below open internet"), src, 1.0),
        ("roadmap:v4", "roadmap:primitive", sv("open federated knowledge fabric + typed intent/protocol layer"), src, 1.0),
        ("roadmap:v4", "roadmap:license", sv("Apache-2.0"), src, 1.0),
        ("roadmap:v4", "roadmap:current_phase", sv("Phase 0 — 2-week scoping sprint"), src, 1.0),
        ("roadmap:v4", "roadmap:phase0_exit_date", sv("2026-05-15"), src, 0.8),

        # dead roadmaps — low confidence (historical only)
        ("roadmap:v3", "roadmap:status", sv("dead — board flagged as Paperclip clone"), src, 1.0),
        ("roadmap:v2", "roadmap:status", sv("dead — SMB pillar plan, replaced by v4"), src, 1.0),
        ("roadmap:v1", "roadmap:status", sv("dead — commodity OSS agents positioning"), src, 1.0),

        # frictions Loom solves
        ("loom:friction:1", "friction:description", sv("memory siloed per-agent"), src, 1.0),
        ("loom:friction:2", "friction:description", sv("decision changes propagate as CEO labor not facts"), src, 1.0),
        ("loom:friction:3", "friction:description", sv("user preferences don't follow user across agents"), src, 1.0),
        ("loom:friction:4", "friction:description", sv("no portability across companies"), src, 1.0),
        ("loom:friction:5", "friction:description", sv("knowledge decays silently"), src, 1.0),
        ("loom:friction:6", "friction:description", sv("no confidence on the wire"), src, 1.0),
        ("loom:friction:7", "friction:description", sv("no provenance on facts"), src, 1.0),
    ]

    ok = 0
    for entity, relation, value, source, confidence in facts:
        result = post_fact(url, entity, relation, value, source, confidence)
        if result.get("id"):
            print(f"  ✓ {entity} / {relation}")
            ok += 1
        else:
            print(f"  ✗ {entity} / {relation}")

    print(f"\nSeeded {ok}/{len(facts)} facts.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    args = parser.parse_args()
    seed(args.url)
