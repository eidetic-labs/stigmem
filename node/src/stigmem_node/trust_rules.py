"""Operator-configured auto-trust rules — spec §19 (ACM-186 scope).

Rules are loaded from a YAML file at path STIGMEM_TRUST_RULES_FILE, or
from the database table `quarantine_rules` (loaded at runtime via the admin API).

YAML format (documented in docs/trust-rules.md):

    # Always trust facts from org-a about any entity
    always_trust:
      - org_uri: "stigmem://org-a.example.com"
        scope: null       # null = all scopes
        entity_prefix: null  # null = all entities
        reason: "Tier-1 partner"

    # Never trust org-b when asserting about scope 'public'
    never_trust:
      - org_uri: "stigmem://org-b.example.com"
        scope: "public"
        entity_prefix: null
        reason: "Untrusted external feed"

evaluate_auto_rules(source_uri, scope) returns:
    1.0   — if an always_trust rule matches
    0.0   — if a never_trust rule matches
    None  — no matching rule; caller falls through to computed score
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("stigmem.trust_rules")


def _load_yaml_rules(path: str) -> dict[str, list[dict[str, Any]]]:
    try:
        import yaml
    except ImportError:
        logger.warning("PyYAML not installed — trust_rules_file ignored")
        return {}

    try:
        with open(path) as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        logger.warning("trust_rules_file not found: %s", path)
        return {}
    except Exception as exc:
        logger.error("Failed to load trust_rules_file %s: %s", path, exc)
        return {}

    if not isinstance(data, dict):
        return {}
    return data


def _rule_matches(rule: dict[str, Any], source_uri: str, scope: str) -> bool:
    if rule.get("org_uri") != source_uri:
        return False
    rule_scope = rule.get("scope")
    return not (rule_scope is not None and rule_scope != scope)


def evaluate_auto_rules(source_uri: str, scope: str) -> float | None:
    """Return 1.0, 0.0, or None per the operator-configured rules."""
    from .settings import settings

    # First check DB-stored rules (runtime admin API)
    db_result = _evaluate_db_rules(source_uri, scope)
    if db_result is not None:
        return db_result

    # Then check file-based rules
    rules_file = settings.trust_rules_file
    if not rules_file:
        return None

    rules = _load_yaml_rules(rules_file)

    for rule in rules.get("always_trust", []):
        if _rule_matches(rule, source_uri, scope):
            return 1.0

    for rule in rules.get("never_trust", []):
        if _rule_matches(rule, source_uri, scope):
            return 0.0

    return None


def _evaluate_db_rules(source_uri: str, scope: str) -> float | None:
    """Check quarantine_rules table for matching always/never rules."""
    try:
        from .db import db

        with db() as conn:
            rows = conn.execute(
                "SELECT rule_type, scope FROM quarantine_rules WHERE org_uri = ?",
                (source_uri,),
            ).fetchall()
    except Exception:
        return None

    for row in rows:
        rule_scope = row["scope"]
        if rule_scope is not None and rule_scope != scope:
            continue
        if row["rule_type"] == "always_trust":
            return 1.0
        if row["rule_type"] == "never_trust":
            return 0.0

    return None
