import { NextResponse } from "next/server";
import { getSession } from "@/lib/session";

/** Returns the caller's session identity for client-side use. */
export async function GET() {
  const session = await getSession();
  if (!session.apiKey) {
    return NextResponse.json({ error: "unauthenticated" }, { status: 401 });
  }
  return NextResponse.json({
    entityUri: session.entityUri,
    permissions: session.permissions ?? [],
  });
}
