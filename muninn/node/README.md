# Muninn Reference Node

Single-host Muninn node implementing [spec v0.3](../spec/muninn-spec-v0.3-draft.md). Phase 2 reference implementation.

## Quick start

```bash
# install
pip install .

# run (auth disabled, local db)
muninn-node

# run with auth
MUNINN_AUTH_REQUIRED=true MUNINN_DB_PATH=./data/muninn.db muninn-node
```

Default port: **8765**. Override with `MUNINN_PORT`.

## Configuration

All settings via environment variables (prefix `MUNINN_`):

| Variable              | Default                  | Description |
|-----------------------|--------------------------|-------------|
| `MUNINN_DB_PATH`      | `muninn.db`              | SQLite file path |
| `MUNINN_HOST`         | `0.0.0.0`                | Bind host |
| `MUNINN_PORT`         | `8765`                   | Bind port |
| `MUNINN_NODE_URL`     | `http://localhost:8765`  | Canonical URL for `/.well-known/muninn` |
| `MUNINN_AUTH_REQUIRED`| `false`                  | Enforce API-key auth |
| `MUNINN_LOG_LEVEL`    | `info`                   | uvicorn log level |

## API

| Route | Description |
|-------|-------------|
| `POST /v1/facts` | Assert a fact (spec §5.1) |
| `GET /v1/facts` | Query facts (spec §5.2) |
| `GET /.well-known/muninn` | Node metadata (spec §5.3) |
| `GET /healthz` | Health check |
| `GET /docs` | OpenAPI UI |

## Running tests

```bash
cd muninn/node
pip install ".[dev]"
pytest
```

## Docker

```bash
docker build -t muninn-node .
docker run -p 8765:8765 -v $(pwd)/data:/data muninn-node
```
