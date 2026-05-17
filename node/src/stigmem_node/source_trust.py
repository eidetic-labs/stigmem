"""Source-trust score computation — spec §19.4.

Exported surface:
    compute_source_trust(source_uri, scope, identity) -> float
    get_cached_trust(source_uri) -> float | None
    bust_trust_cache(source_uri) -> None
    is_blocklisted(source_uri) -> bool

The score is in [0.0, 1.0].  A source with no computable score defaults to 0.5.
Admin-blocklisted sources always return 0.0.

Per §19.4.4, implementations SHOULD cache per-source trust scores with a TTL of
at least 60 seconds.  We use a simple time-based in-process cache; each worker
process maintains its own cache (acceptable for single-process deployments).
"""

from __future__ import annotations

import logging
import os
import time
from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .auth import Identity

logger = logging.getLogger("stigmem.source_trust")

# Cache: { source_uri: (score: float, expires_at: float) }
_TRUST_CACHE: dict[str, tuple[float, float]] = {}
_CACHE_TTL_S: float = 60.0

# Cached cutoff for peer-history lookups. Refreshing this once per cache window
# keeps the rolling 30-day window accurate enough for source-trust scoring
# without recalculating the timestamp on every fresh trust computation.
_PEER_HISTORY_CUTOFF_REFRESH_S: float = 60.0


@lru_cache(maxsize=2)
def _peer_history_cutoff_iso_for_bucket(_bucket: int) -> str:
    from datetime import UTC, datetime, timedelta

    return (datetime.now(UTC) - timedelta(days=30)).isoformat()


def _peer_history_cutoff_iso() -> str:
    refresh_bucket = int(time.monotonic() // _PEER_HISTORY_CUTOFF_REFRESH_S)
    return _peer_history_cutoff_iso_for_bucket(refresh_bucket)


def get_cached_trust(source_uri: str) -> float | None:
    entry = _TRUST_CACHE.get(source_uri)
    if entry is None:
        return None
    score, expires_at = entry
    if time.monotonic() > expires_at:
        del _TRUST_CACHE[source_uri]
        return None
    return score


def _set_cache(source_uri: str, score: float) -> None:
    _TRUST_CACHE[source_uri] = (score, time.monotonic() + _CACHE_TTL_S)


def bust_trust_cache(source_uri: str) -> None:
    _TRUST_CACHE.pop(source_uri, None)


def compute_source_trust(
    source_uri: str,
    scope: str,
    identity: Identity | None = None,
    *,
    identity_strength_override: float | None = None,
) -> float:
    """Return the source-trust score for *source_uri* asserting a fact at *scope*.

    Uses cached value if available (TTL 60 s).  Caches the freshly computed value.
    When *identity_strength_override* is set the cache is bypassed so the
    override is always honoured (spec §19.4.2 capability-token boost).
    """
    if identity_strength_override is None:
        cached = get_cached_trust(source_uri)
        if cached is not None:
            return cached

    score = _compute_fresh(
        source_uri, scope, identity, identity_strength_override=identity_strength_override
    )
    if identity_strength_override is None:
        _set_cache(source_uri, score)
    return score


def _compute_fresh(
    source_uri: str,
    scope: str,
    identity: Identity | None,
    *,
    identity_strength_override: float | None = None,
) -> float:
    from .settings import settings

    trust_mode = settings.trust_mode
    if trust_mode == "off":
        return 0.5  # not computed; return neutral default

    # Check blocklist first — always returns 0.0 regardless (§19.4.5)
    if is_blocklisted(source_uri):
        return 0.0

    # Check auto-rules (operator always_trust / never_trust)
    from .trust_rules import evaluate_auto_rules

    override = evaluate_auto_rules(source_uri, scope)
    if override is not None:
        return override

    w_i = settings.trust_weight_identity
    w_p = settings.trust_weight_peer_history
    w_s = settings.trust_weight_scope_authority
    w_a = settings.trust_weight_attestation_mode

    i_s = (
        identity_strength_override
        if identity_strength_override is not None
        else _identity_strength(source_uri)
    )
    p_h = _peer_history(source_uri)
    s_a = _scope_authority(source_uri, scope, identity)
    a_m = _attestation_mode_factor()

    raw = w_i * i_s + w_p * p_h + w_s * s_a + w_a * a_m
    return max(0.0, min(1.0, raw))


# ---------------------------------------------------------------------------
# Component functions (§19.4.2)
# ---------------------------------------------------------------------------


def _identity_strength(source_uri: str) -> float:
    """Score [0,1] measuring how strongly the source is identified."""
    if not source_uri:
        return 0.0

    from .db import db

    with db() as conn:
        # Source has a valid org manifest (§19.1)?
        manifest_row = conn.execute(
            "SELECT log_entry_json FROM federation_manifests WHERE entity_uri = ?",
            (source_uri,),
        ).fetchone()
        if manifest_row is not None:
            has_log_proof = manifest_row["log_entry_json"] is not None
            return 1.0 if has_log_proof else 0.7

        # Source is a registered local API key?
        key_row = conn.execute(
            "SELECT id FROM agent_keys WHERE entity_uri = ? AND status = 'active'",
            (source_uri,),
        ).fetchone()
        if key_row is not None:
            return 0.4

    # Syntactically valid URI (has a scheme)?
    if "://" in source_uri or source_uri.startswith("stigmem:"):
        return 0.1

    return 0.0


def _peer_history(source_uri: str) -> float:
    """Score [0,1] derived from interaction history over the past 30 days."""
    from .db import db

    cutoff = _peer_history_cutoff_iso()

    with db() as conn:
        row = conn.execute(
            """SELECT
                 COUNT(*) AS total,
                 SUM(CASE WHEN attested = 0 THEN 1 ELSE 0 END) AS failures
               FROM facts
               WHERE source = ? AND timestamp >= ?""",
            (source_uri, cutoff),
        ).fetchone()

    if row is None:
        return 0.5  # no history → neutral (§19.4.2)

    total = row["total"] or 0
    failures = row["failures"] or 0

    if total < 10:
        return 0.5  # new source
    failure_rate = failures / total
    if total >= 100 and failure_rate == 0.0:
        return 1.0
    if failure_rate >= 0.05:
        return 0.3
    return 0.7  # ≥ 10 facts, < 5% failures


def _scope_authority(source_uri: str, scope: str, identity: Identity | None) -> float:
    """Score [0,1] measuring whether source has authority to write at this scope."""
    if identity is not None and identity.entity_uri == source_uri and identity.can_write():
        return 0.9

    from .settings import settings

    # Source entity prefix matches node authority
    try:
        from urllib.parse import urlparse

        parsed = urlparse(settings.node_url)
        authority = parsed.netloc or parsed.path
        if source_uri.startswith(f"stigmem://{authority}"):
            return 0.7
    except Exception:
        logger.exception("Failed to parse node_url while scoring source authority")

    # External entity without explicit scope authority
    if scope in ("public", "team"):
        return 0.5  # treat as external with federate-level access

    return 0.2


def _attestation_mode_factor() -> float:
    """Score based on source-attestation mode only when the plugin is enabled."""
    from .settings import settings

    if not _source_attestation_plugin_enabled():
        return 0.2

    mode = settings.source_attestation_mode
    if mode == "enforce":
        return 1.0
    if mode == "warn":
        return 0.6
    return 0.2  # "off"


def _source_attestation_plugin_enabled() -> bool:
    from .plugins import get_registry

    if "stigmem-plugin-source-attestation" not in get_registry().registered_plugins():
        return False
    raw = os.environ.get("STIGMEM_SOURCE_ATTESTATION_ENABLED", "")
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def is_blocklisted(source_uri: str) -> bool:
    """Return True if source_uri has been admin-blocklisted (peer_history = 0.0 rule)."""
    from .db import db

    with db() as conn:
        row = conn.execute(
            "SELECT id FROM quarantine_rules WHERE rule_type = 'never_trust' AND org_uri = ?",
            (source_uri,),
        ).fetchone()
    return row is not None
