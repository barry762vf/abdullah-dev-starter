# Production API image. Secrets are supplied at runtime as environment variables; nothing
# secret is copied into the image (see backend/.dockerignore and ADR 014).
FROM python:3.11-slim-bookworm AS builder
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /build
COPY requirements.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-compile -r requirements.txt

FROM python:3.11-slim-bookworm AS runtime
ENV PATH=/opt/venv/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ENV_FILE="" \
    PORT=8000 \
    WEB_CONCURRENCY=2
RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --home-dir /app --shell /usr/sbin/nologin app
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
# Code stays root-owned and read-only for the runtime user.
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen(f\"http://127.0.0.1:{os.environ.get('PORT', '8000')}/api/v1/health\", timeout=2)"]
# --no-proxy-headers: forwarding headers are never trusted; the client IP comes from the socket
# peer or the authenticated edge header (CLIENT_IP_SOURCE). Request logs come from the app.
# app.preflight validates settings once and exits non-zero before any worker starts.
CMD ["sh", "-c", "python -m app.preflight && exec uvicorn app.main:app --host 0.0.0.0 --port \"$PORT\" --workers \"$WEB_CONCURRENCY\" --no-proxy-headers --no-server-header --no-access-log"]
