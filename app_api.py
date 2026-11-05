"""Point d'entrée optimisé pour le déploiement (Docker / GitHub Codespaces).

    python app_api.py                 # port 7860 par défaut
    PORT=8000 python app_api.py       # port configurable
"""
import os

import uvicorn

from src.api.main import app  # noqa: F401  (exposé pour `uvicorn app_api:app`)

if __name__ == "__main__":
    uvicorn.run(
        "src.api.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "7860")),
        workers=int(os.getenv("WORKERS", "1")),
        log_level=os.getenv("LOG_LEVEL", "info"),
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
