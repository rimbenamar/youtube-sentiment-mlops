"""Schémas Pydantic : validation des requêtes et format des réponses."""
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

MAX_BATCH_SIZE = 1000
MAX_COMMENT_CHARS = 5000


class BatchRequest(BaseModel):
    comments: List[str] = Field(..., min_length=1, max_length=MAX_BATCH_SIZE,
                                description="Liste de commentaires bruts (1 à 1000)")

    @field_validator("comments")
    @classmethod
    def check_comments(cls, v: List[str]) -> List[str]:
        cleaned = [c.strip()[:MAX_COMMENT_CHARS] for c in v if isinstance(c, str)]
        if not any(cleaned):
            raise ValueError("Le batch ne contient aucun commentaire non vide")
        return cleaned

    model_config = {"json_schema_extra": {"examples": [{"comments": [
        "This video is amazing, thanks!", "Worst explanation ever", "What camera do you use?"]}]}}


class SingleRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=MAX_COMMENT_CHARS)


class Prediction(BaseModel):
    text: str
    sentiment: int = Field(..., description="-1 négatif, 0 neutre, 1 positif")
    label: str
    confidence: float
    probabilities: Dict[str, float]
    skipped: bool = Field(False, description="True si le texte est vide après nettoyage (exclu des statistiques)")


class Statistics(BaseModel):
    total: int
    analyzed: int = Field(..., description="Commentaires réellement classés (total - ignorés)")
    skipped: int
    positive: int
    neutral: int
    negative: int
    positive_pct: float
    neutral_pct: float
    negative_pct: float
    average_confidence: float
    sentiment_score: float = Field(..., description="Moyenne des sentiments, de -1 à 1")
    dominant: str


class BatchResponse(BaseModel):
    predictions: List[Prediction]
    statistics: Statistics
    processing_time_ms: float
    model_version: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    model_name: Optional[str] = None
    model_version: Optional[str] = None
    uptime_seconds: float
    error: Optional[str] = None
