"""Fact assertion and query routes — Spec-03-HTTP-API and Spec-01-Fact-Model."""

from __future__ import annotations

# Re-exported binding used by tests that monkey-patch ``routes.facts._settings``.
from ...settings import settings as _settings  # noqa: F401
from .assertion import assert_fact  # noqa: F401
from .cid import _CidVerifyResponse, verify_cid  # noqa: F401
from .common import (  # noqa: F401
    _SYSTEM_RELATION_PREFIX,
    _check_source_attestation,
    _embed_fact_background,
    _encode_v,
    _get_tombstone_filter,
    _is_valid_entity_uri,
    _record_contradictions,
    _validate_relation,
    logger,
    router,
)
from .provenance import get_provenance  # noqa: F401
from .query import _validate_as_of, query_facts  # noqa: F401
from .single import get_fact  # noqa: F401

__all__ = [
    "_CidVerifyResponse",
    "_SYSTEM_RELATION_PREFIX",
    "_check_source_attestation",
    "_embed_fact_background",
    "_encode_v",
    "_get_tombstone_filter",
    "_is_valid_entity_uri",
    "_record_contradictions",
    "_settings",
    "_validate_as_of",
    "_validate_relation",
    "assert_fact",
    "get_fact",
    "get_provenance",
    "logger",
    "query_facts",
    "router",
    "verify_cid",
]
