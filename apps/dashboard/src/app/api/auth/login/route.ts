import { NextRequest, NextResponse } from "next/server";
import { buildAuthorizationUrl, generatePkce, generateState } from "@/lib/oidc";
import { getSessionFromRequest } from "@/lib/session";

/**
 * GET /api/auth/login
 * Initiates the OIDC PKCE flow: generates verifier + state, stores them in the
 * session cookie, then redirects to the IdP authorization endpoint.
 */
export async function GET(req: NextRequest) {
  const res = NextResponse.redirect("about:blank"); // placeholder, replaced below
  const session = await getSessionFromRequest(req, res);

  const { verifier, challenge } = await generatePkce();
  const state = generateState();

  session.oidcVerifier = verifier;
  session.oidcState = state;
  await session.save();

  let authUrl: string;
  try {
    authUrl = await buildAuthorizationUrl(challenge, state);
  } catch {
    return NextResponse.json({ error: "OIDC provider unavailable" }, { status: 503 });
  }

  const redirectRes = NextResponse.redirect(authUrl);
  // Copy Set-Cookie headers iron-session wrote on the placeholder response
  res.headers.getSetCookie().forEach((c) => redirectRes.headers.append("Set-Cookie", c));
  return redirectRes;
}
