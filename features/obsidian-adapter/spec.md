# Obsidian Adapter Spec

## Scope

The Obsidian adapter maps markdown vault content to Stigmem facts and writes
selected Stigmem facts back into managed markdown sections. It does not own the
node API, Obsidian plugin platform, or markdown tools such as Logseq and
Dendron.

This feature covers:

- the `stigmem-obsidian` Python CLI/daemon;
- the Obsidian plugin implementation;
- vault-to-node parsing for frontmatter, wikilinks, Dataview fields, file
  hashes, titles, and source URIs;
- node-to-vault rendering into managed `## Stigmem` sections;
- configurable ignored paths, sync folder, scope, conflict policy, and
  wikilink relation;
- the shared entity URI and source URI convention.

## Entity and Source URI Contract

| Item | Format |
| --- | --- |
| Entity URI | `obsidian://vault/<vault-relative-path-without-extension>` |
| Source URI | `obsidian://vault/<vault-relative-path>` |

Both the CLI/daemon and plugin use the same URI conventions so a vault can use
either surface without changing stored Stigmem entities. Running both
simultaneously for the same vault is not recommended.

## Sync Behavior

Vault-to-node sync asserts:

- `note:title` from filename or frontmatter;
- `note:<key>` for supported frontmatter fields;
- `references` for wikilinks unless configured otherwise;
- `dataview:<key>` for Dataview inline fields;
- `note:content_hash` for rename tracking.

Node-to-vault sync writes facts from other sources into a managed `## Stigmem`
section. Conflicts are handled through `comment`, `stigmem_wins`, or
`vault_wins` policy.

## Non-Goals

- Treating vault content as authoritative for all node state.
- Guaranteeing safe storage for API keys in every local sync provider.
- Shipping the adapter as part of the stable default surface.
- Defining new node API semantics.

## Canonical Spec Assignment

There is no Spec-X assignment for the Obsidian adapter. It is an external
adapter around markdown-vault sync behavior, not a standalone Stigmem protocol
module.
