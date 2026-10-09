# Multi-stage build for Nuvorix Control Plane API
FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.5.26 /uv /uvx /bin/

# Copy dependency configuration
COPY pyproject.toml README.md ./
COPY backend ./backend
COPY packages ./packages

# Install dependencies into virtualenv
RUN uv sync --frozen --no-dev || uv sync --no-dev

# Production runtime stage
FROM python:3.12-slim AS runner

WORKDIR /app

# Create non-root user
RUN groupadd -r nuvorix && useradd -r -g nuvorix nuvorix

# Copy installed venv and application
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app /app

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Ensure permissions
RUN chown -R nuvorix:nuvorix /app
USER nuvorix

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
