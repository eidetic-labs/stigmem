# stigmem-obsidian

Bidirectional sync between a [Stigmem](https://docs.stigmem.dev) node and an
Obsidian / Logseq / Dendron / plain-folder markdown vault.

```bash
pip install stigmem-obsidian

# One-shot sync
stigmem-obsidian sync /path/to/vault

# Watch daemon
stigmem-obsidian watch /path/to/vault

# Dry run
stigmem-obsidian dry-run /path/to/vault
```

Add `.stigmem-sync.toml` to your vault root:

```toml
node_url = "http://localhost:8765"
scope    = "local"
```

Full documentation: https://docs.stigmem.dev/en/latest/docs/guides/connectors/obsidian

## License

Apache-2.0 — see [LICENSE](../../LICENSE).
