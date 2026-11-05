# Documentation de l'API

Base URL : `http://localhost:7860` (local) ou `https://<nom>-7860.app.github.dev` (Codespaces).
Documentation interactive : `/docs` (Swagger) et `/redoc`.

Chaque réponse contient l'en-tête `X-Process-Time-Ms` (temps de traitement côté serveur).

## GET /health

Vérifie l'état de l'API et du modèle (monitoring).

```json
{
  "status": "ok",
  "model_loaded": true,
  "model_name": "LogisticRegression",
  "model_version": "c46d30fa5a20",
  "uptime_seconds": 124.3,
  "error": null
}
```

`status` vaut `degraded` (et `model_loaded: false`, `error` renseigné) si les fichiers `.joblib` sont introuvables.

## POST /predict_batch

Analyse un batch de commentaires.

**Requête**

| Champ | Type | Contraintes |
|---|---|---|
| `comments` | `string[]` | 1 à 1000 éléments, au moins un non vide ; chaque texte tronqué à 5000 caractères |

```json
{ "comments": ["This video is amazing!", "Worst tutorial ever", "What camera do you use?"] }
```

**Réponse 200**

```json
{
  "predictions": [
    {
      "text": "This video is amazing!",
      "sentiment": 1,
      "label": "positif",
      "confidence": 0.9312,
      "probabilities": { "negatif": 0.0201, "neutre": 0.0487, "positif": 0.9312 },
      "skipped": false
    }
  ],
  "statistics": {
    "total": 3, "analyzed": 3, "skipped": 0,
    "positive": 1, "neutral": 1, "negative": 1,
    "positive_pct": 33.33, "neutral_pct": 33.33, "negative_pct": 33.33,
    "average_confidence": 0.8721,
    "sentiment_score": 0.0,
    "dominant": "positif"
  },
  "processing_time_ms": 3.41,
  "model_version": "c46d30fa5a20"
}
```

- `model_version` : 12 premiers caractères de l'empreinte SHA-256 des fichiers du modèle (identique entre deux entraînements identiques)
- `sentiment` : -1 négatif, 0 neutre, 1 positif
- `confidence` : probabilité de la classe prédite
- `sentiment_score` : (nb positifs − nb négatifs) / total, entre -1 et 1
- L'ordre des prédictions est celui des commentaires envoyés. Un texte vide après nettoyage (ex. `"!!!"`) est renvoyé avec `"skipped": true` et `"label": "ignore"`, et **exclu** des pourcentages (`analyzed` = `total` − `skipped`).

## POST /predict

```json
{ "text": "I love this channel" }
```
Renvoie un objet `Prediction` (mêmes champs qu'un élément de `predictions`).

## Codes d'erreur

| Code | Cas | Corps |
|---|---|---|
| 422 | Batch vide, uniquement des chaînes vides, champ manquant, mauvais type, > 1000 éléments, JSON invalide | `{"error": "Données invalides", "details": [{"field": "...", "message": "..."}]}` |
| 503 | Modèle non chargé | `{"detail": "Modèle indisponible : ..."}` |
| 500 | Erreur interne | `{"error": "Erreur interne du serveur"}` |

## Exemples

```bash
# curl
bash scripts/test_api.sh https://<nom>-7860.app.github.dev
```

```python
import requests
r = requests.post("https://<nom>-7860.app.github.dev/predict_batch",
                  json={"comments": ["great video", "so boring"]}, timeout=30)
print(r.json()["statistics"])
```

```javascript
const res = await fetch(`${API_URL}/predict_batch`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ comments: ["great video", "so boring"] }),
});
const data = await res.json();
```

## Configuration (variables d'environnement)

| Variable | Défaut | Rôle |
|---|---|---|
| `PORT` | `7860` | Port d'écoute |
| `ALLOWED_ORIGINS` | `*` | Origines CORS autorisées (séparées par des virgules) ; `chrome-extension://*` est toujours autorisé |
| `MODEL_PATH` / `VECTORIZER_PATH` | `models/…joblib` | Chemins des artefacts |
| `WORKERS` | `1` | Nombre de workers (via `python app_api.py`) |
