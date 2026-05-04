from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="STIGMEM_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    db_path: str = "stigmem.db"
    host: str = "0.0.0.0"  # nosec B104 — overridable via STIGMEM_HOST; intentional server default
    port: int = 8765
    node_url: str = "http://localhost:8765"
    log_level: str = "info"

    # When True, every request must carry a valid Bearer token.
    # When False (default), all callers are trusted (single-operator mode).
    auth_required: bool = False

    # Federation — Phase 3 (spec §6)
    federation_enabled: bool = False
    # Base64url Ed25519 keypair. If both are empty, auto-generated and stored in node_meta.
    federation_pubkey: str = ""
    federation_privkey: str = ""
    # Pull replication interval in seconds (spec §6.3); advisory pull_interval_s from peer overrides this.
    federation_pull_interval_s: int = 30
    federation_push_enabled: bool = False
    # Nonce window: how long (seconds) a nonce is kept to detect replays (spec §6.6, default 5 min).
    federation_nonce_window_s: int = 300
    # Allow team-scoped facts to cross federation boundaries (must be explicitly enabled; audit-logged).
    federation_allow_team: bool = False

    # Decay sweeper (Phase 6, spec §decay)
    # 0 = disabled; positive = decay non-expiring facts older than N seconds when sweep runs without explicit ttl_seconds
    decay_ttl_seconds: int = 0
    # 0.0 = disabled; positive = decay facts below this confidence when sweep runs without explicit min_confidence
    decay_min_confidence: float = 0.0

    # Track C / C1: require Ed25519 attestation on all fact assertions.
    # When True, POST /v1/facts must include a valid attestation token.
    # Defaults to False for backward compatibility.
    attestation_required: bool = False

    # OIDC bridge (Track B / B3): human identity → scoped API keys.
    # Set oidc_enabled=true and configure the remaining fields to activate.
    oidc_enabled: bool = False
    # IdP issuer URL; discovery doc fetched from {issuer_url}/.well-known/openid-configuration
    oidc_issuer_url: str = ""
    # client_id expected in the id_token's "aud" claim
    oidc_audience: str = ""
    # lifetime of issued API keys in hours (default 8 h working-day session)
    oidc_token_ttl_hours: int = 8
    # comma-separated list of allowed email domains; empty = allow any
    oidc_allowed_domains: str = ""

    # Async job threshold (spec §14.5 / §15.4): scopes with more facts than this
    # trigger the async 202 path. Override in tests to force async path at small scale.
    async_job_threshold: int = 100_000

    # Source attestation mode (v0.9, spec §18).
    # "enforce": reject facts where source != caller's entity_uri (HTTP 403)
    # "warn"   : accept with attested=False; log warning (default; backward compatible)
    # "off"    : no check; attested=None on all facts
    source_attestation_mode: str = "warn"

    # Rate limiting for hosted offering (per API key, sliding 1-hour window).
    # 0 = disabled.
    rate_limit_write_per_hour: int = 1000
    rate_limit_read_per_hour: int = 5000

    # Storage backend (Phase 8).
    # "sqlite" (default) — local SQLite file at db_path.
    # "libsql"           — libSQL / Turso; uses db_path as the local replica
    #                      file; set libsql_url + libsql_auth_token for
    #                      embedded-replica sync with Turso.
    storage_backend: str = "sqlite"
    # Turso database endpoint, e.g. "libsql://my-db.turso.io"
    libsql_url: str = ""
    # Turso auth token (from `turso db tokens create`)
    libsql_auth_token: str = ""

    # Encryption at rest (Phase 8).
    # "off" (default) — no encryption; plaintext DB (dev-friendly default).
    # "on"            — SQLCipher for SQLite backend; native encryption for libSQL.
    # When "on", exactly one of at_rest_key_passphrase_env / at_rest_key_kms_uri
    # must be set — the node refuses to start otherwise.
    at_rest_encryption: str = "off"
    # Name of the env var whose value is the passphrase (not the passphrase itself).
    # e.g. STIGMEM_AT_REST_KEY_PASSPHRASE_ENV=MY_DB_PASSPHRASE
    at_rest_key_passphrase_env: str = ""
    # KMS URI for raw 32-byte key material. "env://VAR" reads a hex-encoded key
    # from env var VAR. Future schemes: "aws-kms://...", "gcp-kms://...".
    at_rest_key_kms_uri: str = ""

    @field_validator("at_rest_encryption")
    @classmethod
    def _validate_encryption_mode(cls, v: str) -> str:
        if v not in ("on", "off"):
            raise ValueError(f"at_rest_encryption must be 'on' or 'off'; got {v!r}")
        return v

    # Federation Trust — Phase 8 (spec §19)
    # trust_mode controls source-trust scoring and quarantine routing:
    #   "strict"  — trust is computed for all inbound facts; t < 0.2 → quarantine.
    #   "relaxed" — trust is computed but quarantine is not auto-triggered (default).
    #   "off"     — trust not computed; source_trust is null on all facts.
    trust_mode: str = "relaxed"

    # Sanitizer mode (§19.7) applied at recall time:
    #   "block"     — fact excluded, placeholder returned.
    #   "quarantine"— fact moved to quarantine garden.
    #   "warn"      — fact returned with sanitizer_warnings (default).
    #   "off"       — no check (implied by trust_mode=off).
    sanitizer_mode: str = "warn"

    # UUID of the node's designated quarantine garden.
    # Required in strict mode; facts below threshold are rejected with 403 if unset.
    quarantine_garden_id: str = ""

    # Source-trust score weights (§19.4.2).  Must sum to 1.0; deviations are not
    # validated at startup — set incorrectly and t will be out of [0,1] range.
    trust_weight_identity:    float = 0.35
    trust_weight_peer_history: float = 0.30
    trust_weight_scope_authority: float = 0.25
    trust_weight_attestation_mode: float = 0.10

    # Path to a newline-delimited file of extra sanitizer regex patterns (§19.7.2).
    sanitizer_extra_patterns_file: str = ""

    # Path to YAML file defining operator auto-trust rules (always_trust / never_trust).
    trust_rules_file: str = ""

    # Transparency log backend (§19.2.3):
    #   "local"  — append-only JSONL file with hash chain (default, no external deps).
    #   "rekor"  — Sigstore Rekor REST API.
    #   "off"    — no TL submission; inclusion proofs are never verified.
    tl_backend: str = "local"
    tl_local_path: str = "stigmem_tl.jsonl"
    tl_rekor_url: str = "https://rekor.sigstore.dev"


settings = Settings()
