FROM python:3.12-slim AS base
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

FROM base AS builder-base
COPY pyproject.toml uv.lock ./
COPY packages/core/pyproject.toml packages/core/
COPY packages/api/pyproject.toml packages/api/
COPY packages/agents/academictransfer-discovery/pyproject.toml packages/agents/academictransfer-discovery/
COPY packages/agents/academictransfer-sourcing/pyproject.toml packages/agents/academictransfer-sourcing/
COPY packages/agents/euraxess-discovery/pyproject.toml packages/agents/euraxess-discovery/
COPY packages/agents/euraxess-sourcing/pyproject.toml packages/agents/euraxess-sourcing/
COPY packages/agents/lang-detection/pyproject.toml packages/agents/lang-detection/
COPY packages/agents/refinement/pyproject.toml packages/agents/refinement/
COPY packages/agents/translation/pyproject.toml packages/agents/translation/
COPY packages/agents/cv-parsing/pyproject.toml packages/agents/cv-parsing/
COPY packages/agents/matching/pyproject.toml packages/agents/matching/

RUN echo 'find /app/.venv -type d -name "tests" -exec rm -rf {} + && \
    find /app/.venv -type d -name "__pycache__" -exec rm -rf {} + && \
    find /app/.venv -name "*.pyc" -delete' > /app/prune.sh && chmod +x /app/prune.sh

FROM builder-base AS builder-api
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-workspace --no-dev --package api \
    --package academictransfer-discovery --package academictransfer-sourcing \
    --package euraxess-discovery --package euraxess-sourcing && \
    sh /app/prune.sh

FROM builder-base AS builder-lang-detection
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-workspace --no-dev --package lang-detection && \
    sh /app/prune.sh

FROM builder-base AS builder-refinement
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-workspace --no-dev --package refinement && \
    sh /app/prune.sh

FROM builder-base AS builder-translation
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-workspace --no-dev --package translation && \
    sh /app/prune.sh

FROM builder-base AS builder-matching
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-workspace --no-dev --package matching && \
    sh /app/prune.sh

FROM builder-base AS builder-cv-parsing
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-workspace --no-dev --no-cache --package cv-parsing && \
    sh /app/prune.sh

FROM base AS slim
COPY --from=builder-api /app/.venv /app/.venv
COPY . .
RUN uv sync --frozen --no-dev --package api \
    --package academictransfer-discovery --package academictransfer-sourcing \
    --package euraxess-discovery --package euraxess-sourcing
CMD ["uv", "run", "--package", "api", "fastapi", "run", "packages/api/src/api/main.py", "--host", "0.0.0.0", "--port", "8000"]

FROM base AS lang-detection
COPY --from=builder-lang-detection /app/.venv /app/.venv
COPY . .
RUN uv sync --frozen --no-dev --package lang-detection

FROM base AS refinement
COPY --from=builder-refinement /app/.venv /app/.venv
COPY . .
RUN uv sync --frozen --no-dev --package refinement

FROM base AS translation
COPY --from=builder-translation /app/.venv /app/.venv
COPY . .
RUN uv sync --frozen --no-dev --package translation

FROM base AS matching
COPY --from=builder-matching /app/.venv /app/.venv
COPY . .
RUN uv sync --frozen --no-dev --package matching

FROM base AS cv-parsing
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libglib2.0-0 \
    libgl1 \
    libxcb1 \
    libxext6 \
    libxrender1 \
    libsm6 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder-cv-parsing /app/.venv /app/.venv
COPY . .
RUN uv sync --frozen --no-dev --package cv-parsing
