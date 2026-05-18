"""stigmem-py — Python client SDK for Stigmem.

Compatible with the canonical Stigmem spec at v0.9.0a1 and onward.
See https://github.com/eidetic-labs/stigmem for the protocol spec,
threat model, and adopter documentation.
"""

from importlib.metadata import PackageNotFoundError as _PackageNotFoundError
from importlib.metadata import version as _pkg_version

from .client import AsyncStigmemClient, StigmemClient
from .exceptions import (
    StigmemAuthError,
    StigmemConflictError,
    StigmemError,
    StigmemHTTPError,
    StigmemNotFoundError,
)
from .models import (
    AssertRequest,
    BooleanValue,
    Conflict,
    ConflictPage,
    ConflictResolution,
    DatetimeValue,
    Fact,
    FactChainCheckpointProof,
    FactChainProof,
    FactPage,
    FactScope,
    FactValue,
    MemoryCard,
    NodeInfo,
    NullValue,
    NumberValue,
    Peer,
    PeerPage,
    RecallRequest,
    RecallResponse,
    RecallWeights,
    RefValue,
    ResolveRequest,
    ScoreBreakdown,
    ScoredFact,
    StringValue,
    TextValue,
    boolean_value,
    datetime_value,
    null_value,
    number_value,
    ref_value,
    string_value,
    text_value,
)
from .verification import (
    StigmemVerificationError,
    compute_fact_cid,
    verify_fact_chain_proof,
    verify_fact_cid,
)

__all__ = [
    # clients
    "StigmemClient",
    "AsyncStigmemClient",
    # exceptions
    "StigmemError",
    "StigmemHTTPError",
    "StigmemAuthError",
    "StigmemNotFoundError",
    "StigmemConflictError",
    # models
    "Fact",
    "FactChainCheckpointProof",
    "FactChainProof",
    "FactPage",
    "FactValue",
    "FactScope",
    "StringValue",
    "TextValue",
    "NumberValue",
    "BooleanValue",
    "DatetimeValue",
    "RefValue",
    "NullValue",
    "NodeInfo",
    "Peer",
    "PeerPage",
    "Conflict",
    "ConflictPage",
    "ConflictResolution",
    "AssertRequest",
    "ResolveRequest",
    # recall + cards (Phase 9)
    "RecallRequest",
    "RecallResponse",
    "RecallWeights",
    "ScoreBreakdown",
    "ScoredFact",
    "MemoryCard",
    # value constructors
    "string_value",
    "text_value",
    "number_value",
    "boolean_value",
    "datetime_value",
    "ref_value",
    "null_value",
    # verification
    "StigmemVerificationError",
    "compute_fact_cid",
    "verify_fact_cid",
    "verify_fact_chain_proof",
]

# Read version from installed package metadata so __version__ stays in
# lockstep with whatever pip installed. Falls back to "0.0.0+unknown" only
# when the package is run from a non-installed source tree (e.g. uv sync
# in a workspace context that hasn't built the wheel yet); CI's package
# build path always populates the metadata.
try:
    __version__ = _pkg_version("stigmem-py")
except _PackageNotFoundError:
    __version__ = "0.0.0+unknown"
