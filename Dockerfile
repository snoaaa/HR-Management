# syntax=docker/dockerfile:1
# Saint Jean HRMS – one image: the Django backend serves the API under /api/
# and the built React application at the root URL, on port 8000.

# ── Stage 1: build the React application ────────────────────────────────────
FROM node:22-alpine AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
# The production build calls the API on the same origin ("/api/").
RUN npm run build

# ── Stage 2: Python application ─────────────────────────────────────────────
FROM python:3.11-slim AS app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# libcairo/pkg-config/gcc: needed by the PDF library (xhtml2pdf → pycairo).
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc pkg-config libcairo2-dev libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements.txt ./
RUN pip install -r requirements.txt

COPY backend/ ./
COPY --from=frontend /frontend/dist /app/frontend_dist

ENV FRONTEND_DIST=/app/frontend_dist \
    STATIC_ROOT=/app/staticfiles \
    BACKUP_ROOT=/app/backups \
    SERVE_MEDIA=true \
    DEBUG=false \
    PORT=8000

# Static files of the Django admin and of the API documentation.
RUN SECRET_KEY=build DATABASE_URL=sqlite:////tmp/build.sqlite3 python manage.py collectstatic --noinput \
    && sed -i 's/\r$//' docker-entrypoint.sh \
    && chmod +x docker-entrypoint.sh \
    && useradd --create-home --uid 1000 hrms \
    && mkdir -p /app/media /app/backups \
    && chown -R hrms:hrms /app/media /app/backups /app/staticfiles

USER hrms
EXPOSE 8000
VOLUME ["/app/media", "/app/backups"]

# Healthy as soon as the server answers (any HTTP status), whatever ALLOWED_HOSTS is.
HEALTHCHECK --interval=30s --timeout=6s --start-period=40s --retries=3 \
    CMD python healthcheck.py || exit 1

ENTRYPOINT ["./docker-entrypoint.sh"]
