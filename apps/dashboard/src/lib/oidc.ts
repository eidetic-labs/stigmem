/**
 * Minimal OIDC PKCE helpers — no external library required.
 * Uses Web Crypto API (Node 18+ / browser).
 */

const ISSUER = process.env.OIDC_ISSUER_URL ?? "";
const CLIENT_ID = process.env.OIDC_CLIENT_ID ?? "";
const CLIENT_SECRET = process.env.OIDC_CLIENT_SECRET ?? "";
const REDIRECT_URI = process.env.OIDC_REDIRECT_URI ?? "";

interface OidcConfig {
  authorization_endpoint: string;
  token_endpoint: string;
}

let _configCache: OidcConfig | null = null;

export async function fetchOidcConfig(): Promise<OidcConfig> {
  if (_configCache) return _configCache;
  const url = `${ISSUER.replace(/\/$/, "")}/.well-known/openid-configuration`;
  const res = await fetch(url, { next: { revalidate: 600 } });
  if (!res.ok) throw new Error(`OIDC discovery failed: ${res.status}`);
  _configCache = await res.json();
  return _configCache!;
}

function base64url(buf: ArrayBuffer): string {
  return Buffer.from(buf)
    .toString("base64")
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=/g, "");
}

export async function generatePkce(): Promise<{ verifier: string; challenge: string }> {
  const array = new Uint8Array(32);
  crypto.getRandomValues(array);
  const verifier = base64url(array.buffer);
  const enc = new TextEncoder();
  const digest = await crypto.subtle.digest("SHA-256", enc.encode(verifier));
  const challenge = base64url(digest);
  return { verifier, challenge };
}

export function generateState(): string {
  const array = new Uint8Array(16);
  crypto.getRandomValues(array);
  return base64url(array.buffer);
}

export async function buildAuthorizationUrl(
  challenge: string,
  state: string
): Promise<string> {
  const config = await fetchOidcConfig();
  const params = new URLSearchParams({
    response_type: "code",
    client_id: CLIENT_ID,
    redirect_uri: REDIRECT_URI,
    scope: "openid email profile",
    code_challenge: challenge,
    code_challenge_method: "S256",
    state,
  });
  return `${config.authorization_endpoint}?${params.toString()}`;
}

export interface TokenResponse {
  id_token: string;
  access_token: string;
  expires_in?: number;
}

export async function exchangeCode(
  code: string,
  verifier: string
): Promise<TokenResponse> {
  const config = await fetchOidcConfig();
  const body = new URLSearchParams({
    grant_type: "authorization_code",
    code,
    redirect_uri: REDIRECT_URI,
    client_id: CLIENT_ID,
    code_verifier: verifier,
  });
  if (CLIENT_SECRET) body.set("client_secret", CLIENT_SECRET);

  const res = await fetch(config.token_endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: body.toString(),
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Token exchange failed: ${res.status} ${err}`);
  }
  return res.json();
}
