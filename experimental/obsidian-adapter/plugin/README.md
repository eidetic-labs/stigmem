# Stigmem — Obsidian Plugin

Real-time bidirectional sync between your Obsidian vault and a
[stigmem](https://docs.stigmem.dev) knowledge-graph node. No separate daemon
process — the plugin runs entirely inside Obsidian.

## Features

| Feature | Details |
|---|---|
| **Live vault sync** | Notes push facts to stigmem on save; stigmem facts appear in a managed `## Stigmem` section in each note |
| **Recall sidebar** | Graph-ranked neighbors of the active note, powered by the stigmem `recall` API |
| **Command palette** | `Recall related memories`, `Sync vault now`, `Open stigmem garden` |
| **Settings tab** | Node URL, API key, scope, sync folder, conflict policy, per-folder scope overrides |
| **Conflict policy** | `comment` (default), `stigmem_wins`, or `vault_wins` — matches the CLI/daemon adapter |

## Requirements

- Obsidian ≥ 1.4.0
- A running stigmem node (see [docs.stigmem.dev](https://docs.stigmem.dev/install))

## Installation

### From the Obsidian community plugin registry (once approved)

1. Open **Settings → Community plugins → Browse**
2. Search for **Stigmem**
3. Click **Install**, then **Enable**

### Manual install (for testing or before registry approval)

1. Download `main.js`, `manifest.json`, and `styles.css` from the latest release.
2. Copy them into `<vault>/.obsidian/plugins/stigmem/`.
3. Reload Obsidian and enable the plugin under **Settings → Community plugins**.

## Quick start

1. Start your stigmem node (`stigmem-node serve` or equivalent — see the
   [deploy guide](https://docs.stigmem.dev/install/deploy-recipes)).
2. In Obsidian, go to **Settings → Stigmem**.
3. Set **Node URL** (e.g. `http://localhost:8765`) and optionally your **API key**.
4. Click **Test connection** to confirm connectivity.
5. Open a note and run **Sync vault now** from the command palette.
6. Click the brain icon in the ribbon (or run **Open Stigmem recall**) to open
   the recall sidebar.

## How sync works

Each markdown note gets a stable entity URI from its vault-relative path:

```
notes/Alice.md  →  obsidian://vault/notes/Alice
```

**Vault → stigmem (push)** — on every save, the plugin asserts:

| Vault content | Stigmem relation |
|---|---|
| Filename (no ext) | `note:title` |
| YAML frontmatter `title:` | `note:title` |
| YAML frontmatter `key:` | `note:<key>` |
| `[[wikilink]]` | `references` (configurable) |
| `key:: value` (Dataview) | `dataview:<key>` |
| File hash | `note:content_hash` |

**Stigmem → vault (pull)** — facts from other sources are written into a managed
`## Stigmem` section at the bottom of the note. This section is auto-refreshed
on every sync; manual edits inside it will be overwritten.

**Conflict policy** — when the same `(entity, relation)` has different values
in both sides:

| Policy | Behaviour |
|---|---|
| `comment` (default) | Appends `%%stigmem-conflict: …%%` comment to the note |
| `stigmem_wins` | Stigmem value written unconditionally |
| `vault_wins` | Conflicting stigmem fact is discarded |

## Compatibility with the CLI/daemon adapter

A vault that uses this plugin and the `stigmem-obsidian` CLI/daemon adapter
interchangeably will remain consistent: both tools use the same entity-URI
convention, source-URI scheme (`obsidian://vault/<rel-path>`), and conflict-
policy semantics. Running both simultaneously is not recommended — use one or
the other per vault.

## Settings reference

| Setting | Default | Description |
|---|---|---|
| Node URL | `http://localhost:8765` | stigmem node endpoint |
| API key | _(empty)_ | Bearer token for auth-enabled nodes |
| Default scope | `local` | `local`, `team`, `company`, or `public` |
| Sync folder | `Stigmem` | Folder where stigmem-only entities are created |
| Auto-sync on save | on | Push+pull on every file save |
| Sync debounce (ms) | `1500` | Wait after last keypress before syncing |
| Ignored paths | `.obsidian/**`, `templates/**`, `*.tmp` | Glob patterns to skip |
| Conflict policy | `comment` | See table above |
| Wikilink relation | `references` | Stigmem relation for `[[wikilink]]` edges |

## Security notes

- The API key is stored in `.obsidian/plugins/stigmem/data.json`. Exclude
  `.obsidian/` from cloud sync (iCloud, Obsidian Sync) if the node is private.
- The plugin only talks to the URL you configure. Review `node_url` before
  enabling the plugin on a shared machine.
- Use **Ignored paths** to exclude files with personal or sensitive content.

## License

MIT — see [LICENSE](https://github.com/Eidetic-Labs/stigmem) for details.
