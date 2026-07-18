FROM python:3.12-slim AS base
WORKDIR /app

# Install curl for docker healthcheck support
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
COPY . .
RUN uv sync --frozen

CMD ["uv", "run", "--package", "api", "fastapi", "run", "packages/api/src/api/main.py", "--host", "0.0.0.0", "--port", "8000"]
