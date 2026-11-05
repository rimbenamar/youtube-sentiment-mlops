"""Tests de l'API FastAPI (TestClient, sans lancer de serveur).

Pour tester l'API déployée :  API_URL=https://<nom>-7860.app.github.dev pytest tests/test_api.py
"""
import os
import time

import pytest

from tests.conftest import requires_model

pytestmark = requires_model

API_URL = os.getenv("API_URL")


@pytest.fixture(scope="module")
def client():
    if API_URL:  # test d'intégration contre l'API déployée
        import httpx
        with httpx.Client(base_url=API_URL.rstrip("/"), timeout=30) as c:
            yield c
    else:
        from fastapi.testclient import TestClient

        from src.api.main import app
        with TestClient(app) as c:  # déclenche le lifespan (chargement du modèle)
            yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok" and body["model_loaded"] is True


def test_root(client):
    assert client.get("/").status_code == 200


@pytest.mark.parametrize("n", [1, 10, 50, 200, 1000])
def test_predict_batch_sizes(client, n):
    comments = [f"comment {i}: this video is great" if i % 3 == 0 else
                f"comment {i}: I hate this boring video" if i % 3 == 1 else
                f"comment {i}: what time is it" for i in range(n)]
    r = client.post("/predict_batch", json={"comments": comments})
    assert r.status_code == 200
    body = r.json()
    assert len(body["predictions"]) == n
    s = body["statistics"]
    assert s["total"] == n
    assert s["positive"] + s["neutral"] + s["negative"] + s["skipped"] == n
    assert abs(s["positive_pct"] + s["neutral_pct"] + s["negative_pct"] - 100) < 0.1
    for p in body["predictions"]:
        assert p["sentiment"] in (-1, 0, 1)
        assert p["label"] in ("positif", "neutre", "negatif", "ignore")


def test_predict_batch_response_time(client):
    comments = ["Amazing work, thank you!"] * 50
    t0 = time.perf_counter()
    r = client.post("/predict_batch", json={"comments": comments})
    elapsed = (time.perf_counter() - t0) * 1000
    assert r.status_code == 200
    assert r.json()["processing_time_ms"] < 100
    assert "x-process-time-ms" in {k.lower() for k in r.headers}
    if not API_URL:
        assert elapsed < 500


@pytest.mark.parametrize("payload", [
    {"comments": []},                 # batch vide
    {"comments": ["", "   "]},        # uniquement des chaînes vides
    {"text": "mauvais champ"},        # champ manquant
    {"comments": "pas une liste"},    # mauvais type
    {"comments": ["x"] * 1001},       # batch trop grand
])
def test_invalid_payloads(client, payload):
    r = client.post("/predict_batch", json=payload)
    assert r.status_code == 422
    assert "error" in r.json()


def test_invalid_json(client):
    r = client.post("/predict_batch", content=b"{not json", headers={"Content-Type": "application/json"})
    assert r.status_code == 422


def test_skipped_excluded_from_percentages(client):
    r = client.post("/predict_batch", json={"comments": ["I love it", "!!!", "???"]})
    assert r.status_code == 200
    body = r.json()
    s = body["statistics"]
    assert s["total"] == 3 and s["skipped"] == 2 and s["analyzed"] == 1
    assert [p["skipped"] for p in body["predictions"]] == [False, True, True]
    assert abs(s["positive_pct"] + s["neutral_pct"] + s["negative_pct"] - 100) < 0.1


def test_predict_single(client):
    r = client.post("/predict", json={"text": "I love this channel"})
    assert r.status_code == 200
    assert r.json()["sentiment"] in (-1, 0, 1)


def test_cors_preflight(client):
    if API_URL:
        pytest.skip("CORS testé en local")
    r = client.options("/predict_batch", headers={
        "Origin": "chrome-extension://abcdefghijklmnop",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    })
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") in ("*", "chrome-extension://abcdefghijklmnop")
