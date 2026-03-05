# -- Stage 1: Build --
# Build context must be the py/ workspace root.
FROM python:3.12-slim AS builder
WORKDIR /workspace

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy workspace root pyproject.toml for dependency resolution
COPY pyproject.toml ./pyproject.toml

# Copy foundrykit library (workspace dependency)
COPY libs/foundrykit ./libs/foundrykit

# Copy app source
COPY apps/loan-origination ./apps/loan-origination

# Install dependencies from the app directory
WORKDIR /workspace/apps/loan-origination
RUN uv sync --no-dev

# -- Stage 2: Run --
FROM python:3.12-slim AS runner
WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app

# uv workspace creates .venv at workspace root (/workspace/.venv)
COPY --from=builder /workspace/.venv /app/.venv
COPY --from=builder /workspace/apps/loan-origination /app
COPY --from=builder /workspace/libs/foundrykit /app/libs/foundrykit

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/libs/foundrykit"
USER app
EXPOSE 8002

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
