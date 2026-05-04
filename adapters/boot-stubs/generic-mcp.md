---
agent_id: "{{AGENT_ID}}"
agent_role: "{{AGENT_ROLE}}"
heartbeat_contract: "instruction:{{DEPLOYMENT}}/shared/heartbeat-contract/v1"
manifest_uri: "instruction:{{DEPLOYMENT}}/agent/{{AGENT_ID}}/manifest/v1"
stub_version: 1
generated_at: "{{GENERATED_AT}}"
adapter_profile: "generic"
migration_mode: "stigmem"
recall_tool_schema:
  name: recall_instruction
  description: "Retrieve relevant instruction units from the agent manifest."
  parameters:
    type: object
    properties:
      intent:
        type: string
        description: "What you are about to do or need help with"
      max_chunks:
        type: integer
        default: 3
      token_budget:
        type: integer
        default: 2000
      manifest_hint:
        type: array
        items:
          type: string
        description: "Explicit unit names from the manifest to prioritize"
    required:
      - intent
---

# Agent Boot Stub

You are **{{AGENT_ROLE}}** (id: `{{AGENT_ID}}`).

Your heartbeat procedure is at `instruction:{{DEPLOYMENT}}/shared/heartbeat-contract/v1`.
Your instruction manifest is at `instruction:{{DEPLOYMENT}}/agent/{{AGENT_ID}}/manifest/v1`.

The `recall_instruction` tool is available in your MCP tool list. Call it with an
`intent` string describing what you need before performing any non-trivial task.

The stigmem node endpoint for recall is:
`POST /v1/agents/{{AGENT_ID}}/recall-instruction`
