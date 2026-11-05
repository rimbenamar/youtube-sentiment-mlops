# ---------- Image de l'API de sentiment YouTube ----------
# Image de base légère
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=7860

WORKDIR /app

# 1) Dépendances d'abord : cette couche reste en cache tant que requirements.txt ne change pas
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2) Code et modèles ensuite (changent plus souvent) - uniquement les fichiers nécessaires
COPY src/__init__.py src/__init__.py
COPY src/utils/ src/utils/
COPY src/api/ src/api/
COPY app_api.py .
COPY models/ models/

# 3) Utilisateur non-root (bonne pratique de sécurité)
RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/logs && chown -R appuser:appuser /app
USER appuser

EXPOSE 7860

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"7860\")}/health', timeout=4)" || exit 1

# Port configurable via la variable d'environnement PORT
CMD ["sh", "-c", "uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-7860} --proxy-headers --forwarded-allow-ips='*'"]
