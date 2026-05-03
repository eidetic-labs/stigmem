# Stigmem Reference Node

Single-host Stigmem node implementing [spec v0.8-draft](../spec/stigmem-spec-v0.8-draft.md). Reference implementation.

## Quick start

```bash
# install
pip install .

# run (auth disabled, local db)
stigmem-node

# run with auth
STIGMEM_AUTH_REQUIRED=true STIGMEM_DB_PATH=./data/stigmem.db stigmem-node
```

Default port: **8765**. Override with `STIGMEM_PORT`.

## Configuration

All settings via environment variables (prefix `STIGMEM_`):

| Variable              | Default                  | Description |
|-----------------------|--------------------------|-------------|
| `STIGMEM_DB_PATH`      | `stigmem.db`              | SQLite file path |
| `STIGMEM_HOST`         | `0.0.0.0`                | Bind host |
| `STIGMEM_PORT`         | `8765`                   | Bind port |
| `STIGMEM_NODE_URL`     | `http://localhost:8765`  | Canonical URL for `/.well-known/stigmem` |
| `STIGMEM_AUTH_REQUIRED`| `false`                  | Enforce API-key auth |
| `STIGMEM_LOG_LEVEL`    | `info`                   | uvicorn log level |

## API

| Route | Description |
|-------|-------------|
| `POST /v1/facts` | Assert a fact (spec §5.1) |
| `GET /v1/facts` | Query facts (spec §5.2) |
| `GET /.well-known/stigmem` | Node metadata (spec §5.3) |
| `GET /healthz` | Health check |
| `GET /docs` | OpenAPI UI |

## Running tests

```bash
cd stigmem/node
pip install ".[dev]"
pytest
```

## Docker

```bash
docker build -t stigmem-node .
docker run -p 8765:8765 -v $(pwd)/data:/data stigmem-node
```
