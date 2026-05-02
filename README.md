# AI Platform

Open-source AI agent platform for SMBs — built on three pillars: a composable agent framework, a compliance engine, and pre-built vertical agents.

## Three Pillars

**Pillar A — Pre-built SMB Agents**
Production-ready agents for e-commerce support, bookkeeping, and appointment scheduling. Deploy in minutes; no ML expertise required.

**Pillar B — Compliance Engine**
Automated evidence collection, AI policy generation, and continuous drift detection for SOC 2, GDPR, and HIPAA.

**Pillar C — Agent Framework (this repo)**
The composable primitives (Agent, Tool, Memory, Orchestrator) that power everything else. Build custom agents in <50 lines of Python.

## Quickstart

```bash
# Install the core framework
pip install agent-platform-core

# Create your first agent
from agent_platform import Agent, AgentConfig, tool
from agent_platform.llm import AnthropicAdapter

@tool(description="Search the web for information")
async def web_search(query: str) -> str:
    # Your search implementation here
    return f"Results for: {query}"

config = AgentConfig(
    agent_id="my-agent",
    system_prompt="You are a helpful assistant.",
)
```

## Local Development

Prerequisites: Python 3.11+, Docker, [uv](https://docs.astral.sh/uv/), [pnpm](https://pnpm.io/) 9+

```bash
# Clone and set up
git clone https://github.com/acmecorp/ai-platform
cd ai-platform

# Start the dev stack (FastAPI + PostgreSQL 16 + pgvector + Redis)
cp .env.example .env  # Add ANTHROPIC_API_KEY
docker compose -f infra/docker/docker-compose.yml up -d

# Install Python deps
uv sync

# Run tests
uv run pytest

# Run linting
uv run ruff check . && uv run mypy packages/core/src
```

## Repository Layout

```
packages/core        # Agent, Tool, Memory, Orchestrator primitives
packages/agents      # Pre-built SMB agents
packages/compliance  # Compliance engine
packages/integrations/  # Third-party connectors
apps/api             # FastAPI REST + WebSocket server
apps/dashboard       # Next.js 14 dashboard
apps/docs            # Mintlify documentation
sdks/typescript      # TypeScript SDK
examples/            # Runnable examples
infra/               # Docker Compose, Helm, Terraform
```

## Contributing

We welcome contributions! Please read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting a PR. All contributions require a DCO sign-off (`git commit -s`).

## License

Apache 2.0 — see [LICENSE](LICENSE).
