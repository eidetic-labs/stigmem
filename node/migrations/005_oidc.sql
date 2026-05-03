-- Track B / B3: link api_keys to OIDC subjects for human identity exchange.
ALTER TABLE api_keys ADD COLUMN oidc_sub TEXT;
CREATE INDEX IF NOT EXISTS idx_api_keys_oidc_sub ON api_keys(oidc_sub);
