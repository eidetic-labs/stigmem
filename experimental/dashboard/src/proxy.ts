import { NextRequest, NextResponse } from "next/server";
import { getSessionFromRequest } from "@/lib/session";

const PUBLIC_PATHS = ["/login", "/api/auth/"];

export async function proxy(req: NextRequest) {
  const { pathname } = req.nextUrl;

  // Pass through public paths and static assets
  if (
    PUBLIC_PATHS.some((p) => pathname.startsWith(p)) ||
    pathname.startsWith("/_next") ||
    pathname.startsWith("/favicon")
  ) {
    return NextResponse.next();
  }

  const res = NextResponse.next();
  const session = await getSessionFromRequest(req, res);

  if (!session.apiKey) {
    const loginUrl = req.nextUrl.clone();
    loginUrl.pathname = "/login";
    loginUrl.searchParams.set("redirect", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return res;
}

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
