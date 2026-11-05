# Déroulé de la vidéo de démonstration (5–8 min)

**Préparation** : ouvrir le Codespace (l'API démarre seule ; vérifier `cat /tmp/start_api.log` et que le port 7860 est **Public**),
coller l'URL dans Écho (⚙️), choisir deux vidéos (une très appréciée, une polémique).

| Temps | Séquence | À montrer / dire |
|---|---|---|
| 0:00–0:45 | Introduction | Problème, schéma d'architecture (`reports/figures/architecture.png`) |
| 0:45–1:45 | Modèle | `reports/performance_report.md` : comparaison avec la baseline, matrice de confusion, critères atteints |
| 1:45–2:45 | API cloud | Codespace, `docker ps`, onglet Ports (Public), `/health` (version du modèle), `/docs` → *Try it out* sur `/predict_batch` (`processing_time_ms`, `"!!!"` → `skipped`) |
| 2:45–3:30 | Installation | `chrome://extensions` → Mode développeur → Charger `dist/echo-extension` → épingler → pastille verte |
| 3:30–5:15 | Utilisation réelle | Vidéo YouTube → Analyser → progression lot par lot → **fermer le popup pendant l'analyse puis le rouvrir** → répartition, score, liste |
| 5:15–6:30 | Fonctionnalités | Onglets Positifs/Négatifs, recherche, tri par confiance (cas douteux), mode sombre, Copier, CSV ouvert dans Excel |
| 6:30–7:15 | Robustesse | Page non-vidéo → bouton désactivé ; `docker stop` → pastille rouge + message clair ; `docker start` → retour |
| 7:15–8:00 | Conclusion | Temps de réponse, limites (Reddit → YouTube, sarcasme, anglais), pistes d'amélioration |
