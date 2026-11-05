#!/usr/bin/env bash
# Tests rapides des endpoints avec curl :  bash scripts/test_api.sh [URL]
URL="${1:-http://localhost:7860}"
echo "== GET /health";  curl -s "$URL/health"; echo; echo
echo "== POST /predict_batch"
curl -s -X POST "$URL/predict_batch" -H "Content-Type: application/json" \
  -d '{"comments":["This video is amazing, thank you!","Worst tutorial ever","What camera do you use?"]}'; echo; echo
echo "== POST /predict_batch (batch vide -> 422)"
curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST "$URL/predict_batch" -H "Content-Type: application/json" -d '{"comments":[]}'
echo "== POST /predict_batch (JSON invalide -> 422)"
curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST "$URL/predict_batch" -H "Content-Type: application/json" -d '{"text":"x"}'
