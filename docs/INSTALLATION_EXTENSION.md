# Installation de l'extension Chrome « Écho »

## 1. Charger l'extension

1. Ouvrir Chrome et aller sur `chrome://extensions`.
2. Activer le **Mode développeur** (interrupteur en haut à droite).
3. Cliquer sur **Charger l'extension non empaquetée**.
4. Sélectionner le dossier `chrome-extension/` du projet (celui qui contient `manifest.json`).
5. Épingler l'extension : icône puzzle 🧩 → épingle à côté de « Écho ».

Version packagée : `python scripts/package_extension.py` crée `dist/echo-extension-v3.0.0.zip` (à décompresser puis charger comme ci-dessus). Avec `--api-url https://<nom>-7860.app.github.dev`, l'URL de production est déjà configurée dans la copie empaquetée.

## 2. Configurer l'URL de l'API

Deux possibilités :

- **Dans l'interface** : ouvrir le popup → ⚙️ → coller `https://<nom>-7860.app.github.dev` → **Tester l'API** → **Enregistrer**.
- **Dans le code** : modifier `DEFAULT_API_URL` dans `chrome-extension/config.js`, puis cliquer sur ↻ (Recharger) dans `chrome://extensions`. Une URL déjà enregistrée dans ⚙️ reste prioritaire.

La pastille en haut du popup indique l'état : verte = API en ligne et modèle chargé, rouge = injoignable (survolez-la pour voir l'URL et la version du modèle).

## 3. Permissions demandées

| Permission | Pourquoi |
|---|---|
| `activeTab`, `scripting` | Lire les commentaires de l'onglet YouTube actif (et injecter le script si la page était ouverte avant l'installation) |
| `storage` | Mémoriser l'URL de l'API, le thème, la progression et les analyses par vidéo |
| Service worker (`background.js`) | Exécuter l'analyse même quand le popup est fermé |
| `https://www.youtube.com/*` | Content script d'extraction |
| `https://*.app.github.dev/*`, `http://localhost/*` | Appels à l'API (Codespaces ou locale) |

Pour utiliser un autre hébergeur, ajouter son domaine dans `host_permissions` de `manifest.json` (l'API autorise aussi CORS `*`).

## 4. Dépannage

| Symptôme | Solution |
|---|---|
| « Impossible de joindre l'API » | Codespace arrêté ou conteneur stoppé : relancer le Codespace puis `docker start youtube-sentiment-api` |
| « Le port 7860 est-il bien Public ? » | Onglet Ports du Codespace → clic droit 7860 → Port Visibility → Public |
| « Aucun commentaire extrait » | Commentaires désactivés, ou YouTube lent : faire défiler jusqu'aux commentaires et relancer |
| Rien ne se passe après une mise à jour du code | `chrome://extensions` → ↻ sur l'extension, puis recharger l'onglet YouTube |
| Erreur dans le service worker | `chrome://extensions` → Écho → « Inspecter les vues : service worker » pour voir la console |
