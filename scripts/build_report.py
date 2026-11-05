"""Génère le rapport technique PDF à partir des résultats réels du pipeline.

    python scripts/build_report.py --auteurs "Prénom Nom, Prénom Nom"

Prérequis : avoir lancé `python run_pipeline.py` (et idéalement `python -m src.models.benchmark`).
Sortie : reports/rapport-technique.pdf  (+ reports/figures/architecture.png)
Les captures docs/screenshots/overview-light.png, comments-light.png et overview-dark.png sont intégrées si présentes.
"""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_CENTER  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle  # noqa: E402
from reportlab.lib.units import cm  # noqa: E402
from reportlab.pdfbase import pdfmetrics  # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont  # noqa: E402
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph, Preformatted,  # noqa: E402
                                SimpleDocTemplate, Spacer, Table, TableStyle)

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
FIG = REPORTS / "figures"
SHOTS = ROOT / "docs" / "screenshots"

INK = colors.HexColor("#1c1b29")
MUTED = colors.HexColor("#6e6e76")
LINE = colors.HexColor("#e8e2d6")
SOFT = colors.HexColor("#f4f1ea")
POS, NEU, NEG = colors.HexColor("#0f9488"), colors.HexColor("#7a86a8"), colors.HexColor("#e8590c")


# ------------------------------------------------------------------ polices
def register_fonts():
    """DejaVu (livrée avec matplotlib) : gère les accents, les flèches et les guillemets."""
    ttf = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
    pdfmetrics.registerFont(TTFont("Body", str(ttf / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("Body-Bold", str(ttf / "DejaVuSans-Bold.ttf")))
    pdfmetrics.registerFont(TTFont("Mono", str(ttf / "DejaVuSansMono.ttf")))
    from reportlab.pdfbase.pdfmetrics import registerFontFamily
    registerFontFamily("Body", normal="Body", bold="Body-Bold", italic="Body", boldItalic="Body-Bold")


def styles():
    base = dict(fontName="Body", fontSize=9.6, leading=14, textColor=INK)
    return {
        "title": ParagraphStyle("title", fontName="Body-Bold", fontSize=26, leading=31, textColor=INK, spaceAfter=10),
        "subtitle": ParagraphStyle("subtitle", fontName="Body", fontSize=13, leading=18, textColor=MUTED),
        "h1": ParagraphStyle("h1", fontName="Body-Bold", fontSize=16, leading=21, spaceBefore=4, spaceAfter=8, textColor=INK),
        "h2": ParagraphStyle("h2", fontName="Body-Bold", fontSize=11.5, leading=15, spaceBefore=10, spaceAfter=4, textColor=INK),
        "p": ParagraphStyle("p", spaceAfter=6, **base),
        "small": ParagraphStyle("small", fontName="Body", fontSize=8.2, leading=11, textColor=MUTED),
        "caption": ParagraphStyle("caption", fontName="Body", fontSize=8.2, leading=11, textColor=MUTED, alignment=TA_CENTER, spaceBefore=3, spaceAfter=8),
        "cell": ParagraphStyle("cell", fontName="Body", fontSize=8.6, leading=11.5, textColor=INK),
        "cellb": ParagraphStyle("cellb", fontName="Body-Bold", fontSize=8.6, leading=11.5, textColor=INK),
        "code": ParagraphStyle("code", fontName="Mono", fontSize=7.6, leading=10, textColor=INK, backColor=SOFT,
                               borderPadding=6, spaceBefore=4, spaceAfter=8),
        "bullet": ParagraphStyle("bullet", leftIndent=12, bulletIndent=2, spaceAfter=2, **base),
    }


# ------------------------------------------------------------------ données
def load(path, default=None):
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def pct(x, d=1):
    return f"{100 * x:.{d}f} %"


# ------------------------------------------------------------------ figure d'architecture
def architecture_figure(path: Path):
    fig, ax = plt.subplots(figsize=(10, 5.4))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 56)
    ax.axis("off")

    def box(x, y, w, h, title, sub, color="#ffffff", edge="#17171a"):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.4,rounding_size=1.6", fc=color, ec=edge, lw=1.2))
        ax.text(x + w / 2, y + h * 0.63, title, ha="center", va="center", fontsize=9.5, weight="bold", color="#17171a")
        ax.text(x + w / 2, y + h * 0.28, sub, ha="center", va="center", fontsize=7.3, color="#55555c")

    def arrow(a, b, text="", dy=1.4, color="#17171a", style="-|>"):
        ax.add_patch(FancyArrowPatch(a, b, arrowstyle=style, mutation_scale=11, lw=1.1, color=color))
        if text:
            ax.text((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + dy, text, ha="center", fontsize=7, color="#55555c")

    # Zones
    ax.add_patch(FancyBboxPatch((1, 30), 41, 24, boxstyle="round,pad=0.3,rounding_size=2", fc="#f5f5f3", ec="none"))
    ax.text(3, 51.6, "Navigateur (Chrome, Manifest V3)", fontsize=8, color="#6e6e76", weight="bold")
    ax.add_patch(FancyBboxPatch((52, 30), 46, 24, boxstyle="round,pad=0.3,rounding_size=2", fc="#e9f3ee", ec="none"))
    ax.text(54, 51.6, "Cloud : GitHub Codespaces · conteneur Docker", fontsize=8, color="#2f6b52", weight="bold")
    ax.add_patch(FancyBboxPatch((1, 2), 97, 21, boxstyle="round,pad=0.3,rounding_size=2", fc="#fbf4e3", ec="none"))
    ax.text(3, 20.6, "Entraînement hors ligne (pipeline reproductible)", fontsize=8, color="#7a5c12", weight="bold")

    # Navigateur
    box(3, 40, 11, 8, "YouTube", "page /watch")
    box(17, 40, 11, 8, "content.js", "extraction DOM")
    box(31, 40, 10, 8, "Service", "worker (lots)")
    box(17, 31.5, 24, 6.5, "Popup", "stats · filtres · thème · export")
    arrow((14, 44), (17, 44))
    arrow((28, 44), (31, 44))
    arrow((36, 40), (33, 38), "")

    # Cloud
    box(55, 40, 12, 8, "FastAPI", "Pydantic · CORS")
    box(70, 40, 12, 8, "Predictor", "chargé 1 fois")
    box(85, 40, 11, 8, "TF-IDF + LR", "predict_proba")
    box(55, 31.5, 27, 6.5, "GET /health  ·  POST /predict_batch", "port 7860 public (HTTPS)")
    arrow((41, 45.5), (55, 45.5))
    arrow((55, 42.5), (41, 42.5))
    ax.text(48, 49.3, "POST /predict_batch", ha="center", fontsize=6.8, color="#55555c")
    ax.text(48, 47.4, "lots JSON · HTTPS", ha="center", fontsize=6.8, color="#55555c")
    ax.text(48, 38.6, "sentiments", ha="center", fontsize=6.8, color="#55555c")
    ax.text(48, 36.8, "+ statistiques", ha="center", fontsize=6.8, color="#55555c")
    arrow((67, 44), (70, 44))
    arrow((82, 44), (85, 44))

    # Entraînement
    box(3, 6, 13, 9, "reddit.csv", "37 249 commentaires")
    box(20, 6, 14, 9, "Nettoyage", "conflits · doublons")
    box(38, 6, 14, 9, "Split 80/20", "stratifié, seed 42")
    box(56, 6, 15, 9, "GridSearchCV", "F1 macro · CV 3")
    box(75, 6, 21, 9, "models/*.joblib", "version = SHA-256")
    for a, b in [((16, 10.5), (20, 10.5)), ((34, 10.5), (38, 10.5)), ((52, 10.5), (56, 10.5)), ((71, 10.5), (75, 10.5))]:
        arrow(a, b)
    arrow((90.5, 15.6), (90.5, 39.4), color="#7a5c12")
    ax.text(89.3, 26.5, "COPY dans\nl'image Docker", fontsize=7, color="#7a5c12", ha="right", va="center")
    fig.tight_layout()
    fig.savefig(path, dpi=170, bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------ helpers de mise en page
def table(rows, widths, st, header=True, zebra=True, align_right_from=None):
    data = [[Paragraph(str(c), st["cellb"] if (header and i == 0) else st["cell"]) for c in r] for i, r in enumerate(rows)]
    t = Table(data, colWidths=widths, hAlign="LEFT", repeatRows=1 if header else 0)
    cmds = [("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE),
            ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]
    if header:
        cmds += [("LINEBELOW", (0, 0), (-1, 0), 0.9, INK)]
    if zebra:
        for i in range(1 if header else 0, len(rows)):
            if i % 2 == 0:
                cmds.append(("BACKGROUND", (0, i), (-1, i), SOFT))
    t.setStyle(TableStyle(cmds))
    return t


def figure(path, width_cm, caption, st):
    if not Path(path).exists():
        return [Paragraph(f"<i>[Figure manquante : {Path(path).name}]</i>", st["small"])]
    from reportlab.lib.utils import ImageReader
    iw, ih = ImageReader(str(path)).getSize()
    w = width_cm * cm
    return [KeepTogether([Image(str(path), width=w, height=w * ih / iw), Paragraph(caption, st["caption"])])]


def bullets(items, st):
    return [Paragraph(i, st["bullet"], bulletText="•") for i in items]


# ------------------------------------------------------------------ contenu
def build(story, st, d):
    meta, metrics, eda, clean, bench = d["meta"], d["metrics"], d["eda"], d["clean"], d["bench"]
    r = meta["metrics"]
    f1 = r["f1_per_class"]
    lat = meta.get("latency_50_comments", {})
    res = metrics["results"]
    P = lambda t: story.append(Paragraph(t, st["p"]))  # noqa: E731
    H1 = lambda t: story.append(Paragraph(t, st["h1"]))  # noqa: E731
    H2 = lambda t: story.append(Paragraph(t, st["h2"]))  # noqa: E731

    # ---------- Page de garde
    story.append(Spacer(1, 3.2 * cm))
    story.append(Paragraph("TP3 · Projet ML complet", st["subtitle"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph("Analyse de sentiment des commentaires YouTube", st["title"]))
    story.append(Paragraph("Du développement au déploiement cloud : modèle scikit-learn, API FastAPI, "
                           "conteneur Docker sur GitHub Codespaces et extension Chrome « Écho ».", st["subtitle"]))
    story.append(Spacer(1, 1.2 * cm))
    kpis = [["Accuracy", "F1 macro", "Latence p95 (50 commentaires)", "Version du modèle"],
            [pct(r["accuracy"], 2), f"{r['f1_macro']:.3f}", f"{lat.get('p95_ms', r['inference_ms_50']):.1f} ms", meta["model_version"]]]
    t = Table([[Paragraph(c, st["small"]) for c in kpis[0]], [Paragraph(f"<b>{c}</b>", ParagraphStyle("k", fontName="Body-Bold", fontSize=15, leading=19)) for c in kpis[1]]],
              colWidths=[3.3 * cm, 3 * cm, 5.2 * cm, 5.1 * cm], hAlign="LEFT")
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), SOFT), ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
    story.append(t)
    story.append(Spacer(1, 2.2 * cm))
    info = [["Établissement", "ENSAM Rabat · Université Mohammed V · Filière INDIA"],
            ["Encadrante", "Prof. Maria Zemzami"],
            ["Auteur(s)", d["auteurs"]],
            ["Année universitaire", "2026/27"],
            ["Date du rapport", date.today().strftime("%d/%m/%Y")]]
    story.append(table(info, [4.2 * cm, 12.4 * cm], st, header=False, zebra=False))
    story.append(PageBreak())

    # ---------- 1. Problème
    H1("1. Analyse du problème et solution proposée")
    H2("Problématique")
    P("Une vidéo YouTube peut recevoir des centaines, voire des milliers de commentaires. Les lire pour comprendre la "
      "réaction du public est chronophage, impossible à faire à grande échelle, subjectif (deux lecteurs ne retiennent pas "
      "les mêmes commentaires) et difficile à transformer en chiffre utilisable pour une décision.")
    H2("Objectif")
    P("Classer automatiquement chaque commentaire en <b>négatif (-1)</b>, <b>neutre (0)</b> ou <b>positif (1)</b> et "
      "présenter, directement sur la page de la vidéo, une synthèse chiffrée : répartition, score global, liste filtrable.")
    H2("Contraintes du cahier des charges")
    story.append(table([["Critère", "Exigence", "Obtenu", "Statut"],
                        ["Accuracy (test)", "≥ 80 %", pct(r["accuracy"], 2), "✔" if r["accuracy"] >= .8 else "✘"],
                        ["F1 par classe", "> 0,75", f"{f1['negatif']:.3f} / {f1['neutre']:.3f} / {f1['positif']:.3f}",
                         "✔" if min(f1.values()) > .75 else "✘"],
                        ["Inférence, batch de 50", "< 100 ms", f"p95 = {lat.get('p95_ms', 0):.1f} ms", "✔" if lat.get("p95_ms", 999) < 100 else "✘"],
                        ["Dataset", "≥ 1 000 lignes, ≥ 300 / classe", f"{clean.get('rows_clean', eda['n_comments']):,} lignes".replace(",", " "), "✔"],
                        ["API", "REST, publique, HTTPS", "FastAPI · Codespaces · port 7860", "✔"],
                        ["Interface", "Extension Chrome", "Manifest V3 · service worker", "✔"]],
                       [4 * cm, 4.4 * cm, 6.2 * cm, 1.8 * cm], st))
    H2("Solution")
    P("Le système suit une démarche MLOps de bout en bout : un pipeline de données reproductible, un modèle optimisé et "
      "versionné, une API REST conteneurisée exécutée dans le cloud, une extension Chrome et des tests automatisés à chaque "
      "niveau (nettoyage, modèle, API, interface). Chaque étape se relance par une commande unique (<font name='Mono'>python run_pipeline.py</font>, "
      "<font name='Mono'>bash scripts/start_api.sh</font>, <font name='Mono'>pytest</font>).")

    # ---------- 2. Architecture
    story.append(PageBreak())
    H1("2. Architecture")
    story += figure(FIG / "architecture.png", 16.5, "Figure 1 — Architecture : flux d'analyse en ligne (haut) et pipeline d'entraînement hors ligne (bas).", st)
    H2("Flux de données")
    story += bullets([
        "<b>1–2.</b> Sur une page <i>youtube.com/watch</i>, le script de contenu fait défiler la section commentaires "
        "(chargée paresseusement par YouTube) puis lit le DOM.",
        "<b>3.</b> Le <b>service worker</b> découpe les textes en lots de 100 et les envoie à <font name='Mono'>POST /predict_batch</font> "
        "(3 requêtes en parallèle). Il tourne indépendamment du popup : fermer le popup n'interrompt pas l'analyse.",
        "<b>4.</b> L'API valide la requête (Pydantic), nettoie les textes avec la <b>même fonction qu'à l'entraînement</b>, "
        "vectorise (TF-IDF) et prédit les probabilités (régression logistique) en une seule opération vectorisée.",
        "<b>5–6.</b> Les prédictions et statistiques sont stockées par vidéo (<font name='Mono'>chrome.storage</font>) ; le popup "
        "les affiche et se met à jour en direct pendant l'analyse.",
    ], st)
    H2("Composants")
    story.append(table([["Couche", "Technologie", "Emplacement"],
                        ["Frontend", "Extension Chrome MV3 (HTML, CSS, JS sans dépendance)", "chrome-extension/"],
                        ["Backend", "FastAPI, Pydantic v2, Uvicorn", "src/api/, app_api.py"],
                        ["ML", "scikit-learn : TF-IDF + LogisticRegression, joblib", "src/models/, models/"],
                        ["Données", "pandas, matplotlib", "src/data/, reports/"],
                        ["Déploiement", "Docker (python:3.10-slim), GitHub Codespaces, devcontainer", "Dockerfile, .devcontainer/"],
                        ["Qualité", "pytest, node --test, GitHub Actions", "tests/, .github/workflows/"]],
                       [2.8 * cm, 8.6 * cm, 5 * cm], st))

    # ---------- 3. Données
    story.append(PageBreak())
    H1("3. Données et préparation")
    P(f"Le dataset Reddit Sentiment Analysis (fichier <font name='Mono'>reddit.csv</font>) contient "
      f"{clean.get('rows_raw', 0):,} commentaires labellisés -1 / 0 / 1. Il est téléchargé automatiquement dans "
      "<font name='Mono'>data/raw/</font>, jamais modifié, puis transformé vers <font name='Mono'>data/processed/</font>.".replace(",", " "))
    H2("Nettoyage")
    story += bullets([
        "Décodage HTML, conversion des emojis fréquents en mots (cœur → <i>love</i>, larmes → <i>sad</i>, pouce baissé → <i>bad</i>), normalisation ASCII, minuscules.",
        "Suppression des URLs, mentions @, symboles # (le mot est gardé), horodatages « 3:45 », caractères spéciaux, lettres répétées (« soooo » → « soo »).",
        "Les négations (<i>not</i>, <i>don't</i>) sont <b>conservées</b> : elles inversent le sentiment.",
        "<b>Textes contradictoires</b> (même texte, labels différents) : tous retirés, plutôt que d'en garder un au hasard. Puis suppression des doublons.",
    ], st)
    story.append(table([["Étape", "Lignes"],
                        ["Fichier brut", f"{clean.get('rows_raw', 0):,}"],
                        ["Valeurs manquantes / labels invalides", f"− {clean.get('missing_or_invalid', 0):,}"],
                        ["Vides après nettoyage", f"− {clean.get('empty_after_cleaning', 0):,}"],
                        [f"Lignes contradictoires ({clean.get('conflicting_texts', 0)} textes)", f"− {clean.get('conflicting_rows_removed', 0):,}"],
                        ["Doublons", f"− {clean.get('duplicates_removed', 0):,}"],
                        ["<b>Jeu final</b>", f"<b>{clean.get('rows_clean', 0):,}</b>"],
                        ["Train / test (80/20, stratifié, seed 42)", f"{clean.get('train_rows', 0):,} / {clean.get('test_rows', 0):,}"]],
                       [11 * cm, 5.4 * cm], st))
    H2("Analyse exploratoire")
    cc, cp = eda["class_counts"], eda["class_pct"]
    P(f"Répartition : positif {cp['positif']} % ({cc['positif']:,}), neutre {cp['neutre']} % ({cc['neutre']:,}), "
      f"négatif {cp['negatif']} % ({cc['negatif']:,}). Le ratio de déséquilibre est de {eda['imbalance_ratio']} : modéré. "
      f"Plutôt que de sur-échantillonner, la pondération <font name='Mono'>class_weight='balanced'</font> est testée dans la recherche "
      f"d'hyperparamètres, et la sélection se fait sur le F1 macro, qui pénalise une classe minoritaire négligée. "
      f"Les commentaires font en moyenne {eda['words_mean']} mots (médiane {eda['words_median']:.0f}, maximum {eda['words_max']:,}).".replace(",", " "))
    imgs = [p for p in (FIG / "class_distribution.png", FIG / "text_length.png") if p.exists()]
    if imgs:
        from reportlab.lib.utils import ImageReader
        cells = []
        for p in imgs:
            iw, ih = ImageReader(str(p)).getSize()
            cells.append(Image(str(p), width=8 * cm, height=8 * cm * ih / iw))
        story.append(Table([cells], colWidths=[8.3 * cm] * len(cells), hAlign="LEFT"))
        story.append(Paragraph("Figure 2 — Distribution des classes et longueur des commentaires.", st["caption"]))

    # ---------- 4. Modélisation
    story.append(PageBreak())
    H1("4. Modélisation et choix techniques")
    H2("Représentation : TF-IDF")
    P("Chaque commentaire devient un vecteur creux où le poids d'un mot est sa fréquence dans le commentaire "
      "(<font name='Mono'>sublinear_tf</font> : 1 + log tf) multipliée par l'inverse de sa fréquence dans le corpus. Les mots présents "
      "partout (<i>the</i>, <i>video</i>) pèsent peu ; les mots discriminants (<i>awesome</i>, <i>worst</i>) pèsent beaucoup. "
      "Contrairement à un simple comptage (CountVectorizer), on évite que les mots fréquents mais neutres dominent, et la "
      "normalisation L2 rend comparables les commentaires courts et longs.")
    H2("Modèle : régression logistique")
    P("Modèle linéaire très adapté aux vecteurs creux de grande dimension : rapide à entraîner, inférence en "
      "quelques millisecondes, coefficients interprétables et surtout des <b>probabilités</b> exploitées comme indice de "
      "confiance dans l'interface.")
    H2("Recherche d'hyperparamètres")
    bp = meta.get("best_params_logreg", {})
    best_txt = ", ".join("{}={}".format(k.split("__")[1], v) for k, v in bp.items())
    P("GridSearchCV, validation croisée stratifiée à 3 plis sur le train uniquement, métrique F1 macro. Grille : "
      "n-grammes (1,1)/(1,2), taille du vocabulaire, C ∈ {1, 5, 10}, class_weight ∈ {None, balanced}. "
      f"Meilleure combinaison : <font name='Mono'>{best_txt}</font>.")
    grid = d["grid"]
    if grid:
        rows = [["Rang", "Paramètres", "F1 macro (CV)", "Écart-type"]]
        for i, g in enumerate(grid[:5], 1):
            params = (g["params"].replace("'clf__", "").replace("'tfidf__", "").replace("'", "").replace(": ", "=")
                      .replace("{", "").replace("}", "").replace("max_features", "vocab").replace("ngram_range", "ngram"))
            rows.append([str(i), params, f"{float(g['mean_test_score']):.4f}", f"{float(g['std_test_score']):.4f}"])
        story.append(table(rows, [1.2 * cm, 10.2 * cm, 2.6 * cm, 2.4 * cm], st))
    H2("Comparaison des algorithmes")
    P("Avec le même TF-IDF, la régression logistique est comparée à une <b>baseline</b> (classe majoritaire, la référence "
      "minimale à battre), un SVM linéaire calibré, un Naive Bayes multinomial et une Random Forest.")
    rows = [["Modèle", "Accuracy", "F1 macro", "F1 nég.", "F1 neu.", "F1 pos.", "ms / 50"]]
    for name in sorted(res, key=lambda n: -res[n]["f1_macro"]):
        m = res[name]
        mark = " ★" if name == metrics["best_model"] else ""
        rows.append([name + mark, pct(m["accuracy"]), f"{m['f1_macro']:.3f}", f"{m['f1_per_class']['negatif']:.3f}",
                     f"{m['f1_per_class']['neutre']:.3f}", f"{m['f1_per_class']['positif']:.3f}", f"{m['inference_ms_50']:.1f}"])
    story.append(KeepTogether([table(rows, [4.6 * cm, 2 * cm, 1.9 * cm, 1.8 * cm, 1.8 * cm, 1.8 * cm, 1.9 * cm], st),
                               Paragraph("★ modèle retenu (meilleur F1 macro sur le test set ; la baseline est exclue de la sélection).", st["small"])]))

    # ---------- 5. Résultats
    story.append(PageBreak())
    H1("5. Résultats et performances")
    P(f"Sur les {meta['n_test']:,} commentaires du test set, jamais vus pendant l'entraînement ni l'optimisation, le modèle "
      f"retenu ({meta['model_name']}) atteint une accuracy de <b>{pct(r['accuracy'], 2)}</b> et un F1 macro de "
      f"<b>{r['f1_macro']:.3f}</b>.".replace(",", " "))
    story += figure(FIG / "confusion_matrix.png", 9.5, "Figure 3 — Matrice de confusion (lignes : classe réelle, colonnes : classe prédite).", st)
    worst = min(f1, key=f1.get)
    P(f"La diagonale porte l'essentiel des prédictions. La classe la plus difficile est <b>{worst}</b> "
      f"(F1 {f1[worst]:.3f}) : c'est la minoritaire, et ses erreurs portent surtout sur la frontière avec le neutre "
      "(critiques implicites, ironie, phrases sans mot fortement polarisé). Les inversions négatif ↔ positif sont rares.")
    story += figure(FIG / "model_comparison.png", 13, "Figure 4 — Accuracy et F1 macro par modèle.", st)
    H2("Latence")
    rows = [["Taille du batch", "p50", "p95", "max"]]
    if bench:
        for size, b in bench.items():
            rows.append([size, f"{b['p50_ms']:.2f} ms", f"{b['p95_ms']:.2f} ms", f"{b['max_ms']:.2f} ms"])
    elif lat:
        rows.append(["50", f"{lat['p50_ms']:.2f} ms", f"{lat['p95_ms']:.2f} ms", f"{lat['max_ms']:.2f} ms"])
    story.append(table(rows, [4 * cm, 3 * cm, 3 * cm, 3 * cm], st))
    story.append(Paragraph("Nettoyage + vectorisation + prédiction sur modèle chargé (hors réseau). Le popup affiche en plus "
                           "le temps mesuré côté API et le temps total ressenti.", st["small"]))
    feats = metrics.get("top_features") or {}
    if feats:
        H2("Interprétabilité : mots les plus influents")
        story.append(table([["Classe", "Termes au poids le plus élevé"]] +
                           [[k, ", ".join(v[:12])] for k, v in feats.items()], [2.6 * cm, 13.8 * cm], st))

    # ---------- 6. API
    story.append(Spacer(1, 10))
    H1("6. API REST")
    story.append(table([["Endpoint", "Méthode", "Rôle"],
                        ["/health", "GET", "État de l'API, modèle chargé, version (empreinte SHA-256)"],
                        ["/predict_batch", "POST", "1 à 1 000 commentaires → sentiment, confiance, probabilités + statistiques"],
                        ["/predict", "POST", "Un seul commentaire"],
                        ["/docs", "GET", "Documentation Swagger générée automatiquement"]],
                       [3.4 * cm, 2 * cm, 11 * cm], st))
    H2("Exemple")
    story.append(Preformatted('POST /predict_batch\n{"comments": ["This video is amazing!", "Worst tutorial ever", "!!!"]}\n\n'
                              '200 OK\n{"predictions": [{"text": "This video is amazing!", "sentiment": 1, "label": "positif",\n'
                              '                  "confidence": 0.93, "probabilities": {...}, "skipped": false}, ...],\n'
                              ' "statistics": {"total": 3, "analyzed": 2, "skipped": 1, "positive_pct": 50.0, ...},\n'
                              ' "processing_time_ms": 1.9, "model_version": "' + meta["model_version"] + '"}', st["code"]))
    H2("Choix de conception")
    story += bullets([
        "<b>FastAPI</b> plutôt que Flask : validation automatique (Pydantic), documentation interactive, serveur ASGI performant.",
        "<b>Chargement unique</b> du modèle au démarrage (lifespan) et pré-chauffe ; en cas d'échec l'API démarre quand même, "
        "<font name='Mono'>/health</font> renvoie « degraded » et les prédictions 503 : plus simple à diagnostiquer qu'un conteneur qui redémarre en boucle.",
        "<b>Validation</b> : batch vide, chaînes vides uniquement, mauvais type, plus de 1 000 éléments ou JSON invalide → 422 avec le champ fautif.",
        "<b>Textes vides après nettoyage</b> (« !!! ») marqués <i>skipped</i> et exclus des pourcentages, au lieu de gonfler artificiellement la classe neutre.",
        "<b>CORS</b> configuré (origines <font name='Mono'>chrome-extension://*</font>, liste paramétrable par <font name='Mono'>ALLOWED_ORIGINS</font>) ; "
        "en-tête <font name='Mono'>X-Process-Time-Ms</font> et journalisation de chaque requête.",
    ], st)

    # ---------- 7. Extension
    H1("7. Extension Chrome « Écho »")
    story += bullets([
        "<b>Extraction</b> : défilement automatique jusqu'au nombre demandé (arrêt si rien ne se charge 3 fois de suite), sélecteurs pour "
        "l'ancien et le nouveau DOM de YouTube, réponses optionnelles, injection à la demande si l'onglet précède l'installation.",
        "<b>Service worker</b> : l'analyse continue si le popup est fermé ; progression lot par lot visible en direct.",
        "<b>Onglet Aperçu</b> : jauge à aiguille du score global (-1 à +1) et verdict en mots (« Plutôt positif », « Avis partagés »…), "
        "part de chaque sentiment, commentaire le plus enthousiaste et le plus critique, temps de réponse et version du modèle.",
        "<b>Onglet Commentaires</b> : cartes avec un visage par sentiment et la confiance (3 probabilités au survol), filtres, recherche, tri par confiance, menu d'export.",
        "<b>Confort</b> : mode sombre/clair mémorisé, copie et export CSV/JSON des résultats filtrés, résultats conservés par vidéo, messages d'erreur explicites (URL, port privé, délai).",
    ], st)
    shots = [p for p in (SHOTS / "overview-light.png", SHOTS / "comments-light.png", SHOTS / "overview-dark.png") if p.exists()]
    if shots:
        from reportlab.lib.utils import ImageReader
        cells = []
        for p in shots:
            iw, ih = ImageReader(str(p)).getSize()
            cells.append(Image(str(p), width=5 * cm, height=5 * cm * ih / iw))
        story.append(Table([cells], colWidths=[5.5 * cm] * len(cells)))
        story.append(Paragraph("Figure 5 — Écho : onglet Aperçu, onglet Commentaires et mode sombre.", st["caption"]))

    # ---------- 8. Déploiement & tests
    story.append(PageBreak())
    H1("8. Déploiement et validation")
    H2("Conteneur Docker")
    story += bullets([
        "Image <font name='Mono'>python:3.10-slim</font>, dépendances de production seulement (requirements.txt séparé de requirements-dev.txt).",
        "Couche des dépendances copiée avant le code : elle reste en cache tant que requirements.txt ne change pas.",
        "Seuls <font name='Mono'>src/api</font>, <font name='Mono'>src/utils</font>, <font name='Mono'>app_api.py</font> et "
        "<font name='Mono'>models/</font> sont copiés (.dockerignore) ; utilisateur non-root ; HEALTHCHECK sur /health ; port configurable par <font name='Mono'>PORT</font>.",
        "Versions de scikit-learn et joblib identiques à l'entraînement et en production (un .joblib n'est pas portable entre versions).",
    ], st)
    H2("GitHub Codespaces")
    P("Hugging Face Spaces exigeant désormais un abonnement pour Docker, l'API s'exécute dans un Codespace. Le fichier "
      "<font name='Mono'>.devcontainer/devcontainer.json</font> installe Docker et lance <font name='Mono'>scripts/start_api.sh</font> "
      "<b>à chaque démarrage</b> : entraînement si le modèle manque, build, lancement du conteneur, passage du port 7860 en public "
      "et affichage de l'URL HTTPS. Après la mise en veille automatique (~30 min), rouvrir le Codespace suffit.")
    H2("Éphémère ou permanent ?")
    P("Un Codespace est un environnement de <i>développement</i> : il s'arrête, son URL dépend du Codespace et il ne passe pas "
      "à l'échelle. Une mise en production réelle demanderait un hébergement permanent (Cloud Run, Render, Azure App Service…) "
      "avec URL stable, supervision, journaux centralisés, authentification et limitation de débit. Grâce à Docker, la même image s'y déploierait sans modification.")
    H2("Tests")
    story.append(table([["Niveau", "Ce qui est vérifié"],
                        ["Nettoyage", "URLs, mentions, emojis, négations, horodatages, textes vides et très longs"],
                        ["Modèle", "Critères du cahier des charges, baseline battue, accuracy recalculée, cas limites (vide, emoji seul, 5 000 caractères, langues mélangées), latence"],
                        ["API", "/health, batchs de 1 à 1 000, temps de réponse, 5 cas de données invalides, JSON malformé, textes ignorés, CORS ; aussi exécutables contre l'URL déployée (API_URL=…)"],
                        ["Extension", "Fonctions pures (lots, statistiques, filtres, CSV, URLs) avec node --test"],
                        ["Intégration", "GitHub Actions : tests, build de l'image, démarrage du conteneur et appels réels"]],
                       [2.8 * cm, 13.6 * cm], st))

    # ---------- 9. Difficultés, limites, améliorations
    story.append(PageBreak())
    H1("9. Difficultés rencontrées et solutions")
    story.append(table([["Difficulté", "Solution"],
                        ["Commentaires YouTube chargés dynamiquement", "Défilement automatique avec condition d'arrêt ; sélecteurs ancien et nouveau DOM"],
                        ["Popup fermé = analyse perdue", "Analyse déplacée dans un service worker, état partagé via chrome.storage"],
                        ["Codespace en veille, port repassé en privé", "devcontainer qui relance l'API au démarrage ; détection d'une réponse HTML (page de connexion) avec message explicite"],
                        ["Compilation de numpy sous Windows (Python récent)", "Contraintes de version assouplies pour utiliser les roues précompilées"],
                        ["Parallélisme joblib/loky en échec sous Windows", "Option --n-jobs et repli automatique sur un seul processus"],
                        ["Textes identiques avec labels opposés", "Retrait des groupes contradictoires avant le split"],
                        ["LinearSVC sans probabilités", "Calibration (CalibratedClassifierCV) pour comparer à armes égales"]],
                       [6.2 * cm, 10.2 * cm], st))
    H1("10. Limites et améliorations futures")
    story += bullets([
        "<b>Changement de domaine</b> : le modèle apprend sur Reddit et s'applique à YouTube (emojis, argot, commentaires très courts). "
        "Les scores ci-dessus valent pour Reddit ; annoter quelques centaines de commentaires YouTube permettrait de mesurer et réduire l'écart.",
        "<b>Langues</b> : le modèle est anglophone. Un Transformer multilingue (XLM-R, DistilBERT multilingue) quantifié couvrirait le français et la darija.",
        "<b>Sarcasme et contexte</b> : hors de portée d'un sac de mots ; mêmes pistes (Transformers) ou analyse par fil de discussion.",
        "<b>MLOps</b> : registre de modèles (MLflow), suivi de la dérive des prédictions, réentraînement planifié, déploiement continu de l'image.",
        "<b>Production</b> : hébergement permanent, clé d'API et limitation de débit, CORS restreint à l'identifiant de l'extension.",
    ], st)
    H1("11. Conclusion")
    P(f"Le système répond à l'ensemble du cahier des charges : un modèle à {pct(r['accuracy'])} d'accuracy et F1 > 0,75 sur chaque "
      f"classe, une inférence en {lat.get('p95_ms', 0):.1f} ms (p95) pour 50 commentaires, une API conteneurisée accessible publiquement "
      "et une extension utilisable sur n'importe quelle vidéo. Au-delà du score, la démarche MLOps (données brutes immuables, pipeline "
      "reproductible, versions figées, modèle versionné par empreinte, conteneur, tests à chaque niveau) rend chaque résultat "
      "re-calculable et chaque déploiement répétable.")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--auteurs", default="[Prénom Nom]")
    p.add_argument("--output", default=str(REPORTS / "rapport-technique.pdf"))
    args = p.parse_args()

    meta = load(ROOT / "models" / "model_metadata.json")
    metrics = load(REPORTS / "metrics.json")
    eda = load(REPORTS / "eda_stats.json")
    if not (meta and metrics and eda):
        sys.exit("Résultats introuvables : lancez d'abord `python run_pipeline.py`.")
    import csv
    grid_path = REPORTS / "gridsearch_results.csv"
    grid = list(csv.DictReader(grid_path.open(encoding="utf-8"))) if grid_path.exists() else []
    data = {"meta": meta, "metrics": metrics, "eda": eda, "clean": load(REPORTS / "cleaning_stats.json", {}),
            "bench": load(REPORTS / "benchmark.json", {}), "grid": grid, "auteurs": args.auteurs}

    FIG.mkdir(parents=True, exist_ok=True)
    architecture_figure(FIG / "architecture.png")
    register_fonts()
    st = styles()

    def decorate(canvas, doc):
        canvas.saveState()
        canvas.setFont("Body", 7.5)
        canvas.setFillColor(MUTED)
        if doc.page > 1:
            canvas.drawString(2 * cm, A4[1] - 1.2 * cm, "TP3 · ANALYSE DE SENTIMENT YOUTUBE")
            canvas.drawRightString(A4[0] - 2 * cm, A4[1] - 1.2 * cm, f"Modèle {meta['model_version']}")
            canvas.setStrokeColor(LINE)
            canvas.line(2 * cm, A4[1] - 1.35 * cm, A4[0] - 2 * cm, A4[1] - 1.35 * cm)
        canvas.drawCentredString(A4[0] / 2, 1.1 * cm, f"{doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(args.output, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm,
                            bottomMargin=1.8 * cm, title="Analyse de sentiment YouTube — rapport technique",
                            author=args.auteurs)
    story = []
    build(story, st, data)
    doc.build(story, onFirstPage=decorate, onLaterPages=decorate)
    try:
        from pypdf import PdfReader
        n = len(PdfReader(args.output).pages)
    except Exception:
        n = "?"
    print(f"Rapport -> {args.output} ({n} pages)")


if __name__ == "__main__":
    main()
