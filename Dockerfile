# syntax=docker/dockerfile:1.7
# ---------- etap 1: budowa zależności ----------
FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build
COPY requirements.txt .
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --upgrade pip \
 && /opt/venv/bin/pip install -r requirements.txt

# ---------- etap 2: obraz runtime ----------
FROM python:3.11-slim

LABEL org.opencontainers.image.title="macro-diet-app" \
      org.opencontainers.image.description="Low-carb / IF Macro Tracker (Streamlit + SQLite)"

ARG APP_UID=10001
ARG APP_GID=10001

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/tmp \
    MACRO_DATA_DIR=/app/data \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Aktualizacje bezpieczeństwa systemu bazowego, bez zbędnych pakietów
RUN apt-get update \
 && apt-get upgrade -y --no-install-recommends \
 && rm -rf /var/lib/apt/lists/* \
 && groupadd -r -g ${APP_GID} appgroup \
 && useradd -r -u ${APP_UID} -g appgroup -d /app -s /usr/sbin/nologin appuser

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app

# Kod tylko do odczytu: root:root, pliki 0644, katalogi 0755.
# UWAGA: nie używamy "COPY --chmod=0644" – BuildKit nadaje ten tryb także katalogom
# tworzonym przy kopiowaniu (/app/.streamlit bez bitu x -> PermissionError na secrets.toml).
COPY app.py db.py foods.json ./
COPY .streamlit/config.toml ./.streamlit/config.toml

# Jedyny zapisywalny katalog: wolumen na SQLite + foods.json
RUN chown -R root:root /app \
 && find /app -type d -exec chmod 0755 {} + \
 && find /app -type f -exec chmod 0644 {} + \
 && mkdir -p /app/data \
 && chown appuser:appgroup /app/data \
 && chmod 0700 /app/data

VOLUME ["/app/data"]

USER appuser

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health', timeout=4).status == 200 else 1)"

# Wolumen tylko na dane, kod z obrazu; STOPSIGNAL domyślny SIGTERM -> SQLite zamyka się czysto
CMD ["streamlit", "run", "app.py"]
