# AI Platform

Open-source AI agent platform for SMBs — automate support, compliance, and workflows.

## Three Pillars

| Pillar | What it does |
|--------|-------------|
| **A — Agent Platform** | Pre-built autonomous agents for customer support, bookkeeping, and scheduling |
| **B — Compliance Engine** | SOC2/GDPR/HIPAA automation: evidence collection, policy generation, audit prep |
| **C — Developer Tools** | Agent framework: orchestration, tool use, memory, multi-agent coordination |

## Quickstart

```bash
# 1. Clone and install
git clone https://github.com/acme/ai-platform.git
cd ai-platform
uv sync

# 2. Start the dev stack (PostgreSQL + Redis)
docker compose -f infra/docker/docker-compose.yml up -d

# 3. Run the API
cd apps/api && uv run uvicorn api.main:app --reload

# 4. Build your first agent
from agent_platform import Agent, tool, LLMConfig

@tool(description="Get weather for a city")
async def get_weather(city: str) -> str:
    return f"Sunny in {city}"

agent = Agent.create(
    name="weather",
    instructions="You help users check the weather.",
    tools=[get_weather],
    llm=LLMConfig(provider="anthropic", model="claude-sonnet-4-6"),
)

response = await agent.run("What's the weather in Tokyo?")
print(response.content)
```

## Architecture

```
packages/core          # Agent framework (Pillar C)
packages/agents        # Pre-built SMB agents (Pillar A)
packages/compliance    # Compliance engine (Pillar B)
packages/integrations  # Shopify, Stripe, GitHub, AWS, ...
apps/api               # FastAPI REST + WebSocket server
apps/dashboard         # Next.js 14 web dashboard
apps/docs              # Mintlify documentation
sdks/typescript        # TypeScript SDK
```

## Stack

- **Runtime**: Python 3.11+, [uv](https://docs.astral.sh/uv/)
- **API**: FastAPI, PostgreSQL 16 + pgvector, Redis, ARQ
- **Dashboard**: Next.js 14, TypeScript
- **Primary LLM**: Anthropic Claude
- **License**: Apache 2.0

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). By submitting a pull request you agree to the [Developer Certificate of Origin](https://developercertificate.org/).

## License

Apache 2.0 — see [LICENSE](LICENSE).
