export interface AgentRunOptions {
  agentId: string;
  input: string;
  sessionId?: string;
}

export interface RunResult {
  runId: string;
  output: string;
  status: "completed" | "failed";
}
