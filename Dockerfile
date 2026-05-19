# syntax=docker/dockerfile:1.7

# Stage 1: 构建前端 dist
FROM node:20-alpine AS web-builder
WORKDIR /web
COPY web/package.json ./
RUN npm install --no-audit --no-fund
COPY web/ ./
RUN npm run build


# Stage 2: 用 uv 同步 Python 依赖
FROM python:3.12-slim AS py-builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project


# Stage 3: 运行时
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=py-builder /opt/venv /opt/venv
COPY pyproject.toml uv.lock alembic.ini ./
COPY alembic ./alembic
COPY fystrm ./fystrm
COPY scripts ./scripts
COPY --from=web-builder /web/dist ./web/dist

EXPOSE 8095
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://localhost:8095/health || exit 1
CMD ["uvicorn", "fystrm.main:app", "--host", "0.0.0.0", "--port", "8095"]
