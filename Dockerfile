# ── Build stage ──────────────────────────────────────────────────────────────
# Uses UV to install all Python dependencies into a staging layer so the final
# image contains only the installed packages and app source, not the build tools.
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install UV package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency manifests first for better layer caching
COPY . .
#COPY pyproject.toml uv.lock ./

# Install production dependencies into the project's virtual environment.
# --frozen: use the lock file exactly as committed
# --no-dev: skip test/lint tooling
RUN uv sync --frozen --no-dev

# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the installed virtual environment from the builder stage
COPY --from=builder /app/.venv /app/.venv

# Copy application source code
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY scripts/ ./scripts/

# Make the virtual environment the first Python interpreter on PATH
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"

# Cloud Run injects PORT; default to 8080 for local container testing
ENV PORT=8080

# Run with gunicorn.
# --workers 2: enough for Cloud Run single-instance; adjust via GUNICORN_WORKERS
# --timeout 120: generous timeout for cold-start AI model calls
# --bind: listen on all interfaces at the injected PORT
CMD gunicorn \
        --bind "0.0.0.0:${PORT}" \
        --workers "${GUNICORN_WORKERS:-2}" \
        --timeout 120 \
        --access-logfile - \
        --error-logfile - \
        "juntos:create_app()"
