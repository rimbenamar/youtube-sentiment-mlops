"""Benchmark de latence : temps pour nettoyer + vectoriser + prédire un batch de 50 commentaires.

On mesure sur un modèle « chaud » (déjà chargé) et on rapporte la médiane (p50) et le p95 :
le p95 dit « 95 % des batchs sont plus rapides que ça », plus exigeant qu'une moyenne.

    python -m src.models.benchmark            # sur les modèles sauvegardés
"""
import json
import time

import numpy as np

from src.utils.text_cleaning import clean_text

COMMENTS = [
    "This video is amazing, thank you so much for the clear explanation!",
    "worst tutorial ever, total waste of time",
    "what camera do you use?",
    "I love this channel ❤️ keep going",
    "this is so boring and the audio is terrible",
    "first",
    "Great explanation, very clear and helpful 👍",
    "I hate the music in the background, can't hear anything",
    "Can you make a video about docker compose next?",
    "Not bad at all, pretty good actually",
]


def benchmark_latency(vectorizer, model, batch_size: int = 50, runs: int = 200) -> dict:
    batch = (COMMENTS * (batch_size // len(COMMENTS) + 1))[:batch_size]
    for _ in range(5):  # échauffement
        model.predict_proba(vectorizer.transform([clean_text(t) for t in batch]))
    times = []
    for _ in range(runs):
        t0 = time.perf_counter()
        model.predict_proba(vectorizer.transform([clean_text(t) for t in batch]))
        times.append((time.perf_counter() - t0) * 1000)
    arr = np.array(times)
    return {
        "batch_size": batch_size,
        "runs": runs,
        "mean_ms": round(float(arr.mean()), 3),
        "p50_ms": round(float(np.percentile(arr, 50)), 3),
        "p95_ms": round(float(np.percentile(arr, 95)), 3),
        "max_ms": round(float(arr.max()), 3),
    }


def main():
    from src.api.predictor import SentimentPredictor
    from src.utils.config import REPORTS_DIR

    p = SentimentPredictor().load()
    res = {size: benchmark_latency(p.vectorizer, p.model, batch_size=size, runs=100) for size in (1, 50, 250, 1000)}
    print(f"{'batch':>6} {'p50 (ms)':>10} {'p95 (ms)':>10} {'max (ms)':>10}")
    for size, r in res.items():
        print(f"{size:>6} {r['p50_ms']:>10.2f} {r['p95_ms']:>10.2f} {r['max_ms']:>10.2f}")
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    (REPORTS_DIR / "benchmark.json").write_text(json.dumps(res, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
