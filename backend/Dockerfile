# Backend image (spec 017, T023).
#
# IMPORTANT: build context is the REPO ROOT (set RAILWAY_DOCKERFILE_PATH=backend/Dockerfile
# on the Railway backend service). That's required because the API installs the
# `intuitiveness` core editable from the repo root — it lives one level above
# `backend/`. Building from inside `backend/` alone cannot see it.

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

# Build tooling for any wheels that need compiling (psycopg2-binary ships wheels,
# but keep gcc available for safety on slim).
RUN apt-get update && apt-get install -y --no-install-recommends gcc \
 && rm -rf /var/lib/apt/lists/*

# --- the core package (installed editable with the postgres + graph extras) --
COPY pyproject.toml README.md ./
COPY intuitiveness ./intuitiveness
RUN pip install --upgrade pip && pip install -e ".[postgres,graph]"

# --- the FastAPI adapter + its server deps -----------------------------------
COPY backend ./backend
RUN pip install \
      "fastapi>=0.110" \
      "uvicorn[standard]>=0.29" \
      "httpx>=0.27" \
      "python-multipart>=0.0.9"

WORKDIR /app/backend

EXPOSE 8000
# Railway injects $PORT; default to 8000 for local `docker run`.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
