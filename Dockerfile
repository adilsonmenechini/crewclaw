FROM python:3.13-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

FROM python:3.13-slim
WORKDIR /app
COPY --from=builder /app/.venv /app/.venv

COPY crewclaw ./crewclaw
COPY pyproject.toml .
COPY uv.lock .

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
RUN uv sync --frozen --no-dev
VOLUME /app/workspace

# Comando padrão (pode ser sobrescrito facilmente)
CMD ["crewclaw", "run", "--help"]
