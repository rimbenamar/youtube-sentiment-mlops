"""Configuration centrale du projet (chemins, constantes, hyperparamètres)."""
from pathlib import Path

# Racine du projet (…/youtube-sentiment-mlops)
ROOT_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
MODELS_DIR = ROOT_DIR / "models"
LOGS_DIR = ROOT_DIR / "logs"
REPORTS_DIR = ROOT_DIR / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"

DATASET_URL = (
    "https://raw.githubusercontent.com/Himanshu-1703/reddit-sentiment-analysis/"
    "refs/heads/main/data/reddit.csv"
)
RAW_DATA_PATH = RAW_DIR / "reddit.csv"
CLEAN_DATA_PATH = PROCESSED_DIR / "reddit_clean.csv"
TRAIN_PATH = PROCESSED_DIR / "train.csv"
TEST_PATH = PROCESSED_DIR / "test.csv"

MODEL_PATH = MODELS_DIR / "sentiment_model.joblib"
VECTORIZER_PATH = MODELS_DIR / "tfidf_vectorizer.joblib"
METADATA_PATH = MODELS_DIR / "model_metadata.json"

LABELS = {-1: "negatif", 0: "neutre", 1: "positif"}
LABEL_ORDER = [-1, 0, 1]

RANDOM_STATE = 42
TEST_SIZE = 0.2
MIN_TEXT_LENGTH = 2  # caractères après nettoyage

# Critères de performance du cahier des charges
TARGET_ACCURACY = 0.80
TARGET_F1_PER_CLASS = 0.75
TARGET_INFERENCE_MS_50 = 100.0


def ensure_dirs() -> None:
    for d in (RAW_DIR, PROCESSED_DIR, MODELS_DIR, LOGS_DIR, REPORTS_DIR, FIGURES_DIR):
        d.mkdir(parents=True, exist_ok=True)
