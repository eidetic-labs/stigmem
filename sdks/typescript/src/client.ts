export class AIPlatformClient {
  private readonly baseUrl: string;
  private readonly apiKey: string;

  constructor(options: { baseUrl?: string; apiKey: string }) {
    this.baseUrl = options.baseUrl ?? "http://localhost:8000";
    this.apiKey = options.apiKey;
  }

  async health(): Promise<{ status: string; version: string }> {
    const res = await fetch(`${this.baseUrl}/health`, {
      headers: { Authorization: `Bearer ${this.apiKey}` },
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  }

  async listAgents(): Promise<Array<{ id: string; name: string; status: string }>> {
    const res = await fetch(`${this.baseUrl}/v1/agents`, {
      headers: { Authorization: `Bearer ${this.apiKey}` },
    });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return res.json();
  }
}
