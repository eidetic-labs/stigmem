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


settings = Settings()
