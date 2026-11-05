/**
 * Configuration de l'extension.
 * >>> Remplacez DEFAULT_API_URL par l'URL publique de votre Codespace
 *     (https://<nom>-7860.app.github.dev) — ou saisissez-la dans ⚙️ Paramètres.
 *     `python scripts/package_extension.py --api-url <URL>` le fait automatiquement.
 */
var DEFAULT_API_URL = "http://localhost:7860";

var CONFIG = {
  BATCH_SIZE: 100,          // commentaires par requête /predict_batch
  MAX_PARALLEL: 3,          // requêtes simultanées
  REQUEST_TIMEOUT_MS: 30000,
  MAX_STORED_RESULTS: 15,   // analyses gardées en mémoire (une par vidéo)
  DEFAULT_SETTINGS: { apiUrl: DEFAULT_API_URL, maxComments: 100, autoScroll: true, includeReplies: false, theme: null },
};

if (typeof module !== "undefined") module.exports = { DEFAULT_API_URL, CONFIG };
