/**
 * Typed HTTP client for the stigmem node REST API.
 * Wraps assert (/v1/facts POST), query (/v1/facts GET), and recall (/v1/recall POST).
 */

export interface FactValue {
	type: "string" | "text" | "number" | "boolean" | "datetime" | "ref" | "null";
	v: string | number | boolean | null;
}

export interface FactRecord {
	id: string;
	entity: string;
	relation: string;
	value: FactValue;
	source: string;
	timestamp: string;
	confidence: number;
	scope: string;
	contradicted: boolean;
	garden_id: string | null;
	quarantine_status: string | null;
}

export interface QueryResponse {
	facts: FactRecord[];
	total: number;
	cursor: string | null;
}

export interface RecallWeights {
	lexical?: number;
	semantic?: number;
	graph?: number;
	source_trust?: number;
	recency?: number;
}

export interface RecallRequest {
	query: string;
	scope?: string;
	token_budget?: number;
	depth?: number;
	weights?: RecallWeights;
	min_confidence?: number;
	include_neighbors?: boolean;
	limit?: number;
}

export interface ScoredFact {
	fact: FactRecord;
	score: number;
	hop_distance: number;
	token_estimate: number;
	from_card: boolean;
}

export interface RecallResponse {
	recall_id: string;
	query_hash: string;
	facts: ScoredFact[];
	total_scored: number;
	token_budget: number;
	tokens_used: number;
	truncated: boolean;
}

export interface AssertRequest {
	entity: string;
	relation: string;
	value: FactValue;
	source: string;
	scope: string;
	confidence?: number;
}

export class StigmemClient {
	private baseUrl: string;
	private apiKey: string | null;

	constructor(nodeUrl: string, apiKey: string | null = null) {
		this.baseUrl = nodeUrl.replace(/\/$/, "");
		this.apiKey = apiKey;
	}

	private headers(): Record<string, string> {
		const h: Record<string, string> = { "Content-Type": "application/json" };
		if (this.apiKey) h["Authorization"] = `Bearer ${this.apiKey}`;
		return h;
	}

	async assertFact(req: AssertRequest): Promise<FactRecord> {
		const resp = await fetch(`${this.baseUrl}/v1/facts`, {
			method: "POST",
			headers: this.headers(),
			body: JSON.stringify(req),
		});
		if (!resp.ok) {
			const body = await resp.text();
			throw new Error(`stigmem assert failed ${resp.status}: ${body}`);
		}
		return resp.json() as Promise<FactRecord>;
	}

	async queryFacts(
		entity: string,
		scope: string,
		cursor?: string,
		limit = 100,
	): Promise<QueryResponse> {
		const params = new URLSearchParams({ entity, scope, limit: String(limit) });
		if (cursor) params.set("cursor", cursor);
		const resp = await fetch(`${this.baseUrl}/v1/facts?${params}`, {
			headers: this.headers(),
		});
		if (!resp.ok) {
			const body = await resp.text();
			throw new Error(`stigmem query failed ${resp.status}: ${body}`);
		}
		return resp.json() as Promise<QueryResponse>;
	}

	/** Fetch all pages for an entity, filtering out contradicted facts. */
	async queryAll(entity: string, scope: string): Promise<FactRecord[]> {
		const all: FactRecord[] = [];
		let cursor: string | undefined = undefined;
		do {
			const page = await this.queryFacts(entity, scope, cursor);
			for (const f of page.facts) {
				if (!f.contradicted && f.quarantine_status !== "pending") {
					all.push(f);
				}
			}
			cursor = page.cursor ?? undefined;
		} while (cursor);
		return all;
	}

	async recall(req: RecallRequest): Promise<RecallResponse> {
		const resp = await fetch(`${this.baseUrl}/v1/recall`, {
			method: "POST",
			headers: this.headers(),
			body: JSON.stringify(req),
		});
		if (!resp.ok) {
			const body = await resp.text();
			throw new Error(`stigmem recall failed ${resp.status}: ${body}`);
		}
		return resp.json() as Promise<RecallResponse>;
	}

	/** Ping the node. Returns true if reachable. */
	async ping(): Promise<boolean> {
		try {
			const resp = await fetch(`${this.baseUrl}/v1/health`, {
				headers: this.headers(),
				signal: AbortSignal.timeout(5000),
			});
			return resp.ok;
		} catch {
			return false;
		}
	}
}

// ---------------------------------------------------------------------------
// Value constructors (mirrors Python SDK helpers)
// ---------------------------------------------------------------------------

export const stringValue = (v: string): FactValue => ({ type: "string", v });
export const textValue = (v: string): FactValue => ({ type: "text", v });
export const numberValue = (v: number): FactValue => ({ type: "number", v });
export const booleanValue = (v: boolean): FactValue => ({ type: "boolean", v });
export const refValue = (v: string): FactValue => ({ type: "ref", v });
