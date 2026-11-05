# Rapport technique

Le rapport PDF (8–12 pages) est **généré automatiquement** à partir de vos résultats réels :

```bash
python run_pipeline.py                 # produit models/ et reports/
python -m src.models.benchmark         # latences p50/p95 (recommandé)
python scripts/build_report.py --auteurs "Prénom Nom, Prénom Nom"
# -> reports/rapport-technique.pdf  (+ reports/figures/architecture.png)
```

Contenu : page de garde avec indicateurs clés, problème et critères du cahier des charges, architecture (diagramme),
données et nettoyage, choix techniques justifiés (TF-IDF, régression logistique, GridSearch), comparaison des modèles
avec baseline, résultats (matrice de confusion, latence, mots influents), API, extension (captures), déploiement
Docker / Codespaces, tests, difficultés et solutions, limites, améliorations et conclusion.

Avant de le rendre :
- remplacez `docs/screenshots/overview-light.png`, `comments-light.png` et `overview-dark.png` par vos captures sur une vraie vidéo (elles sont intégrées au PDF) ;
- relisez et adaptez le texte : le générateur insère vos chiffres, mais l'analyse doit refléter **votre** compréhension ;
- le contenu se modifie dans `scripts/build_report.py` (fonction `build`).
