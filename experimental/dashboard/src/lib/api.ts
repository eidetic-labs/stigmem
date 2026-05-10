/**
 * Thin fetch wrapper used by server-side code (route handlers, server components)
 * to call the stigmem backend with the caller's API key.
 *
 * Client components call /api/stigmem/* proxy routes instead.
 */

const STIGMEM_URL = (
  process.env.NEXT_PUBLIC_STIGMEM_API_URL ?? "http://localhost:8765"
).replace(/\/$/, "");

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function stigmemFetch(
  path: string,
  apiKey: string,
  options: RequestInit = {}
): Promise<Response> {
  const url = `${STIGMEM_URL}${path}`;
  return fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
      Authorization: `Bearer ${apiKey}`,
    },
  });
}

export async function stigmemJson<T>(
  path: string,
  apiKey: string,
  options: RequestInit = {}
): Promise<T> {
  const res = await stigmemFetch(path, apiKey, options);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {}
    throw new ApiError(res.status, detail);
  }
  return res.json();
}

// ── Type mirrors of the stigmem backend models ──────────────────────────────

export interface FactValue {
  type: "string" | "number" | "boolean" | "null" | "text";
  v: string | number | boolean | null;
}

export interface FactRecord {
  id: string;
  entity: string;
  relation: string;
  value: FactValue;
  source: string;
  timestamp: string;
  hlc: string | null;
  received_from: string | null;
  valid_until: string | null;
  confidence: number;
  scope: string;
  attested_key_id: string | null;
  contradicted: boolean;
  warnings: string[];
}

export interface QueryResponse {
  facts: FactRecord[];
  total: number;
  cursor: string | null;
}

export interface GardenMemberRecord {
  entity_uri: string;
  role: string;
  added_by: string;
  added_at: string;
}

export interface GardenRecord {
  id: string;
  garden_id: string;
  slug: string;
  name: string;
  scope: string;
  description: string | null;
  created_by: string;
  created_at: string;
  members: GardenMemberRecord[];
}

export interface AuditLogEntry {
  id: string;
  fact_id: string;
  event_type: string;
  entity_uri: string;
  oidc_sub: string | null;
  source: string;
  attested_key_id: string | null;
  ts: string;
  attested_key_entity_uri: string | null;
  attested_key_description: string | null;
  fact_entity: string | null;
  fact_relation: string | null;
  fact_value_type: string | null;
  fact_value_v: string | null;
  fact_scope: string | null;
}

export interface AuditLogResponse {
  entries: AuditLogEntry[];
  total: number;
  cursor: string | null;
}

export interface MeResponse {
  entity_uri: string;
  permissions: string[];
  oidc_sub: string | null;
}
