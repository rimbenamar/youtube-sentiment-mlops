"""Phase 3 - Entraînement, comparaison et optimisation des modèles.

1. TF-IDF + Logistic Regression optimisés ensemble par GridSearchCV (f1_macro, CV 3 folds)
2. Comparaison avec d'autres algorithmes (SVM linéaire calibré, Naive Bayes, Random Forest)
   en réutilisant les meilleurs paramètres TF-IDF
3. Évaluation sur le test set (accuracy, F1 par classe, matrice de confusion, temps d'inférence)
4. Sauvegarde du meilleur modèle + vectoriseur avec joblib

Usage :
    python -m src.models.train          # recherche complète (~quelques minutes)
    python -m src.models.train --fast   # grille réduite, sans Random Forest
"""
import argparse
import hashlib
import json
import os
import platform
import time
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.calibration import CalibratedClassifierCV
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GridSearchCV, StratifiedKFold
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

from src.models.benchmark import benchmark_latency
from src.models.evaluate import evaluate_model, save_reports
from src.utils.config import (LABELS, METADATA_PATH, MODEL_PATH, RANDOM_STATE, TARGET_ACCURACY,
                              TARGET_F1_PER_CLASS, TARGET_INFERENCE_MS_50, TEST_PATH, TRAIN_PATH,
                              VECTORIZER_PATH, ensure_dirs)
from src.utils.logger import get_logger

logger = get_logger("train", "pipeline.log")
BASELINE = "Baseline (majoritaire)"

# Nombre de processus parallèles (-1 = tous les cœurs). Modifiable par --n-jobs ou la variable N_JOBS.
N_JOBS = int(os.getenv("N_JOBS", "-1"))


def load_split():
    train = pd.read_csv(TRAIN_PATH).dropna()
    test = pd.read_csv(TEST_PATH).dropna()
    return (train["text"].astype(str), train["label"].astype(int),
            test["text"].astype(str), test["label"].astype(int))


def tune_logreg(X, y, fast: bool):
    pipe = Pipeline([
        ("tfidf", TfidfVectorizer(sublinear_tf=True, min_df=2, max_df=0.95, strip_accents="unicode")),
        ("clf", LogisticRegression(max_iter=3000, random_state=RANDOM_STATE)),
    ])
    if fast:
        grid = {
            "tfidf__ngram_range": [(1, 2)],
            "tfidf__max_features": [30000],
            "clf__C": [1.0, 10.0],
            "clf__class_weight": [None, "balanced"],
        }
    else:
        grid = {
            "tfidf__ngram_range": [(1, 1), (1, 2)],
            "tfidf__max_features": [20000, 50000],
            "clf__C": [1.0, 5.0, 10.0],
            "clf__class_weight": [None, "balanced"],
        }
    cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=RANDOM_STATE)
    t0 = time.perf_counter()
    try:
        search = GridSearchCV(pipe, grid, scoring="f1_macro", cv=cv, n_jobs=N_JOBS, verbose=1, refit=True)
        search.fit(X, y)
    except Exception as exc:
        if N_JOBS == 1:
            raise
        # Sous Windows, le lancement de processus parallèles (joblib/loky) échoue parfois
        # (erreurs « when serializing ... LokyProcess »). On relance sans parallélisme.
        logger.warning("Calcul parallèle impossible (%s) -> nouvel essai avec n_jobs=1", type(exc).__name__)
        search = GridSearchCV(pipe, grid, scoring="f1_macro", cv=cv, n_jobs=1, verbose=1, refit=True)
        search.fit(X, y)
    logger.info("GridSearch LogReg terminée en %.1fs - meilleur f1_macro CV = %.4f",
                time.perf_counter() - t0, search.best_score_)
    logger.info("Meilleurs paramètres : %s", search.best_params_)
    cv_results = pd.DataFrame(search.cv_results_)[["params", "mean_test_score", "std_test_score", "mean_fit_time"]]
    cv_results = cv_results.sort_values("mean_test_score", ascending=False)
    return search.best_estimator_, search.best_params_, float(search.best_score_), cv_results


def other_candidates(tfidf_params: dict, fast: bool):
    """Autres algorithmes, avec le même TF-IDF que le meilleur modèle LogReg."""
    def tfidf(**override):
        params = dict(sublinear_tf=True, min_df=2, max_df=0.95, strip_accents="unicode", **tfidf_params)
        params.update(override)
        return TfidfVectorizer(**params)

    cands = {
        # Référence minimale : prédit toujours la classe majoritaire. Tout modèle utile doit la battre nettement.
        BASELINE: Pipeline([("tfidf", tfidf()), ("clf", DummyClassifier(strategy="most_frequent"))]),
        # LinearSVC n'a pas de predict_proba : on le calibre pour obtenir une confiance utilisable par l'API
        "LinearSVC (calibré)": Pipeline([
            ("tfidf", tfidf()),
            ("clf", CalibratedClassifierCV(LinearSVC(C=0.5, class_weight="balanced",
                                                     random_state=RANDOM_STATE), cv=3)),
        ]),
        "MultinomialNB": Pipeline([("tfidf", tfidf()), ("clf", MultinomialNB(alpha=0.1))]),
    }
    if not fast:
        cands["RandomForest"] = Pipeline([
            ("tfidf", tfidf(max_features=10000)),
            ("clf", RandomForestClassifier(n_estimators=200, n_jobs=N_JOBS, class_weight="balanced",
                                           random_state=RANDOM_STATE)),
        ])
    return cands


def main(argv=None):
    p = argparse.ArgumentParser(description="Entraîne et sauvegarde le modèle de sentiment")
    p.add_argument("--fast", action="store_true", help="grille réduite, sans Random Forest")
    p.add_argument("--n-jobs", type=int, default=None, help="processus parallèles (1 = désactive, conseillé si erreur sous Windows)")
    args = p.parse_args(argv)
    global N_JOBS
    if args.n_jobs is not None:
        N_JOBS = args.n_jobs
    ensure_dirs()

    X_train, y_train, X_test, y_test = load_split()
    logger.info("Train : %d | Test : %d", len(X_train), len(X_test))

    results, fitted = {}, {}

    # 1. Logistic Regression (modèle de référence du cahier des charges) + GridSearch
    best_lr, best_params, cv_score, cv_results = tune_logreg(X_train, y_train, args.fast)
    fitted["LogisticRegression"] = best_lr
    results["LogisticRegression"] = evaluate_model(best_lr, X_test, y_test)
    results["LogisticRegression"]["cv_f1_macro"] = round(cv_score, 4)

    # 2. Autres algorithmes
    tfidf_params = {k.replace("tfidf__", ""): v for k, v in best_params.items() if k.startswith("tfidf__")}
    for name, pipe in other_candidates(tfidf_params, args.fast).items():
        t0 = time.perf_counter()
        pipe.fit(X_train, y_train)
        fitted[name] = pipe
        results[name] = evaluate_model(pipe, X_test, y_test)
        results[name]["fit_time_s"] = round(time.perf_counter() - t0, 2)
        logger.info("%-22s acc=%.4f f1_macro=%.4f", name, results[name]["accuracy"], results[name]["f1_macro"])

    # 3. Sélection du meilleur (F1 macro sur le test set)
    best_name = max((n for n in results if n != BASELINE), key=lambda n: results[n]["f1_macro"])
    best = fitted[best_name]
    r = results[best_name]
    logger.info("Meilleur modèle : %s (acc=%.4f, f1_macro=%.4f)", best_name, r["accuracy"], r["f1_macro"])

    # 4. Sauvegarde : vectoriseur et modèle séparés (comme demandé)
    joblib.dump(best.named_steps["tfidf"], VECTORIZER_PATH, compress=3)
    joblib.dump(best.named_steps["clf"], MODEL_PATH, compress=3)
    # Version = empreinte SHA-256 des artefacts : deux modèles identiques ont la même version,
    # et la version affichée par l'API prouve quel fichier est réellement servi.
    digest = hashlib.sha256(VECTORIZER_PATH.read_bytes() + MODEL_PATH.read_bytes()).hexdigest()
    latency = benchmark_latency(best.named_steps["tfidf"], best.named_steps["clf"])
    logger.info("Latence (50 commentaires) : p50=%.2f ms, p95=%.2f ms", latency["p50_ms"], latency["p95_ms"])

    criteria = {
        "accuracy>=0.80": r["accuracy"] >= TARGET_ACCURACY,
        "f1_par_classe>0.75": all(v > TARGET_F1_PER_CLASS for v in r["f1_per_class"].values()),
        "inference_50<100ms": latency["p95_ms"] < TARGET_INFERENCE_MS_50,
    }
    metadata = {
        "model_name": best_name,
        "model_version": digest[:12],
        "artifacts_sha256": digest,
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "labels": {str(k): v for k, v in LABELS.items()},
        "best_params_logreg": {k: (list(v) if isinstance(v, tuple) else v) for k, v in best_params.items()},
        "vocabulary_size": int(len(best.named_steps["tfidf"].vocabulary_)),
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "metrics": r,
        "latency_50_comments": latency,
        "baseline": results.get(BASELINE),
        "criteria": criteria,
        "sklearn_version": sklearn.__version__,
        "python_version": platform.python_version(),
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    save_reports(results, best_name, best, X_test, y_test, cv_results)

    print("\n================ RÉSULTATS ================")
    print(f"{'Modèle':<22}{'Accuracy':>10}{'F1 macro':>10}{'ms/50':>8}")
    for name, m in sorted(results.items(), key=lambda kv: -kv[1]["f1_macro"]):
        mark = "  <- retenu" if name == best_name else ""
        print(f"{name:<22}{m['accuracy']:>10.4f}{m['f1_macro']:>10.4f}{m['inference_ms_50']:>8.1f}{mark}")
    print(f"\nLatence 50 commentaires : p50 {latency['p50_ms']:.2f} ms | p95 {latency['p95_ms']:.2f} ms")
    print("F1 par classe (modèle retenu) :", {k: round(v, 4) for k, v in r["f1_per_class"].items()})
    print("Critères du cahier des charges :")
    for k, ok in criteria.items():
        print(f"  [{'OK' if ok else 'KO'}] {k}")
    print(f"Version du modèle : {digest[:12]}")
    print(f"\nModèle      -> {MODEL_PATH}\nVectoriseur -> {VECTORIZER_PATH}")
    print("===========================================\n")
    return metadata


if __name__ == "__main__":
    np.random.seed(RANDOM_STATE)
    main()
