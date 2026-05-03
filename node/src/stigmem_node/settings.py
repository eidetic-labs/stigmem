from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="STIGMEM_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    db_path: str = "stigmem.db"
    host: str = "0.0.0.0"
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


settings = Settings()
