import { NextRequest, NextResponse } from "next/server";
import { exchangeCode } from "@/lib/oidc";
import { getSessionFromRequest } from "@/lib/session";
import { stigmemJson } from "@/lib/api";
import type { GardenRecord } from "@/lib/api";

/**
 * GET /api/auth/callback
 * Receives OIDC authorization code, exchanges for id_token, then calls
 * POST /v1/auth/oidc/exchange on the stigmem backend to obtain an API key.
 * Stores the key in the iron-session HttpOnly cookie and redirects to /facts.
 * New users (no existing gardens) are redirected to /onboarding instead.
 */
export async function GET(req: NextRequest) {
  const res = NextResponse.redirect(new URL("/facts", req.url));
  const session = await getSessionFromRequest(req, res);

  const params = req.nextUrl.searchParams;
  const code = params.get("code");
  const state = params.get("state");
  const error = params.get("error");

  if (error) {
    const errUrl = new URL("/login", req.url);
    errUrl.searchParams.set("error", error);
    return NextResponse.redirect(errUrl);
  }

  const storedState = session.oidcState;
  const verifier = session.oidcVerifier;

  if (!code || !state || !verifier || state !== storedState) {
    const errUrl = new URL("/login", req.url);
    errUrl.searchParams.set("error", "invalid_state");
    return NextResponse.redirect(errUrl);
  }

  // Clean up PKCE state
  session.oidcVerifier = undefined;
  session.oidcState = undefined;

  let tokens: { id_token: string };
  try {
    tokens = await exchangeCode(code, verifier);
  } catch {
    const errUrl = new URL("/login", req.url);
    errUrl.searchParams.set("error", "token_exchange_failed");
    return NextResponse.redirect(errUrl);
  }

  // Exchange id_token for stigmem API key
  let exchangeResult: { api_key: string; entity_uri: string; permissions: string[] };
  try {
    exchangeResult = await stigmemJson(`/v1/auth/oidc/exchange`, "", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id_token: tokens.id_token }),
    });
  } catch {
    const errUrl = new URL("/login", req.url);
    errUrl.searchParams.set("error", "stigmem_exchange_failed");
    return NextResponse.redirect(errUrl);
  }

  session.apiKey = exchangeResult.api_key;
  session.entityUri = exchangeResult.entity_uri;
  session.permissions = exchangeResult.permissions;
  await session.save();

  // Detect new users: check for existing gardens and auto-provision if none found.
  let isNewUser = false;
  try {
    const gardens = await stigmemJson<GardenRecord[]>("/v1/gardens", exchangeResult.api_key);
    if (gardens.length === 0) {
      await stigmemJson("/v1/gardens", exchangeResult.api_key, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          slug: "my-facts",
          name: "My Facts",
          scope: "private",
          description: "Your personal fact namespace.",
        }),
      });
      isNewUser = true;
    }
  } catch {
    // Garden check/creation is best-effort; fall through to /facts on failure.
  }

  const dest = isNewUser ? "/onboarding" : "/facts";
  const redirectRes = NextResponse.redirect(new URL(dest, req.url));
  res.headers.getSetCookie().forEach((c) => redirectRes.headers.append("Set-Cookie", c));
  return redirectRes;
}
