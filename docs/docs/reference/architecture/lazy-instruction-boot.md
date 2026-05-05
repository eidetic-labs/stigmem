---
title: "Lazy Instruction Boot"
sidebar_label: "Lazy Instruction Boot"
sidebar_position: 4
description: "Architecture diagram of the lazy instruction discovery system — boot stub, instruction manifest, and recall_instruction tool flow."
audience: Spec
---

# Lazy Instruction Boot

*Audience: engineers building agent runtimes or adapters that use Stigmem's lazy instruction discovery (spec §21).*

Instead of preloading every instruction document at startup, agents discover and load instructions on demand. The system has three runtime components — a **boot stub**, an **instruction manifest**, and the **`recall_instruction` tool** — plus an off-path **discovery audit** for retrieval-quality evaluation.

## Boot sequence

```mermaid
sequenceDiagram
    participant Runtime as Agent Runtime<br/>(Adapter)
    participant Node as Stigmem Node
    participant Agent as Agent LLM

    Note over Runtime,Agent: Heartbeat start

    Runtime->>Node: GET /v1/agents/{id}/boot-stub<br/>?profile=paperclip-claude-code
    Node-->>Runtime: Boot stub (YAML frontmatter +<br/>markdown ≤ 500 tokens)

    Runtime->>Agent: Inject boot stub +<br/>adapter-specific tools

    Note over Agent: Agent knows: agent_id,<br/>role, manifest_uri,<br/>recall_instruction schema

    Agent->>Agent: Read task from heartbeat

    alt Task matches required_by_task_types
        Agent->>Node: recall_instruction(intent)<br/>with manifest_hint, task_type
        Node->>Node: Recall from instruction: scope<br/>(§20 pipeline restricted to<br/>instruction facts)
        Node-->>Agent: Ranked instruction chunks<br/>≤ token_budget
    else Agent decides it needs instructions
        Agent->>Node: recall_instruction(intent)<br/>with natural-language intent
        Node-->>Agent: Relevant instruction chunks
    end

    Agent->>Agent: Execute task with<br/>loaded instructions
```

## Component architecture

```mermaid
graph TB
    subgraph BootStub["Boot Stub (§21.1)"]
        BS_ID["agent_id"]
        BS_Role["agent_role"]
        BS_HC["heartbeat_contract URI"]
        BS_Manifest["manifest_uri"]
        BS_Schema["recall_tool_schema"]
    end

    subgraph Manifest["Instruction Manifest (§21.2)"]
        M_Units["Instruction units\nid, summary,\nrequired_by_task_types,\nguarantee_load"]
    end

    subgraph RecallTool["recall_instruction (§21.3)"]
        RT_Intent["intent (natural language)"]
        RT_Hint["manifest_hint (unit ids)"]
        RT_Budget["token_budget"]
    end

    subgraph Storage["Stigmem Storage"]
        Facts[("instruction: scope facts\nembedded instruction units")]
        Audit[("discovery_audit table\nevery invocation logged")]
    end

    BootStub -- "manifest_uri\npoints to" --> Manifest
    BootStub -- "recall_tool_schema\nenables" --> RecallTool
    Manifest -- "describes available\nunits for" --> RecallTool
    RecallTool -- "§20 recall pipeline\nrestricted to instruction: scope" --> Facts
    RecallTool -- "audit record\n(best-effort)" --> Audit
```

## Boot stub structure

The boot stub is a markdown document with YAML frontmatter:

```yaml
---
agent_id: "8e0ed057-bcd8-4f8f-92ee-c046c55b64e9"
agent_role: "CTO"
heartbeat_contract: "instruction:acme/heartbeat-contract/v1"
manifest_uri: "instruction:acme/agent/cto/manifest/v1"
stub_version: 1
adapter_profile: "paperclip-claude-code"
---

# Agent Boot Stub

You are **CTO** (id: `8e0ed057-...`).
Call `recall_instruction(intent)` to load relevant sections.
```

## Instruction load strategies

| Strategy | When | How |
|----------|------|-----|
| Task-type preload | Task matches a unit's `required_by_task_types` | Deterministically loaded at heartbeat start before agent sees the task |
| Guarantee load | Unit has `guarantee_load: true` | Always appended to every `recall_instruction` response (max 5 per agent) |
| On-demand recall | Agent decides it needs context | Agent calls `recall_instruction` with natural-language intent |
| Boot stub embedding | Rule is always applicable | Embedded directly in boot stub body (security constraints, escalation thresholds) |
