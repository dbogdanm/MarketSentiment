# --- Stage 1: build the Tailwind stylesheet ---
FROM node:20-alpine AS assets

WORKDIR /build
COPY package.json ./
RUN npm install
COPY tailwind.config.js postcss.config.js ./
COPY website/static/css/input.css ./website/static/css/input.css
COPY website/static/js ./website/static/js
COPY website/templates ./website/templates
RUN npm run build:css

# --- Stage 2: application image ---
FROM python:3.11-slim

# System dependencies (libpq for psycopg2, curl for the container healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Install dependencies first so source changes don't bust this layer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=assets /build/website/static/css/style.css ./website/static/css/style.css

# Run as an unprivileged user; data/log dirs must be writable by it
RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/website/data_files /app/scheduler_logs \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:5000/healthz || exit 1

# GUNICORN_WORKERS/GUNICORN_TIMEOUT can be overridden at runtime
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:5000 --workers ${GUNICORN_WORKERS:-2} --timeout ${GUNICORN_TIMEOUT:-120} --access-logfile - --error-logfile - website.appFlask:app"]
