/**
 * AI Platform TypeScript SDK — Phase 2 stub.
 * Mirrors the Python agent_platform API surface over HTTP.
 */
export interface RunRequest {
  message: string;
  sessionId?: string;
  model?: string;
  instructions?: string;
}

export interface RunResponse {
  content: string;
  sessionId?: string;
  inputTokens: number;
  outputTokens: number;
  costUsd: number;
}

export class AIPlatformClient {
  constructor(
    private readonly baseUrl: string,
    private readonly apiKey?: string,
  ) {}

  async run(request: RunRequest): Promise<RunResponse> {
    const response = await fetch(`${this.baseUrl}/api/v1/agents/run`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(this.apiKey ? { Authorization: `Bearer ${this.apiKey}` } : {}),
      },
      body: JSON.stringify(request),
    });
    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }
    return response.json() as Promise<RunResponse>;
  }
}
