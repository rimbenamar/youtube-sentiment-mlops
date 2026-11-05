"""Évaluation : métriques, matrice de confusion, temps d'inférence, rapports."""
import json
import time

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from sklearn.metrics import (accuracy_score, classification_report, confusion_matrix,  # noqa: E402
                             f1_score, precision_score, recall_score)

from src.utils.config import FIGURES_DIR, LABELS, LABEL_ORDER, REPORTS_DIR  # noqa: E402
from src.utils.text_cleaning import clean_text  # noqa: E402

SAMPLE_COMMENTS = [
    "This video is amazing, thank you so much!", "worst tutorial ever, total waste of time",
    "what camera do you use?", "I love this channel", "this is so boring and stupid",
    "first", "Great explanation, very clear and helpful", "I hate the music in the background",
    "Can you make a video about docker?", "Not bad at all, pretty good actually",
]


def measure_inference_ms(model, n: int = 50, repeats: int = 30) -> float:
    """Temps médian (ms) pour nettoyer + prédire un batch de n commentaires bruts."""
    batch = (SAMPLE_COMMENTS * (n // len(SAMPLE_COMMENTS) + 1))[:n]
    model.predict_proba([clean_text(t) for t in batch])  # warm-up
    times = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        model.predict_proba([clean_text(t) for t in batch])
        times.append((time.perf_counter() - t0) * 1000)
    return float(np.median(times))


def evaluate_model(model, X_test, y_test) -> dict:
    y_pred = model.predict(X_test)
    f1_per = f1_score(y_test, y_pred, labels=LABEL_ORDER, average=None, zero_division=0)
    return {
        "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
        "f1_macro": round(float(f1_score(y_test, y_pred, average="macro", zero_division=0)), 4),
        "f1_weighted": round(float(f1_score(y_test, y_pred, average="weighted", zero_division=0)), 4),
        "precision_macro": round(float(precision_score(y_test, y_pred, average="macro", zero_division=0)), 4),
        "recall_macro": round(float(recall_score(y_test, y_pred, average="macro", zero_division=0)), 4),
        "f1_per_class": {LABELS[lab]: round(float(v), 4) for lab, v in zip(LABEL_ORDER, f1_per)},
        "inference_ms_50": round(measure_inference_ms(model), 2),
    }


def plot_confusion(model, X_test, y_test, path):
    y_pred = model.predict(X_test)
    cm = confusion_matrix(y_test, y_pred, labels=LABEL_ORDER)
    cm_norm = cm / cm.sum(axis=1, keepdims=True)
    names = [LABELS[label] for label in LABEL_ORDER]
    fig, ax = plt.subplots(figsize=(5.5, 4.5))
    im = ax.imshow(cm_norm, cmap="Blues", vmin=0, vmax=1)
    for i in range(3):
        for j in range(3):
            ax.text(j, i, f"{cm[i, j]}\n{cm_norm[i, j]:.1%}", ha="center", va="center",
                    color="white" if cm_norm[i, j] > 0.5 else "black", fontsize=10)
    ax.set_xticks(range(3), names)
    ax.set_yticks(range(3), names)
    ax.set_xlabel("Prédit")
    ax.set_ylabel("Réel")
    ax.set_title("Matrice de confusion (test set)")
    fig.colorbar(im, ax=ax, fraction=0.046)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return cm


def plot_comparison(results: dict, path):
    names = sorted(results, key=lambda n: -results[n]["f1_macro"])
    x = np.arange(len(names))
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.bar(x - 0.2, [results[n]["accuracy"] for n in names], 0.4, label="Accuracy", color="#264653")
    ax.bar(x + 0.2, [results[n]["f1_macro"] for n in names], 0.4, label="F1 macro", color="#2a9d8f")
    ax.axhline(0.80, ls="--", color="#d1495b", lw=1, label="Seuil 0.80")
    ax.set_xticks(x, names, rotation=10)
    ax.set_ylim(0.0, 1.0)
    ax.set_title("Comparaison des modèles (test set)")
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def top_features(model, k: int = 15) -> dict:
    """Mots les plus influents par classe (uniquement pour la régression logistique)."""
    clf = model.named_steps["clf"]
    if not hasattr(clf, "coef_"):
        return {}
    vocab = np.array(model.named_steps["tfidf"].get_feature_names_out())
    return {LABELS[lab]: vocab[np.argsort(clf.coef_[i])[-k:][::-1]].tolist()
            for i, lab in enumerate(clf.classes_)}


def save_reports(results, best_name, best_model, X_test, y_test, cv_results):
    cm = plot_confusion(best_model, X_test, y_test, FIGURES_DIR / "confusion_matrix.png")
    plot_comparison(results, FIGURES_DIR / "model_comparison.png")
    report_txt = classification_report(y_test, best_model.predict(X_test), labels=LABEL_ORDER,
                                       target_names=[LABELS[label] for label in LABEL_ORDER], digits=4)
    (REPORTS_DIR / "classification_report.txt").write_text(report_txt, encoding="utf-8")
    cv_results.assign(params=cv_results["params"].astype(str)).to_csv(
        REPORTS_DIR / "gridsearch_results.csv", index=False)
    feats = top_features(best_model)
    payload = {"best_model": best_name, "results": results, "confusion_matrix": cm.tolist(),
               "labels_order": [LABELS[label] for label in LABEL_ORDER], "top_features": feats}
    (REPORTS_DIR / "metrics.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    # Rapport de performance lisible (livrable « Rapport de performance »)
    lines = ["# Rapport de performance du modèle", "",
             f"**Modèle retenu : {best_name}** (critère : F1 macro sur le test set)", "",
             "## Comparaison des modèles", "",
             "| Modèle | Accuracy | F1 macro | F1 négatif | F1 neutre | F1 positif | Inférence 50 commentaires (ms) |",
             "|---|---|---|---|---|---|---|"]
    for n in sorted(results, key=lambda n: -results[n]["f1_macro"]):
        m = results[n]
        f = m["f1_per_class"]
        lines.append(f"| {n} | {m['accuracy']:.4f} | {m['f1_macro']:.4f} | {f['negatif']:.4f} | "
                     f"{f['neutre']:.4f} | {f['positif']:.4f} | {m['inference_ms_50']:.1f} |")
    lines += ["", "## Rapport de classification (modèle retenu)", "", "```", report_txt, "```", "",
              "## Matrice de confusion", "", "![Matrice de confusion](figures/confusion_matrix.png)", "",
              "![Comparaison](figures/model_comparison.png)", "",
              "## Meilleurs hyperparamètres (GridSearchCV, 5 premiers)", "",
              "| Paramètres | F1 macro CV | Écart-type |", "|---|---|---|"]
    for _, row in cv_results.head(5).iterrows():
        lines.append(f"| `{row['params']}` | {row['mean_test_score']:.4f} | {row['std_test_score']:.4f} |")
    if feats:
        lines += ["", "## Mots les plus influents par classe (LogReg)", ""]
        for lab, words in feats.items():
            lines.append(f"- **{lab}** : {', '.join(words)}")
    (REPORTS_DIR / "performance_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
