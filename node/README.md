# Stigmem Reference Node

Single-host reference implementation of the Stigmem protocol. The modular protocol
specs live under [`../spec/specs/`](../spec/specs/), with the generated protocol
composition at [`../spec/PROTOCOL.md`](../spec/PROTOCOL.md).

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
| `POST /v1/facts` | Assert a fact (`Spec-03-HTTP-API`) |
| `GET /v1/facts` | Query facts (`Spec-03-HTTP-API`) |
| `GET /.well-known/stigmem` | Node metadata (`Spec-03-HTTP-API`) |
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
