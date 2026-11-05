"""Service de prédiction : charge le modèle une seule fois et prédit par batch.

Indépendant de FastAPI pour pouvoir être testé et réutilisé seul.
"""
import json
import os
import threading
from pathlib import Path
from typing import Dict, List

import joblib
import numpy as np

from src.utils.config import LABELS, METADATA_PATH, MODEL_PATH, VECTORIZER_PATH
from src.utils.text_cleaning import clean_text


class SentimentPredictor:
    def __init__(self, model_path: Path = None, vectorizer_path: Path = None, metadata_path: Path = None):
        self.model_path = Path(model_path or os.getenv("MODEL_PATH", MODEL_PATH))
        self.vectorizer_path = Path(vectorizer_path or os.getenv("VECTORIZER_PATH", VECTORIZER_PATH))
        self.metadata_path = Path(metadata_path or METADATA_PATH)
        self.model = None
        self.vectorizer = None
        self.metadata: Dict = {}
        self._lock = threading.Lock()

    @property
    def is_loaded(self) -> bool:
        return self.model is not None and self.vectorizer is not None

    def load(self) -> "SentimentPredictor":
        with self._lock:
            if self.is_loaded:
                return self
            for p in (self.model_path, self.vectorizer_path):
                if not p.exists():
                    raise FileNotFoundError(f"Fichier introuvable : {p}. Lancez d'abord `python run_pipeline.py`.")
            self.vectorizer = joblib.load(self.vectorizer_path)
            self.model = joblib.load(self.model_path)
            if self.metadata_path.exists():
                self.metadata = json.loads(self.metadata_path.read_text(encoding="utf-8"))
            # Pré-chauffe (première prédiction plus lente sinon)
            self.model.predict_proba(self.vectorizer.transform(["warm up"]))
        return self

    def predict(self, texts: List[str]) -> List[Dict]:
        if not self.is_loaded:
            raise RuntimeError("Modèle non chargé")
        cleaned = [clean_text(t) for t in texts]
        proba = self.model.predict_proba(self.vectorizer.transform(cleaned))
        classes = [int(c) for c in self.model.classes_]
        out = []
        for text, cl, p in zip(texts, cleaned, proba):
            if not cl:  # ex. « !!! » : rien à analyser -> ignoré et exclu des pourcentages
                out.append({"text": text, "sentiment": 0, "label": "ignore", "confidence": 0.0,
                            "probabilities": {LABELS[c]: 0.0 for c in classes}, "skipped": True})
                continue
            i = int(np.argmax(p))
            out.append({
                "text": text,
                "sentiment": classes[i],
                "label": LABELS[classes[i]],
                "confidence": round(float(p[i]), 4),
                "probabilities": {LABELS[c]: round(float(v), 4) for c, v in zip(classes, p)},
                "skipped": False,
            })
        return out

    @staticmethod
    def statistics(preds: List[Dict]) -> Dict:
        analyzed = [p for p in preds if not p.get("skipped")]
        n = len(analyzed)
        pos = sum(1 for p in analyzed if p["sentiment"] == 1)
        neu = sum(1 for p in analyzed if p["sentiment"] == 0)
        neg = sum(1 for p in analyzed if p["sentiment"] == -1)
        pct = (lambda k: round(100.0 * k / n, 2)) if n else (lambda k: 0.0)
        counts = {"positif": pos, "neutre": neu, "negatif": neg}
        return {
            "total": len(preds), "analyzed": n, "skipped": len(preds) - n,
            "positive": pos, "neutral": neu, "negative": neg,
            "positive_pct": pct(pos), "neutral_pct": pct(neu), "negative_pct": pct(neg),
            "average_confidence": round(sum(p["confidence"] for p in analyzed) / n, 4) if n else 0.0,
            "sentiment_score": round((pos - neg) / n, 4) if n else 0.0,
            "dominant": max(counts, key=counts.get) if n else "aucun",
        }
