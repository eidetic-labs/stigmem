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

## CORS

The Stigmem node ships with CORS disabled by default. Enable it only for the
deployment shape you operate.

### Local development (any localhost port)

```bash
STIGMEM_CORS_DEV_LOCALHOST=1
```

Accepts any `Origin` matching
`^https?://(localhost|127\.0\.0\.1)(:\d+)?$`. Use this when the UI and API run
on separate, dynamically chosen localhost ports.

### Production with a known UI origin

```bash
STIGMEM_CORS_ALLOWED_ORIGINS=https://stigmem-ui.example.com
```

### Production with multiple UI origins

```bash
STIGMEM_CORS_ALLOWED_ORIGINS=https://a.example.com,https://b.example.com
```

### Self-managed regex (advanced)

```bash
STIGMEM_CORS_ALLOWED_ORIGIN_REGEX=^https://[a-z0-9-]+\.example\.com$
```

### Credentials

`STIGMEM_CORS_ALLOW_CREDENTIALS` defaults to `true` and controls whether
browsers may send cookies or `Authorization` headers cross-origin. Set it to
`false` only when the deployment does not use credentialed browser requests.

### Security note

Do not combine `STIGMEM_CORS_DEV_LOCALHOST=1` with a production deployment. The
dev-localhost regex is intentionally permissive and must only run on
maintainer-controlled machines.

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
