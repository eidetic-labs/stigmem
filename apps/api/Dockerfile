FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PYTHON=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Copy workspace files first for layer caching
COPY pyproject.toml .python-version ./
COPY packages/core/pyproject.toml packages/core/
COPY packages/agents/pyproject.toml packages/agents/
COPY packages/compliance/pyproject.toml packages/compliance/
COPY apps/api/pyproject.toml apps/api/

# Install dependencies (no dev deps in prod)
RUN uv sync --frozen --no-dev

# Copy source
COPY packages/ packages/
COPY apps/api/ apps/api/

WORKDIR /app/apps/api

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
