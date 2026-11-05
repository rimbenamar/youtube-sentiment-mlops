"""Tests du modèle : performance sur le test set, cas limites, temps d'inférence."""
import json
import time

import pandas as pd
import pytest

from src.api.predictor import SentimentPredictor
from src.utils.config import (METADATA_PATH, TARGET_ACCURACY, TARGET_F1_PER_CLASS, TARGET_INFERENCE_MS_50,
                              TEST_PATH)
from tests.conftest import requires_model

pytestmark = requires_model


@pytest.fixture(scope="module")
def predictor():
    return SentimentPredictor().load()


def test_metadata_meets_criteria():
    meta = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    m = meta["metrics"]
    assert meta["latency_50_comments"]["p95_ms"] < TARGET_INFERENCE_MS_50
    assert m["f1_macro"] > meta["baseline"]["f1_macro"] + 0.2, "le modèle doit battre nettement la baseline"
    assert m["accuracy"] >= TARGET_ACCURACY, f"accuracy {m['accuracy']} < {TARGET_ACCURACY}"
    for cls, f1 in m["f1_per_class"].items():
        assert f1 > TARGET_F1_PER_CLASS, f"F1 {cls} = {f1}"


@pytest.mark.skipif(not TEST_PATH.exists(), reason="test set absent")
def test_accuracy_on_test_set(predictor):
    df = pd.read_csv(TEST_PATH).dropna()
    preds = [p["sentiment"] for p in predictor.predict(df["text"].astype(str).tolist())]
    acc = (pd.Series(preds) == df["label"].astype(int).values).mean()
    assert acc >= TARGET_ACCURACY


@pytest.mark.parametrize("text", [
    "", "a", "!!!", "😀", "🔥🔥🔥", "ok", "x" * 5000, "good " * 2000,
    "C'est génial, j'adore ❤️", "this is bueno muy bien 👍", "1:23 lol", "@user https://t.co/x",
])
def test_edge_cases_do_not_crash(predictor, text):
    out = predictor.predict([text])[0]
    assert out["sentiment"] in (-1, 0, 1)
    assert 0.0 <= out["confidence"] <= 1.0


def test_probabilities_sum_to_one(predictor):
    out = predictor.predict(["I really love this video"])[0]
    assert abs(sum(out["probabilities"].values()) - 1.0) < 1e-3


def test_inference_time_batch_50(predictor):
    batch = ["This video is great, thanks a lot!", "worst content ever", "what mic do you use?"] * 17
    batch = batch[:50]
    predictor.predict(batch)  # warm-up
    times = []
    for _ in range(20):
        t0 = time.perf_counter()
        predictor.predict(batch)
        times.append((time.perf_counter() - t0) * 1000)
    times.sort()
    assert times[len(times) // 2] < TARGET_INFERENCE_MS_50


def test_statistics():
    preds = [{"sentiment": 1, "confidence": 0.9}, {"sentiment": 1, "confidence": 0.7},
             {"sentiment": -1, "confidence": 0.8}, {"sentiment": 0, "confidence": 0.6}]
    s = SentimentPredictor.statistics(preds + [{"sentiment": 0, "confidence": 0.0, "skipped": True}])
    assert s["total"] == 5 and s["skipped"] == 1 and s["analyzed"] == 4 and s["positive"] == 2 and s["negative"] == 1 and s["neutral"] == 1
    assert s["positive_pct"] == 50.0 and s["dominant"] == "positif"
    assert s["sentiment_score"] == 0.25
