"""Phase 4 - API REST FastAPI pour servir le modèle de sentiment.

Lancement local :
    uvicorn src.api.main:app --reload --port 7860
Documentation interactive : http://localhost:7860/docs
"""
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.predictor import SentimentPredictor
from src.api.schemas import (BatchRequest, BatchResponse, HealthResponse, Prediction,
                             SingleRequest)
from src.utils.logger import get_logger

logger = get_logger("api", "api.log")
predictor = SentimentPredictor()
START_TIME = time.time()
LOAD_ERROR = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Le modèle est chargé UNE seule fois au démarrage, pas à chaque requête.
    global LOAD_ERROR
    try:
        predictor.load()
        logger.info("Modèle chargé : %s (version %s)", predictor.metadata.get("model_name"),
                    predictor.metadata.get("model_version"))
    except Exception as exc:  # l'API démarre quand même : /health signale le problème
        LOAD_ERROR = str(exc)
        logger.error("Échec du chargement du modèle : %s", exc)
    yield


app = FastAPI(
    title="YouTube Sentiment Analysis API",
    description="Analyse le sentiment (négatif / neutre / positif) de commentaires YouTube. "
                "Modèle : TF-IDF + classifieur scikit-learn.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS : l'extension Chrome (origine chrome-extension://<id>) et les tests locaux.
# Les extensions MV3 avec host_permissions passent outre CORS, mais on le configure
# pour les autres clients (pages web, tests depuis le navigateur…).
origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"chrome-extension://.*",
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    t0 = time.perf_counter()
    response = await call_next(request)
    ms = (time.perf_counter() - t0) * 1000
    response.headers["X-Process-Time-Ms"] = f"{ms:.2f}"
    logger.info("%s %s -> %d (%.1f ms)", request.method, request.url.path, response.status_code, ms)
    return response


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    errors = [{"field": ".".join(str(x) for x in e.get("loc", [])), "message": e.get("msg")}
              for e in exc.errors()]
    return JSONResponse(status_code=422, content={"error": "Données invalides", "details": errors})


@app.exception_handler(Exception)
async def unhandled_handler(request: Request, exc: Exception):
    logger.exception("Erreur interne : %s", exc)
    return JSONResponse(status_code=500, content={"error": "Erreur interne du serveur"})


def _require_model():
    if not predictor.is_loaded:
        raise HTTPException(status_code=503, detail=f"Modèle indisponible : {LOAD_ERROR or 'non chargé'}")


@app.get("/", tags=["info"])
def root():
    return {"name": "YouTube Sentiment Analysis API", "docs": "/docs", "health": "/health",
            "endpoints": ["GET /health", "POST /predict_batch", "POST /predict"]}


@app.get("/health", response_model=HealthResponse, tags=["monitoring"])
def health():
    loaded = predictor.is_loaded
    return HealthResponse(
        status="ok" if loaded else "degraded",
        model_loaded=loaded,
        model_name=predictor.metadata.get("model_name"),
        model_version=predictor.metadata.get("model_version"),
        uptime_seconds=round(time.time() - START_TIME, 1),
        error=None if loaded else LOAD_ERROR,
    )


@app.post("/predict_batch", response_model=BatchResponse, tags=["prediction"])
def predict_batch(req: BatchRequest):
    _require_model()
    t0 = time.perf_counter()
    preds = predictor.predict(req.comments)
    stats = predictor.statistics(preds)
    ms = round((time.perf_counter() - t0) * 1000, 2)
    logger.info("predict_batch : %d commentaires en %.1f ms", len(preds), ms)
    return BatchResponse(predictions=preds, statistics=stats, processing_time_ms=ms,
                         model_version=predictor.metadata.get("model_version"))


@app.post("/predict", response_model=Prediction, tags=["prediction"])
def predict_one(req: SingleRequest):
    _require_model()
    if not req.text.strip():
        raise HTTPException(status_code=422, detail="Texte vide")
    return predictor.predict([req.text])[0]
