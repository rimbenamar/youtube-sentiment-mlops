#!/usr/bin/env bash
# Démarre (ou redémarre) l'API dans Docker. Idempotent : peut être relancé à tout moment.
# Lancé automatiquement à chaque démarrage du Codespace (.devcontainer/devcontainer.json),
# ce qui règle le problème « l'URL ne marche plus après la mise en veille du Codespace ».
#   bash scripts/start_api.sh            # journal : /tmp/start_api.log en automatique
set -uo pipefail
cd "$(dirname "$0")/.."

IMAGE=youtube-sentiment-api
CONTAINER=youtube-sentiment-api
PORT="${PORT:-7860}"

log() { echo "[$(date +%H:%M:%S)] $*"; }

# 1. Attendre que le démon Docker soit prêt (docker-in-docker démarre en parallèle)
for i in $(seq 1 60); do docker info >/dev/null 2>&1 && break; sleep 1; done
if ! docker info >/dev/null 2>&1; then log "Docker indisponible"; exit 1; fi

# 2. Entraîner le modèle s'il manque
if [ ! -f models/sentiment_model.joblib ] || [ ! -f models/tfidf_vectorizer.joblib ]; then
  log "Modèle absent : entraînement (quelques minutes)…"
  python -m pip install -q --user -r requirements-dev.txt
  python run_pipeline.py || { log "Échec de l'entraînement"; exit 1; }
fi

# 3. Construire l'image (rapide si rien n'a changé grâce au cache des couches)
log "Build de l'image $IMAGE"
docker build -q -t "$IMAGE" . >/dev/null || { log "Échec du build"; exit 1; }

# 4. (Re)lancer le conteneur
docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
docker run -d --name "$CONTAINER" --restart unless-stopped -p "$PORT:7860" "$IMAGE" >/dev/null
for i in $(seq 1 30); do curl -fs "http://localhost:$PORT/health" >/dev/null && break; sleep 1; done
if curl -fs "http://localhost:$PORT/health" >/dev/null; then
  log "API OK : $(curl -s "http://localhost:$PORT/health")"
else
  log "L'API ne répond pas. Journaux :"; docker logs --tail 30 "$CONTAINER"; exit 1
fi

# 5. Port public + URL (dans un Codespace uniquement)
if [ -n "${CODESPACE_NAME:-}" ]; then
  gh codespace ports visibility "$PORT:public" -c "$CODESPACE_NAME" >/dev/null 2>&1 \
    && log "Port $PORT rendu public" \
    || log "Rendez le port public : onglet Ports > clic droit sur $PORT > Port Visibility > Public"
  URL="https://${CODESPACE_NAME}-${PORT}.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-app.github.dev}"
  echo "$URL" > /tmp/api_url.txt
  echo ""
  echo "================================================================"
  echo " URL publique de l'API : $URL"
  echo " Documentation         : $URL/docs"
  echo " -> à coller dans l'extension (⚙️ > URL de l'API)"
  echo "================================================================"
else
  echo "API locale : http://localhost:$PORT/docs"
fi
