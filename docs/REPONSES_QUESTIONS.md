# Réponses aux questions de réflexion

## Phase 1 — Configuration de l'environnement MLOps

**Pourquoi séparer les données raw et processed ?**
Les données brutes sont la source de vérité : on ne les modifie jamais. Tout le traitement (nettoyage, split) est fait par un script qui lit `raw/` et écrit dans `processed/`. On peut donc à tout moment supprimer `processed/` et le régénérer à l'identique, modifier le nettoyage sans avoir à re-télécharger, comparer avant/après, et tracer l'origine de chaque donnée. C'est la base de la reproductibilité : *données brutes + code versionné = résultat reproductible*.

**Quels fichiers ne doivent jamais être commités sur Git ?**
- Les secrets : `.env`, clés d'API, tokens, mots de passe, certificats (`*.pem`, `*.key`).
- L'environnement virtuel (`venv/`) : lourd, spécifique à la machine ; `requirements.txt` suffit à le recréer.
- Les données volumineuses ou régénérables (`data/raw`, `data/processed`) : elles se téléchargent/recalculent ; pour les versionner on utilise DVC ou Git LFS.
- Les fichiers générés : `__pycache__/`, `*.pyc`, `logs/`, `.pytest_cache/`, archives de build.
- Les fichiers propres à l'éditeur/OS : `.vscode/`, `.idea/`, `.DS_Store`.
Exception volontaire ici : les modèles `.joblib` (moins d'1 Mo compressés) sont commités car le Dockerfile les copie dans l'image et le TP demande de les pousser. Pour de gros modèles, on utiliserait Git LFS ou un registre de modèles (MLflow).

**Quelle est l'importance d'un environnement virtuel ?**
Il isole les dépendances du projet de celles du système et des autres projets : chaque projet a ses propres versions (ici scikit-learn 1.7.2 figée), sans conflit ni droits administrateur. Avec `requirements.txt`, n'importe qui (ou le Codespace, ou Docker) recrée exactement le même environnement. C'est essentiel en ML car un modèle sérialisé avec une version de scikit-learn peut ne pas se charger avec une autre.

## Phase 2 — Pipeline de données

**Pourquoi nettoyer les URLs et mentions ?**
Ce sont des tokens quasi uniques (chaque URL, chaque @pseudo est différent) qui n'apportent aucune information de sentiment. Ils gonflent le vocabulaire TF-IDF, ajoutent du bruit, favorisent le sur-apprentissage (le modèle peut mémoriser un pseudo associé à une classe) et ne se généralisent pas aux commentaires YouTube. Les supprimer réduit la dimension et améliore la généralisation. Pour la même raison, on retire les timestamps type `1:23`, très fréquents sur YouTube.

**Comment gérer les emojis dans le texte ?**
Plusieurs options : les supprimer (perte d'information), les garder comme tokens (le dataset Reddit en contient peu), ou les **convertir en mots**. Nous avons choisi la conversion pour les emojis les plus courants (`😍 → love`, `😭 → sad`, `👎 → bad`, `🔥 → awesome`…) dans `text_cleaning.py`, car sur YouTube un commentaire peut n'être qu'un emoji et celui-ci porte souvent tout le sentiment. Les autres sont supprimés lors de la normalisation ASCII. Une amélioration serait d'utiliser la librairie `emoji` (`emoji.demojize`) pour couvrir tous les emojis.

**Quel ratio train/test est approprié ?**
80/20 est un bon compromis pour ~37 000 commentaires : ~7 000 exemples de test donnent une estimation stable (intervalle de confiance d'environ ±1 % sur l'accuracy) tout en gardant assez de données pour l'entraînement. Le split est **stratifié** (même proportion de classes dans train et test) et **reproductible** (`random_state=42`). L'optimisation des hyperparamètres se fait par validation croisée (3 folds) **uniquement sur le train**, pour que le test set reste une évaluation non biaisée. Pour un petit dataset (~1 000), on préférerait 70/30 ou une validation croisée complète.

**Gestion du déséquilibre** : le dataset est modérément déséquilibré (positif > neutre > négatif, ratio ~2:1). Plutôt que du sur-échantillonnage, on teste `class_weight="balanced"` dans la GridSearch et on optimise le **F1 macro**, qui pénalise une mauvaise classe minoritaire.

## Phase 3 — Modèle

**Pourquoi utiliser TF-IDF plutôt que Count Vectorizer ?**
CountVectorizer compte les occurrences brutes : les mots très fréquents mais peu informatifs (« the », « video », « is ») dominent. TF-IDF pondère chaque mot par l'inverse de sa fréquence documentaire : un mot présent partout pèse peu, un mot discriminant (« awesome », « worst ») pèse beaucoup. Avec `sublinear_tf=True` (1 + log tf), un mot répété 10 fois ne pèse pas 10 fois plus. La normalisation L2 rend aussi les commentaires courts et longs comparables. Résultat : de meilleures performances avec les modèles linéaires, pour le même coût.

**Comment interpréter la matrice de confusion ?**
Les lignes sont les classes réelles, les colonnes les classes prédites. La diagonale contient les bonnes prédictions ; chaque case hors diagonale montre un type d'erreur précis. On lit par ligne le **rappel** (part des vrais négatifs bien retrouvés) et par colonne la **précision**. Pour le sentiment, les erreurs graves sont négatif ↔ positif (sarcasme, négations : « not bad »), tandis que les confusions avec neutre sont plus « acceptables » (sentiment faible). La version normalisée (pourcentages par ligne) permet de comparer les classes malgré le déséquilibre. Voir `reports/figures/confusion_matrix.png`.

**Quels hyperparamètres ont le plus d'impact sur les performances ?**
D'après la GridSearch (`reports/gridsearch_results.csv`) :
1. **`ngram_range`** : passer de (1,1) à (1,2) capte les négations et expressions (« not good », « waste time ») — gain le plus important.
2. **`C`** (inverse de la régularisation) : trop faible = sous-apprentissage ; une valeur plus élevée (5–10) convient bien à ce vocabulaire riche.
3. **`class_weight`** : améliore le F1 de la classe minoritaire (négatif), parfois au prix d'un peu d'accuracy.
4. **`max_features`** : impact modéré au-delà de 20 000 ; il joue surtout sur la taille du modèle et la vitesse.

## Phase 4 — API REST

**Pourquoi utiliser FastAPI plutôt que Flask ?**
- **Validation automatique** des entrées/sorties avec Pydantic (types, tailles, erreurs 422 explicites) au lieu de vérifications manuelles.
- **Documentation interactive générée** (`/docs` Swagger, `/redoc`) à partir du code : utile pour tester et pour le livrable « documentation API ».
- **Performances** : ASGI (Uvicorn), support natif de l'asynchrone, parmi les frameworks Python les plus rapides.
- **Annotations de type** : meilleure autocomplétion, moins de bugs, code plus lisible.
- Fonctions modernes intégrées : lifespan (chargement du modèle au démarrage), middlewares, injection de dépendances.
Flask reste plus simple et très répandu, mais il faudrait ajouter soi-même validation et documentation.

**À quoi sert la configuration CORS ?**
Les navigateurs appliquent la *Same-Origin Policy* : une page d'une origine (ex. `chrome-extension://abc` ou `https://youtube.com`) ne peut pas lire la réponse d'une requête vers une autre origine (`https://…app.github.dev`) sauf si le serveur l'autorise explicitement via les en-têtes `Access-Control-Allow-Origin`. Pour un POST JSON, le navigateur envoie d'abord une requête *preflight* `OPTIONS`. Le `CORSMiddleware` répond à ces requêtes et ajoute les en-têtes. Nous autorisons les origines `chrome-extension://*` (et `*` par défaut, configurable via `ALLOWED_ORIGINS` pour restreindre en production). À noter : en Manifest V3, le popup avec `host_permissions` sur l'API n'est pas bloqué par CORS, mais un content script ou une page web le serait.

**Comment gérer efficacement le chargement du modèle ?**
Le modèle et le vectoriseur sont chargés **une seule fois au démarrage** (lifespan FastAPI) et gardés en mémoire dans un objet `SentimentPredictor` — jamais à chaque requête (charger un `.joblib` prend des centaines de ms). Une prédiction de pré-chauffe est faite au chargement. Si le chargement échoue, l'API démarre quand même et `/health` renvoie `degraded` avec l'erreur (plus facile à diagnostiquer qu'un conteneur qui redémarre en boucle), et `/predict_batch` renvoie 503. Les prédictions sont vectorisées par batch (un seul `transform` + `predict_proba` pour tout le lot), ce qui est bien plus rapide que commentaire par commentaire. Les fichiers sont compressés (`compress=3`) pour une image plus légère.

## Phase 5 — Extension Chrome

**Comment gérer les commentaires avec des réponses (threads) ?**
Sur YouTube, chaque fil (`ytd-comment-thread-renderer`) contient un commentaire principal et un conteneur de réponses (`ytd-comment-replies-renderer`), repliées par défaut. Le script de contenu distingue les deux grâce à `node.closest("ytd-comment-replies-renderer")` : par défaut seuls les commentaires principaux sont analysés (ils représentent l'avis sur la vidéo ; les réponses discutent souvent d'un autre commentaire et peuvent fausser les statistiques). L'option « Inclure les réponses » ajoute les réponses dépliées, marquées « réponse » dans la liste. Une amélioration serait de cliquer automatiquement sur « Afficher les réponses » et de calculer un sentiment par fil.

**Quelle stratégie pour extraire les commentaires dynamiques ?**
YouTube est une application monopage qui charge les commentaires paresseusement (seulement quand la section est visible, puis par blocs de ~20 au scroll). Stratégie :
1. faire défiler jusqu'à `#comments` pour déclencher le premier chargement et attendre que des fils apparaissent ;
2. si « Chargement auto » est activé, faire défiler en bas de page en boucle, attendre ~1 s, et s'arrêter quand le nombre voulu est atteint, quand rien de nouveau n'arrive 3 fois de suite, ou après 30 s ;
3. lire le DOM avec des sélecteurs couvrant l'ancien (`ytd-comment-renderer`) et le nouveau (`ytd-comment-view-model`) format, dédupliquer, puis remettre la page à sa position initiale.
Le script est aussi injecté à la demande (`chrome.scripting.executeScript`) si l'onglet était ouvert avant l'installation. Alternative plus robuste : l'API YouTube Data v3 (`commentThreads`), qui nécessite une clé API et un quota.

**Comment optimiser les performances avec de nombreux commentaires ?**
- Limiter le nombre extrait (paramètre, 100 par défaut, 1000 max) et tronquer les textes très longs côté API.
- Exécuter l'analyse dans le **service worker** et non dans le popup : l'utilisateur peut fermer le popup pendant une longue analyse sans la perdre.
- Envoyer par **lots de 100** avec au plus 3 requêtes en parallèle (débit élevé sans surcharger l'API) et afficher la progression lot par lot.
- Côté API, prédiction vectorisée par batch.
- Côté interface : construction de la liste avec un `DocumentFragment` (une seule mise à jour du DOM), texte replié à 3 lignes, filtres/recherche faits localement sans rappeler l'API.
- Mise en cache des analyses par vidéo dans `chrome.storage` (pas de nouvel appel en rouvrant le popup sur une vidéo déjà analysée).
- Pour des milliers de commentaires : liste virtualisée (n'afficher que les éléments visibles) et pagination.

## Phase 6 — Déploiement Docker

**Pourquoi séparer les requirements dev et prod ?**
L'image de production ne doit contenir que ce qui est nécessaire pour servir le modèle (FastAPI, Uvicorn, scikit-learn, joblib, numpy). pandas, matplotlib, pytest, httpx ne servent qu'à l'entraînement et aux tests. Les séparer donne : une image plus petite (build et démarrage plus rapides), une surface d'attaque réduite (moins de paquets vulnérables), moins de risques de conflits, et des versions de prod figées et maîtrisées. Ici `requirements-dev.txt` inclut `requirements.txt` (`-r`) : les versions critiques (scikit-learn, joblib) sont donc identiques à l'entraînement et en production.

**Comment réduire la taille de l'image Docker ?**
- Image de base légère `python:3.10-slim` (~120 Mo au lieu de ~1 Go pour `python:3.10`).
- `pip install --no-cache-dir` / `PIP_NO_CACHE_DIR=1` : pas de cache pip dans l'image.
- `.dockerignore` : exclure `venv/`, `.git/`, `data/`, `tests/`, `docs/`, l'extension…
- Ne copier que `src/api`, `src/utils`, `app_api.py` et `models/`.
- Requirements de production minimaux, modèles compressés.
- Aller plus loin : build multi-étapes, image `distroless`, ou suppression des fichiers de test des paquets installés.

**Quelle stratégie pour les mises à jour du modèle ?**
- **Versionner** chaque modèle : `model_version` = empreinte SHA-256 des fichiers `.joblib` (dans `model_metadata.json`, exposée par `/health` et dans chaque réponse), ce qui prouve quel fichier est réellement servi ; conserver ses métriques et le comparer à une baseline.
- Réentraîner avec le même pipeline (`run_pipeline.py`), valider automatiquement les critères (tests pytest : accuracy, F1, latence) avant de publier.
- Construire une nouvelle image taguée (`youtube-sentiment-api:20261105`), garder l'ancienne pour un **rollback** immédiat.
- Déploiement progressif (blue/green ou canary) en production réelle, avec monitoring des distributions de prédictions pour détecter la dérive des données (le vocabulaire YouTube évolue).
- Variante : monter les modèles en volume ou les télécharger depuis un registre (MLflow, S3) via `MODEL_PATH`, pour changer de modèle sans reconstruire l'image.
- Automatiser avec un pipeline CI/CD (GitHub Actions : tests → build → push de l'image).

**Quelle différence entre un environnement cloud éphémère (Codespaces) et un hébergement PaaS permanent ? Quelles conséquences pour la mise en production ?**

| | GitHub Codespaces | PaaS permanent (Render, Railway, Cloud Run, Azure App Service…) |
|---|---|---|
| Finalité | Environnement de **développement** | Hébergement d'**applications** |
| Disponibilité | S'arrête après ~30 min d'inactivité ; quota mensuel d'heures | 24/7, redémarrage automatique, SLA |
| URL | Change par Codespace, liée au port et à sa visibilité | Stable, domaine personnalisé, HTTPS géré |
| Scalabilité | Une VM, aucune montée en charge | Mise à l'échelle horizontale/automatique |
| Exploitation | Démarrage manuel (`docker run`) | Déploiement auto depuis Git/registre, health checks, logs, métriques |
| Coût | Gratuit dans le quota | Payant à l'usage (offres gratuites limitées) |

Pour limiter cet inconvénient ici, `.devcontainer/devcontainer.json` relance automatiquement l'API (build, `docker run`, port public) à chaque démarrage du Codespace.

Conséquences : Codespaces convient pour un prototype ou une démonstration, mais pas pour la production — l'URL de l'extension cesse de fonctionner dès que le Codespace s'arrête, aucun utilisateur réel ne pourrait en dépendre. Pour la production il faudrait un PaaS ou un service de conteneurs, une URL stable, du monitoring/alerting, des logs centralisés, un CI/CD, de l'authentification ou un quota (rate limiting) sur l'API, et restreindre CORS. L'avantage de Docker est que **la même image** fonctionne dans les deux cas : seul l'hébergeur change.
