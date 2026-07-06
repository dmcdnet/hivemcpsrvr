FROM python:3.12-slim

# Install uv for fast, reproducible installs
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Install dependencies first for better layer caching
COPY pyproject.toml uv.lock README.md ./
COPY hivemcpsrvr ./hivemcpsrvr
RUN uv pip install --system --no-cache .

# Run as a non-root user
RUN useradd --create-home --uid 10001 hive
USER hive

# Network transport so an MCP client can connect to the container
ENV HIVE_TRANSPORT=sse \
    HIVE_HOST=0.0.0.0 \
    HIVE_PORT=8000

EXPOSE 8000

# Credentials are supplied at runtime via environment variables, e.g.
#   docker run --env-file .env -p 8000:8000 hivemcpsrvr
# See .env.example for the expected variables.
CMD ["hivemcpsrvr"]
