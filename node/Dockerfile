# ── Build stage ───────────────────────────────────────────────────────────────
# Requires repo root as build context.
# docker build -f node/Dockerfile -t stigmem-node .
# See deploy/ for Compose, Helm, and Fly recipes.
FROM python:3.11-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /build

COPY node/pyproject.toml pyproject.toml
COPY node/migrations/ migrations/
COPY node/src/ src/

RUN uv pip install --system --no-cache .

# ── Runtime stage ─────────────────────────────────────────────────────────────
# Minimal Python slim image — no build tools, no uv, no pip invocations.
# Non-root UID 65532 (matches gcr.io/distroless:nonroot convention).
# Read-only root filesystem and capability drops are enforced at runtime
# via the Compose / Helm / Fly recipes (see deploy/).
FROM python:3.11-slim-bookworm

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin/stigmem /usr/local/bin/stigmem
COPY --from=builder /usr/local/bin/stigmem-node /usr/local/bin/stigmem-node

# Place migrations at the path db.py resolves to for a system-installed package:
#   Path(__file__).parent.parent.parent / "migrations"
# where __file__ = /usr/local/lib/python3.11/site-packages/stigmem_node/db.py
# → .parent × 3 = /usr/local/lib/python3.11  →  /usr/local/lib/python3.11/migrations
COPY --from=builder /build/migrations /usr/local/lib/python3.11/migrations

# Non-root user — create before switching so /data is owned correctly.
RUN groupadd -r -g 65532 stigmem \
 && useradd -r -u 65532 -g 65532 -d /nonexistent -s /sbin/nologin stigmem \
 && mkdir -p /data && chown 65532:65532 /data

ENV STIGMEM_DB_PATH=/data/stigmem.db
ENV STIGMEM_HOST=0.0.0.0
ENV STIGMEM_PORT=8765
# Prevent .pyc writes; required when root filesystem is read-only.
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

USER 65532:65532

VOLUME ["/data"]
EXPOSE 8765

CMD ["stigmem-node"]
