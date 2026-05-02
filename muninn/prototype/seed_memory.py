"""Load example facts into a running Muninn node.

Usage:
    python seed_memory.py [--url http://localhost:8000]
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from typing import Any


def post_fact(url: str, entity: str, relation: str, value: dict[str, Any],
              source: str, confidence: float = 1.0, scope: str = "local") -> dict[str, Any]:
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
    src = "agent:example"
    print(f"Seeding Muninn node at {url} ...")

    facts = [
        # User preferences
        ("user:alice", "preference:timezone", sv("America/New_York"), src, 1.0),
        ("user:alice", "memory:role", sv("CEO"), src, 1.0),
        ("user:alice", "preference:format", sv("markdown"), src, 0.9),

        # Agent capabilities
        ("agent:assistant", "capability:coding", bv(True), src, 1.0),
        ("agent:assistant", "capability:research", bv(True), src, 1.0),

        # Project state
        ("project:muninn", "roadmap:status", sv("public-draft"), src, 1.0),
        ("project:muninn", "roadmap:version", sv("v0.2"), src, 1.0),
        ("project:muninn", "roadmap:license", sv("Apache-2.0"), src, 1.0),

        # Example contradiction pair — two agents disagree on budget
        ("project:muninn", "budget:estimate_usd", {"type": "number", "v": 5000}, "agent:assistant", 0.7),
        ("project:muninn", "budget:estimate_usd", {"type": "number", "v": 8000}, "agent:other", 0.6),
    ]

    ok = 0
    for args in facts:
        entity, relation, value, source = args[0], args[1], args[2], args[3]
        confidence = args[4] if len(args) > 4 else 1.0  # type: ignore[misc]
        scope = args[5] if len(args) > 5 else "local"  # type: ignore[misc]
        result = post_fact(url, entity, relation, value, source, confidence, scope)
        if result.get("id"):
            contradicted = " [CONTRADICTION]" if result.get("contradicted") else ""
            print(f"  ok {entity} / {relation}{contradicted}")
            ok += 1
        else:
            print(f"  fail {entity} / {relation}")

    print(f"\nSeeded {ok}/{len(facts)} facts.")
    print(f"\nQuery example:")
    print(f"  curl '{url}/v1/facts?entity=user:alice'")
    print(f"  curl '{url}/v1/facts?entity=project:muninn&include_contradicted=true'")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8000")
    args = parser.parse_args()
    seed(args.url)
