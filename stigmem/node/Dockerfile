FROM python:3.12-slim

WORKDIR /app

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

COPY pyproject.toml .
COPY migrations/ migrations/
COPY src/ src/

RUN uv pip install --system --no-cache .

ENV STIGMEM_DB_PATH=/data/stigmem.db
ENV STIGMEM_HOST=0.0.0.0
ENV STIGMEM_PORT=8765

VOLUME ["/data"]
EXPOSE 8765

CMD ["stigmem-node"]
