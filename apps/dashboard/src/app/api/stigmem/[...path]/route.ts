import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/session";

const STIGMEM_URL = (
  process.env.NEXT_PUBLIC_STIGMEM_API_URL ?? "http://localhost:8765"
).replace(/\/$/, "");

/**
 * Proxy all /api/stigmem/* requests to the stigmem backend, injecting the
 * caller's API key from the HttpOnly session cookie.
 *
 * Client components use React Query against these proxy routes so the raw
 * API key never leaves the server.
 */
async function proxy(req: NextRequest, path: string[]) {
  const session = await getSession();
  if (!session.apiKey) {
    return NextResponse.json({ error: "unauthenticated" }, { status: 401 });
  }

  const backendPath = "/" + path.join("/");
  const search = req.nextUrl.search;
  const url = `${STIGMEM_URL}${backendPath}${search}`;

  const headers: Record<string, string> = {
    Authorization: `Bearer ${session.apiKey}`,
  };
  const contentType = req.headers.get("content-type");
  if (contentType) headers["Content-Type"] = contentType;

  const body =
    req.method !== "GET" && req.method !== "HEAD"
      ? await req.arrayBuffer()
      : undefined;

  const upstream = await fetch(url, {
    method: req.method,
    headers,
    body: body ? Buffer.from(body) : undefined,
  });

  const resHeaders = new Headers();
  upstream.headers.forEach((v, k) => {
    if (k !== "content-encoding") resHeaders.set(k, v);
  });

  return new NextResponse(upstream.body, {
    status: upstream.status,
    headers: resHeaders,
  });
}

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  return proxy(req, (await params).path);
}

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  return proxy(req, (await params).path);
}

export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  return proxy(req, (await params).path);
}

export async function DELETE(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  return proxy(req, (await params).path);
}
