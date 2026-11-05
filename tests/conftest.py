import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.utils.config import MODEL_PATH, VECTORIZER_PATH  # noqa: E402

models_exist = MODEL_PATH.exists() and VECTORIZER_PATH.exists()
requires_model = pytest.mark.skipif(not models_exist, reason="Modèle non entraîné : lancez `python run_pipeline.py`")
