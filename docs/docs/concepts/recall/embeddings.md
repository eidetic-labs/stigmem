---
title: Embeddings
sidebar_label: Embeddings
description: Choosing an embedding model, dimensionality tradeoffs, and mixed-model safety.
audience: Integrator
---

# Embeddings

**Audience:** Node operators configuring the embedding layer.
**Spec reference:** §20.2 Vector Embeddings.

---

Stigmem stores a dense vector embedding alongside each fact at write time. These embeddings power the vector stage of the [`recall`](./) pipeline. This guide covers model selection, dimensionality tradeoffs, and safe migration between models.

## How embeddings are stored

Each fact is embedded as a composed string:

```
"{entity_display} {relation} {value_text}"
```

For example:

```
"project/api-service memory:status in progress"
```

The composed vector is written to the `vec_facts` virtual table (sqlite-vec). At recall time, the same composition is applied to the query string before ANN search. The model used for query and index **must match** — mismatched models produce silently incorrect cosine similarities.

---

## Enabling embeddings

Embeddings are **disabled by default** to keep the default install dependency-free.

```bash
STIGMEM_EMBED_ENABLED=true stigmem start
```

When disabled, the node skips the vector stage in `recall` entirely. Set the `weights` parameter to `{lexical: 0.70, vector: 0.00, graph: 0.30}` if you call `recall` on a node without embeddings.

---

## Model providers

The node supports three providers, selected via `STIGMEM_EMBED_MODEL_PROVIDER`.

### `local` — Ollama (default)

Runs the embedding model on your machine via the [Ollama](https://ollama.com) HTTP API. No data leaves your host.

```bash
# Install Ollama, then pull the model
ollama pull nomic-embed-text

# Start the node
STIGMEM_EMBED_ENABLED=true \
STIGMEM_EMBED_MODEL_PROVIDER=local \
STIGMEM_EMBED_MODEL_ID=nomic-embed-text-v1.5 \
STIGMEM_EMBED_OLLAMA_URL=http://localhost:11434 \
stigmem start
```

**Default model: `nomic-embed-text-v1.5`.** 768 dimensions, Apache-2.0 license, runs on a laptop CPU.

### `openai` — OpenAI Embeddings API

Uses OpenAI's API. Requires network access and a valid API key.

```bash
STIGMEM_EMBED_ENABLED=true \
STIGMEM_EMBED_MODEL_PROVIDER=openai \
STIGMEM_EMBED_MODEL_ID=text-embedding-3-small \
OPENAI_API_KEY=sk-... \
stigmem start
```

The env var name holding the key is configurable via `STIGMEM_EMBED_OPENAI_API_KEY_ENV` (default `OPENAI_API_KEY`). Use this when your secret manager injects under a different name.

### `stub` — Deterministic test stub

Returns deterministic fixed-dimension vectors. Not useful for production; use in CI or unit tests to avoid Ollama/OpenAI dependencies.

---

## Dimensionality

| Model | Provider | Dimensions | License | Notes |
|---|---|---|---|---|
| `nomic-embed-text-v1.5` | local | 768 | Apache-2.0 | Default; runs offline |
| `nomic-embed-text-v1` | local | 768 | Apache-2.0 | Prior version |
| `text-embedding-3-small` | openai | 1536 | Proprietary | High quality, cloud |
| `text-embedding-3-large` | openai | 3072 | Proprietary | Highest quality, higher cost |
| `text-embedding-ada-002` | openai | 1536 | Proprietary | Legacy; prefer 3-small |

`STIGMEM_EMBED_DIMENSION` must match the model's output dimension. The node validates this at startup and refuses to start if `vec_facts` was initialized with a different dimension than the configured model would produce.

:::caution Changing dimension
Changing `STIGMEM_EMBED_DIMENSION` after facts have been indexed requires a full reindex. Run:

```bash
stigmem embed reindex
```

This drops and rebuilds `vec_facts` from the fact table. Recall will be unavailable until the reindex completes. For large datasets run it during maintenance.
:::

---

## Mixed-model safety

**Never change the embedding model without reindexing.** The `vec_facts` virtual table stores raw float vectors. There is no per-fact model tag — the node assumes all stored vectors were produced by the current model. Mixing models produces silent correctness failures: cosine similarity between vectors from different embedding spaces is meaningless.

**Safe model upgrade procedure:**

1. Stop the node (or quiesce writes).
2. Change `STIGMEM_EMBED_MODEL_ID` and `STIGMEM_EMBED_DIMENSION` in your config.
3. Run `stigmem embed reindex` — this re-embeds all live facts with the new model.
4. Restart the node.

**Federation note:** when facts are replicated from a peer node, embeddings are *not* replicated — the receiving node re-embeds incoming facts with its own model. Peers may use different models; recall accuracy is only affected if the receiving node's model is a poor fit for the fact content.

---

## Decay and tombstoning

When the decay sweep retires a fact (confidence falls below `STIGMEM_DECAY_MIN_CONFIDENCE`), the corresponding `vec_facts` entry is also deleted. The tombstone threshold is configurable:

```bash
STIGMEM_EMBED_TOMBSTONE_THRESHOLD=0.1  # default
```

Facts with effective confidence below this threshold have their `vec_facts` entry removed during the next decay sweep, keeping the index size proportional to live facts.

---

## Configuration reference

| Environment variable | Default | Description |
|---|---|---|
| `STIGMEM_EMBED_ENABLED` | `false` | Enable/disable the embedding layer |
| `STIGMEM_EMBED_MODEL_PROVIDER` | `local` | `local`, `openai`, or `stub` |
| `STIGMEM_EMBED_MODEL_ID` | `nomic-embed-text-v1.5` | Model identifier passed to the provider |
| `STIGMEM_EMBED_DIMENSION` | `768` | Output dimension; must match the model |
| `STIGMEM_EMBED_OLLAMA_URL` | `http://localhost:11434` | Ollama base URL (local provider only) |
| `STIGMEM_EMBED_OPENAI_API_KEY_ENV` | `OPENAI_API_KEY` | Env var name holding the OpenAI key |
| `STIGMEM_EMBED_TOMBSTONE_THRESHOLD` | `0.1` | Confidence below which `vec_facts` entries are deleted on decay sweep |

---

## Related guides

- [Recall](./) — how embeddings are used in the recall pipeline
- [Decay](../lifecycle/decay) — confidence-based fact retirement and tombstoning
