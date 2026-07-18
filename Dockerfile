FROM python:3.12-slim AS base
WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    libglib2.0-0 \
    libgl1 \
    libxcb1 \
    libxext6 \
    libxrender1 \
    libsm6 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
COPY . .
RUN uv sync --frozen --all-packages

CMD ["uv", "run", "--package", "api", "fastapi", "run", "packages/api/src/api/main.py", "--host", "0.0.0.0", "--port", "8000"]
