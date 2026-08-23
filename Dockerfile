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
COPY packages/agents/abg-discovery/pyproject.toml packages/agents/abg-discovery/
COPY packages/agents/abg-sourcing/pyproject.toml packages/agents/abg-sourcing/
COPY packages/agents/naturecareers-discovery/pyproject.toml packages/agents/naturecareers-discovery/
COPY packages/agents/naturecareers-sourcing/pyproject.toml packages/agents/naturecareers-sourcing/
COPY packages/agents/researchgate-discovery/pyproject.toml packages/agents/researchgate-discovery/
COPY packages/agents/researchgate-sourcing/pyproject.toml packages/agents/researchgate-sourcing/
COPY packages/agents/eurosciencejobs-discovery/pyproject.toml packages/agents/eurosciencejobs-discovery/
COPY packages/agents/eurosciencejobs-sourcing/pyproject.toml packages/agents/eurosciencejobs-sourcing/
COPY packages/agents/lang-detection/pyproject.toml packages/agents/lang-detection/
COPY packages/agents/refinement/pyproject.toml packages/agents/refinement/
COPY packages/agents/translation/pyproject.toml packages/agents/translation/
COPY packages/agents/cv-parsing/pyproject.toml packages/agents/cv-parsing/
COPY packages/agents/matching/pyproject.toml packages/agents/matching/
COPY packages/agents/embedding-worker/pyproject.toml packages/agents/embedding-worker/
COPY packages/agents/telegram-bot/pyproject.toml packages/agents/telegram-bot/

RUN echo 'find /app/.venv -type d -name "tests" -exec rm -rf {} + && \
    find /app/.venv -type d -name "__pycache__" -exec rm -rf {} + && \
    find /app/.venv -name "*.pyc" -delete' > /app/prune.sh && chmod +x /app/prune.sh

FROM builder-base AS builder-api
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-workspace --no-dev --package api \
    --package academictransfer-discovery --package academictransfer-sourcing \
    --package euraxess-discovery --package euraxess-sourcing \
    --package abg-discovery --package abg-sourcing \
    --package naturecareers-discovery --package naturecareers-sourcing \
    --package researchgate-discovery --package researchgate-sourcing \
    --package eurosciencejobs-discovery --package eurosciencejobs-sourcing && \
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

FROM builder-base AS builder-embedding
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-workspace --no-dev --package embedding-worker && \
    sh /app/prune.sh

FROM builder-base AS builder-cv-parsing
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-workspace --no-dev --no-cache --package cv-parsing && \
    sh /app/prune.sh

FROM builder-base AS builder-telegram-bot
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-workspace --no-dev --package telegram-bot && \
    sh /app/prune.sh

# API Gateway Stage
FROM base AS academix-gateway-api
COPY --from=builder-api /app/.venv /app/.venv
COPY . .
RUN uv sync --frozen --no-dev --package api \
    --package academictransfer-discovery --package academictransfer-sourcing \
    --package euraxess-discovery --package euraxess-sourcing \
    --package abg-discovery --package abg-sourcing \
    --package naturecareers-discovery --package naturecareers-sourcing \
    --package researchgate-discovery --package researchgate-sourcing \
    --package eurosciencejobs-discovery --package eurosciencejobs-sourcing
CMD ["uv", "run", "--package", "api", "fastapi", "run", "packages/api/src/api/main.py", "--host", "0.0.0.0", "--port", "8000"]

FROM academix-gateway-api AS slim

# Core Worker Stages
FROM base AS academix-lang-detection-worker
COPY --from=builder-lang-detection /app/.venv /app/.venv
COPY . .
RUN uv sync --frozen --no-dev --package lang-detection
CMD ["uv", "run", "--package", "lang-detection", "python", "-m", "agent_lang_detection.main"]

FROM academix-lang-detection-worker AS lang-detection

FROM base AS academix-refinement-worker
COPY --from=builder-refinement /app/.venv /app/.venv
COPY . .
RUN uv sync --frozen --no-dev --package refinement
CMD ["uv", "run", "--package", "refinement", "python", "-m", "agent_refinement.main"]

FROM academix-refinement-worker AS refinement

FROM base AS academix-translation-worker
COPY --from=builder-translation /app/.venv /app/.venv
COPY . .
RUN uv sync --frozen --no-dev --package translation
CMD ["uv", "run", "--package", "translation", "python", "-m", "agent_translation.main"]

FROM academix-translation-worker AS translation

FROM base AS academix-matching-worker
COPY --from=builder-matching /app/.venv /app/.venv
COPY . .
RUN uv sync --frozen --no-dev --package matching
CMD ["uv", "run", "--package", "matching", "python", "-m", "agent_matching.main"]

FROM academix-matching-worker AS matching

FROM base AS academix-embedding-worker
COPY --from=builder-embedding /app/.venv /app/.venv
COPY . .
RUN uv sync --frozen --no-dev --package embedding-worker
CMD ["uv", "run", "--package", "embedding-worker", "python", "-m", "agent_embedding.main"]

FROM academix-embedding-worker AS embedding

FROM base AS academix-cv-parsing-worker
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
CMD ["uv", "run", "--package", "cv-parsing", "python", "-m", "agent_cv_parsing.main"]

FROM academix-cv-parsing-worker AS cv-parsing

FROM base AS academix-telegram-bot
COPY --from=builder-telegram-bot /app/.venv /app/.venv
COPY . .
RUN uv sync --frozen --no-dev --package telegram-bot
RUN python -m compileall -q /app/.venv /app/packages/agents/telegram-bot /app/packages/core
CMD ["uv", "run", "--package", "telegram-bot", "python", "-m", "telegram_bot.main"]

FROM academix-telegram-bot AS telegram-bot

# Crawler & Scraper Stages
FROM slim AS academix-academic-discovery
CMD ["uv", "run", "--package", "academictransfer-discovery", "python", "-m", "academictransfer_discovery.main"]

FROM academix-academic-discovery AS academic-disc
FROM academix-academic-discovery AS academictransfer-discovery

FROM slim AS academix-academic-sourcing
CMD ["uv", "run", "--package", "academictransfer-sourcing", "python", "-m", "academictransfer_sourcing.main"]

FROM academix-academic-sourcing AS academic-src
FROM academix-academic-sourcing AS academictransfer-sourcing

FROM slim AS academix-euraxess-discovery
CMD ["uv", "run", "--package", "euraxess-discovery", "python", "-m", "euraxess_discovery.main"]

FROM academix-euraxess-discovery AS euraxess-disc

FROM slim AS academix-euraxess-sourcing
CMD ["uv", "run", "--package", "euraxess-sourcing", "python", "-m", "euraxess_sourcing.main"]

FROM academix-euraxess-sourcing AS euraxess-src

FROM slim AS academix-abg-discovery
CMD ["uv", "run", "--package", "abg-discovery", "python", "-m", "abg_discovery.main"]

FROM academix-abg-discovery AS abg-disc

FROM slim AS academix-abg-sourcing
CMD ["uv", "run", "--package", "abg-sourcing", "python", "-m", "abg_sourcing.main"]

FROM academix-abg-sourcing AS abg-src

FROM slim AS academix-naturecareers-discovery
CMD ["uv", "run", "--package", "naturecareers-discovery", "python", "-m", "naturecareers_discovery.main"]

FROM academix-naturecareers-discovery AS nature-disc

FROM slim AS academix-naturecareers-sourcing
CMD ["uv", "run", "--package", "naturecareers-sourcing", "python", "-m", "naturecareers_sourcing.main"]

FROM academix-naturecareers-sourcing AS nature-src

FROM slim AS academix-researchgate-discovery
CMD ["uv", "run", "--package", "researchgate-discovery", "python", "-m", "researchgate_discovery.main"]

FROM academix-researchgate-discovery AS rgate-disc

FROM slim AS academix-researchgate-sourcing
CMD ["uv", "run", "--package", "researchgate-sourcing", "python", "-m", "researchgate_sourcing.main"]

FROM academix-researchgate-sourcing AS rgate-src

FROM slim AS academix-euroscience-discovery
CMD ["uv", "run", "--package", "eurosciencejobs-discovery", "python", "-m", "eurosciencejobs_discovery.main"]

FROM academix-euroscience-discovery AS euroscience-disc
FROM academix-euroscience-discovery AS eurosciencejobs-discovery

FROM slim AS academix-euroscience-sourcing
CMD ["uv", "run", "--package", "eurosciencejobs-sourcing", "python", "-m", "eurosciencejobs_sourcing.main"]

FROM academix-euroscience-sourcing AS euroscience-src
FROM academix-euroscience-sourcing AS eurosciencejobs-sourcing

FROM slim AS academix-migration-runner
CMD ["uv", "run", "python", "-m", "core.infrastructure.db.run_migrations"]

FROM slim AS academix-cleanup-agent
CMD ["uv", "run", "--package", "agent-cleanup", "python", "-m", "agent_cleanup.main"]

