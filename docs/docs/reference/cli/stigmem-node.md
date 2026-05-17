---
title: "stigmem-node"
sidebar_label: "stigmem-node"
sidebar_position: 2
description: "CLI reference for the stigmem-node command — starts the Stigmem HTTP server."
audience: Operator
---


# stigmem-node CLI


Auto-generated from `stigmem-node --help`. Regenerate with `make gen-cli-docs`.


The `stigmem-node` command starts the Stigmem reference node HTTP server.


## Usage


```

stigmem-node [--host HOST] [--port PORT]

```


## Environment Variables


| Variable | Default | Description |

|----------|---------|-------------|

| `STIGMEM_HOST` | `0.0.0.0` | Bind address |

| `STIGMEM_PORT` | `8765` | Listen port |

| `STIGMEM_DB_PATH` | `stigmem.db` | SQLite database path |

| `STIGMEM_AUTH_REQUIRED` | `false` | Require API key authentication |

| `STIGMEM_SOURCE_ATTESTATION_MODE` | `off` | Legacy source-attestation mode field; runtime enforcement is plugin-gated |

| `STIGMEM_FEDERATION_PULL_INTERVAL` | `30` | Seconds between federation pull cycles |

| `STIGMEM_EMBED_DIMENSIONS` | `768` | Embedding dimensions (Matryoshka truncation) |

| `STIGMEM_CARD_MAX_AGE_S` | `86400` | Memory card staleness threshold (seconds) |
