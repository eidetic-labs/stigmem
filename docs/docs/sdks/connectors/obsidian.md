---
title: Obsidian / Markdown Vault
sidebar_label: Obsidian Vault
audience: Integrator
---

# Obsidian Vault Adapter

The `stigmem-obsidian` CLI/daemon provides **bidirectional sync** between a
stigmem node and any Obsidian (or generic markdown) vault directory. It runs
outside the Obsidian process, which means it also works with Logseq, Dendron,
and plain-folder vaults — the difference is config only.

## Architecture

```
┌──────────────────────────────┐        ┌──────────────────┐
│  Markdown vault on disk       │        │  Stigmem node     │
│                              │        │                  │
│  note.md ──parse──► facts ───┼──POST──► /v1/facts        │
│  note.md ◄─write─── facts ◄──┼──GET───  /v1/facts        │
│  (## Stigmem section)        │        │                  │
└──────────────────────────────┘        └──────────────────┘
         stigmem-obsidian sync / watch
```

**Vault → stigmem** (push):

| Vault content | Stigmem fact relation |
|---|---|
| Filename (no ext) | `note:title` (fallback) |
| YAML frontmatter `title:` | `note:title` |
| YAML frontmatter `tags:` | `note:tags` |
| YAML frontmatter `key:` | `note:<key>` |
| `[[wikilink]]` | `references` (configurable) |
| `key:: value` (Dataview) | `dataview:<key>` |
| File hash | `note:content_hash` (rename tracking) |

**Stigmem → vault** (pull): Facts with a source other than the current vault
file are written into a managed `## Stigmem` section at the bottom of the note.
New entities that exist only in stigmem create notes inside the configured
`sync_folder` (default: `Stigmem/`).

**Provenance**: All pushed facts carry `source = obsidian://vault/<rel-path>`.
Pulled facts retain their original `source` (e.g. `stigmem://another-agent`).

## Installation

```bash
pip install stigmem-obsidian
# or
uv add stigmem-obsidian
```

## Quick start

1. Add `.stigmem-sync.toml` to your vault root:

```toml
node_url = "http://localhost:8765"
vault_name = "my-vault"
scope = "local"
```

2. Run a one-shot sync:

```bash
stigmem-obsidian sync /path/to/vault
```

3. Start the watch daemon (syncs on every file change + periodic pull):

```bash
stigmem-obsidian watch /path/to/vault
```

4. Preview changes without writing anything:

```bash
stigmem-obsidian dry-run /path/to/vault
```

## Configuration reference (`.stigmem-sync.toml`)

```toml
# Required
node_url = "https://stigmem.example.com"

# Optional identity
vault_name  = "my-vault"         # used in log messages; default "vault"
api_key     = "sk-..."           # omit if node has no auth

# Sync scope
scope = "local"                  # "local" | "team" | "company" | "public"

# Paths to skip (glob patterns, vault-relative)
ignored_paths = [
  ".obsidian/**",
  "templates/**",
  "*.tmp",
]

# Where stigmem-only entities are created as new notes
sync_folder = "Stigmem"

# Conflict resolution policy
# "comment"       — surface conflict as %%stigmem-conflict: ..%% comment (default)
# "stigmem_wins"  — stigmem value overwrites vault section
# "vault_wins"    — conflicting stigmem facts are ignored
conflict_policy = "comment"

# Relation used for [[wikilinks]] (default "references")
wikilink_relation = "references"

# Per-folder scope overrides (evaluated in order, first match wins)
[[folder_scope]]
folder = "journals"
scope  = "local"

[[folder_scope]]
folder = "shared"
scope  = "company"

# Daemon poll interval for periodic pulls (seconds)
watch_interval = 2.0
```

## Conflict semantics

A conflict occurs when the same `(entity, relation)` pair has different values
in the vault's `## Stigmem` section and in the stigmem node (from a different
source).

| `conflict_policy` | Behaviour |
|---|---|
| `comment` (default) | Appends `%%stigmem-conflict: relation=… vault=… stigmem=…%%` comment to the note |
| `stigmem_wins` | Stigmem value written unconditionally; no comment |
| `vault_wins` | Conflicting stigmem fact discarded; vault content unchanged |

To resolve a `comment`-policy conflict manually: edit the vault note to the
correct value and delete the `%%stigmem-conflict:%%` line, then run a sync.

## Entity URIs

Each note gets a stable entity URI derived from its vault-relative path:

```
obsidian://vault/<vault-relative-path-without-extension>
```

Examples:
- `notes/Alice.md` → `obsidian://vault/notes/Alice`
- `journals/2026-05-04.md` → `obsidian://vault/journals/2026-05-04`

Renames are tracked via the `note:content_hash` fact: if the hash matches an
existing entity but the path changed, a new fact is asserted under the new URI
and the old one retracted automatically on the next sync.

## Vault type compatibility

| Vault type | Notes |
|---|---|
| Obsidian | Full support. `[[wikilinks]]`, YAML frontmatter, Dataview fields. |
| Logseq | Works. Daily notes in `journals/`. Bullet-journal body parsed for wikilinks and Dataview fields. |
| Dendron | Works. Hierarchical filenames (`people.alice.md`) produce nested entity URIs. |
| Plain folder | Works. Any directory of `.md` files syncs without special configuration. |

## CLI reference

### `stigmem-obsidian sync [VAULT]`

One-shot bidirectional sync. Exits non-zero if any errors occur.

```
Options:
  -c, --config PATH   Path to .stigmem-sync.toml (default: auto-discover)
  --dry-run           Preview without writing
  -v, --verbose       Debug logging
```

### `stigmem-obsidian watch [VAULT]`

Long-running daemon. Runs an initial full sync, then watches for file changes
and runs `sync_note()` on each changed file. Also runs a periodic pull from
stigmem every `watch_interval` seconds.

```
Options:
  -c, --config PATH
  --interval FLOAT    Override watch_interval from config
  -v, --verbose
```

### `stigmem-obsidian dry-run [VAULT]`

Shorthand for `sync --dry-run`. Prints counts of what would change.

## Security notes

- The adapter reads vault files and sends fact values to the configured
  `node_url`. Review your `node_url` before enabling on a shared machine.
- Use `ignored_paths` to exclude files with personal or sensitive content.
- Set `api_key` in `.stigmem-sync.toml` for nodes that require authentication.
  Keep this file out of version control (add to `.gitignore`).
