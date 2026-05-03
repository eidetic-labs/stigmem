import { getIronSession, IronSession, SessionOptions } from "iron-session";
import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";

export interface SessionData {
  apiKey?: string;
  entityUri?: string;
  permissions?: string[];
  // PKCE state — set in /api/auth/login, consumed in /api/auth/callback
  oidcVerifier?: string;
  oidcState?: string;
}

const SESSION_OPTIONS: SessionOptions = {
  password: process.env.SESSION_SECRET ?? "changeme-set-SESSION_SECRET-in-env",
  cookieName: "stigmem_session",
  cookieOptions: {
    secure: process.env.NODE_ENV === "production",
    httpOnly: true,
    sameSite: "lax",
    maxAge: 60 * 60 * 8, // 8 hours
  },
};

export async function getSession(): Promise<IronSession<SessionData>> {
  return getIronSession<SessionData>(await cookies(), SESSION_OPTIONS);
}

export async function getSessionFromRequest(
  req: NextRequest,
  res: NextResponse
): Promise<IronSession<SessionData>> {
  return getIronSession<SessionData>(req, res, SESSION_OPTIONS);
}
