---
id: obsidian-plugin
title: Obsidian Community Plugin
sidebar_label: Obsidian Plugin
---

# Obsidian Community Plugin

The **Stigmem Obsidian plugin** provides in-process, real-time vault ↔ stigmem
reflection. It runs entirely inside Obsidian with no separate daemon — install
it like any other community plugin and point it at your stigmem node.

> **CLI/daemon adapter**: If you prefer to run sync outside Obsidian (e.g. for
> Logseq or plain-folder vaults), see the
> [Obsidian Vault Adapter](./obsidian.md) page instead.

## Architecture

```
┌──────────────────────────────────────────────┐
│  Obsidian                                    │
│                                              │
│  Active note                                 │
│    on-save ──parse──► facts ──POST──► stigmem│
│             ◄─write── facts ◄──GET───────────│
│  (## Stigmem section auto-refreshed)         │
│                                              │
│  Recall sidebar (right panel)                │
│    active-leaf-change ──POST /v1/recall──►   │
│                        ◄── scored facts ◄────│
└──────────────────────────────────────────────┘
```

## Requirements

- Obsidian ≥ 1.4.0
- A running stigmem node. See [Deploy runbooks](../../operating/deploy-runbooks.md).

## Installation

### Community plugin registry

1. **Settings → Community plugins → Browse**
2. Search **Stigmem**
3. **Install** → **Enable**

> Registry submission is pending board approval. Use the manual method below
> in the meantime.

### Manual install

```bash
# Download the latest release assets
cd <your-vault>/.obsidian/plugins/
mkdir stigmem && cd stigmem
curl -LO https://github.com/Eidetic-Labs/stigmem/releases/latest/download/main.js
curl -LO https://github.com/Eidetic-Labs/stigmem/releases/latest/download/manifest.json
```

Reload Obsidian (**Ctrl/Cmd+R**) and enable the plugin under **Settings →
Community plugins**.

## Quick start

1. Open **Settings → Stigmem**.
2. Enter your **Node URL** (e.g. `http://localhost:8765`).
3. Enter your **API key** if the node requires authentication.
4. Click **Test connection** — you should see "Connected to stigmem node."
5. Open any note and run **Sync vault now** from the command palette (**Cmd+P**).
6. Click the 🧠 brain icon in the ribbon to open the **Recall sidebar**.

## Command palette

| Command | What it does |
|---|---|
| `Recall related memories` | Opens the recall sidebar and loads neighbors for the active note |
| `Sync vault now` | Full bidirectional sync of all vault notes |
| `Open stigmem garden` | Opens `<node_url>/garden` in your browser |

## Recall sidebar

The **Stigmem recall** sidebar pane (right panel) shows graph-ranked neighbors
of the active note. It updates automatically when you switch notes.

Results are grouped by entity and sorted by recall score. Each row shows:

```
path/to/Note
  • note:title: Alice  [92%]
  • references: obsidian://vault/projects/Loom  [78%]
  • dataview:status: active  [61%]
```

The score is the stigmem hybrid recall score (lexical + semantic + graph + recency).

## Sync semantics

### Entity URIs

Each note gets a stable entity URI from its vault-relative path (extension stripped):

| Vault file | Entity URI |
|---|---|
| `notes/Alice.md` | `obsidian://vault/notes/Alice` |
| `journals/2026-05-04.md` | `obsidian://vault/journals/2026-05-04` |

### Vault → stigmem (push)

On every file save the plugin asserts these facts:

| Vault content | Stigmem relation |
|---|---|
| Filename (no ext) | `note:title` |
| YAML frontmatter `title:` | `note:title` |
| YAML frontmatter `key:` | `note:<key>` |
| `[[wikilink]]` | `references` (configurable per **Wikilink relation** setting) |
| `key:: value` (Dataview) | `dataview:<key>` |
| File hash | `note:content_hash` |

All facts carry `source = obsidian://vault/<rel-path>`.

### Stigmem → vault (pull)

After push, the plugin queries stigmem for all facts on the entity whose source
is **not** this vault file. Those external facts are written into a managed
`## Stigmem` section at the bottom of the note.

```markdown
## Stigmem
- relation: note:summary
  value: Leads the Loom project.
  source: stigmem://another-agent
- relation: note:status
  value: active
  source: stigmem://another-agent
```

> **Do not edit the `## Stigmem` section manually.** It is auto-replaced on
> every sync. Put your own notes above it.

### Conflict policy

When the same `(entity, relation)` has different values in both the vault's
`## Stigmem` section and in stigmem (from a different source), the configured
conflict policy applies:

| Policy | Behaviour |
|---|---|
| `comment` (default) | Appends `%%stigmem-conflict: relation=… vault=… stigmem=…%%` to the note |
| `stigmem_wins` | Overwrites the vault section with the stigmem value |
| `vault_wins` | Discards the conflicting stigmem fact; vault value preserved |

To resolve a `comment`-policy conflict: edit the value in the note body (not
the `## Stigmem` section) and delete the `%%stigmem-conflict:%%` line, then
save to trigger a sync.

## Settings reference

Open **Settings → Stigmem** to configure:

| Setting | Default | Description |
|---|---|---|
| **Node URL** | `http://localhost:8765` | stigmem node endpoint |
| **API key** | _(empty)_ | Bearer token for auth-enabled nodes |
| **Test connection** | — | Ping button to verify connectivity |
| **Default scope** | `local` | `local` \| `team` \| `company` \| `public` |
| **Sync folder** | `Stigmem` | Folder where stigmem-only entities are created as new notes |
| **Auto-sync on save** | on | Sync the current note when you save |
| **Sync debounce (ms)** | `1500` | Wait time after last file-change event |
| **Ignored paths** | `.obsidian/**`, `templates/**`, `*.tmp` | Glob patterns to skip |
| **Conflict policy** | `comment` | See table above |
| **Wikilink relation** | `references` | Stigmem relation used for `[[wikilink]]` edges |

## Security

- The API key is stored in `.obsidian/plugins/stigmem/data.json` (local to your
  device). **Do not sync `.obsidian/` to a shared cloud drive** if the node is
  private.
- All requests go only to the URL you configure. Review `node_url` before
  enabling on a shared machine.
- Use **Ignored paths** to exclude files with personal or sensitive content.

## Compatibility with the CLI/daemon adapter

A vault can be used with either the Obsidian plugin **or** the
[`stigmem-obsidian` CLI adapter](./obsidian.md) — **not both simultaneously**.
Both tools share:

- The same `obsidian://vault/<rel-path>` entity URI scheme
- The same source URI (`obsidian://vault/<rel-path>`)
- The same conflict-policy semantics and `## Stigmem` section format

Switching between them does not corrupt the stigmem node; the next sync simply
picks up where the other left off.

## Troubleshooting

| Symptom | Fix |
|---|---|
| "Could not reach stigmem node" | Check that the node is running and the URL is correct. Try `curl http://localhost:8765/v1/health`. |
| `## Stigmem` section is empty | Run **Sync vault now**. If the node has no facts for the entity, the section will remain empty. |
| Facts not appearing in the sidebar | The node URL must be reachable from Obsidian. CORS is not an issue for desktop builds, but check if a firewall is blocking the port. |
| Conflict comments accumulating | Edit the note to resolve conflicts manually and run a sync. Set `vault_wins` or `stigmem_wins` to suppress future conflicts. |
