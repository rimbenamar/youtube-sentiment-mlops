"""Logger partagé : console + fichier dans logs/."""
import logging
import sys
from logging.handlers import RotatingFileHandler

from src.utils.config import LOGS_DIR


def get_logger(name: str, log_file: str = "app.log") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    logger.addHandler(console)

    try:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        fh = RotatingFileHandler(LOGS_DIR / log_file, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
        fh.setFormatter(fmt)
        logger.addHandler(fh)
    except OSError:
        # Système de fichiers en lecture seule (ex. conteneur) : console uniquement
        pass

    logger.propagate = False
    return logger
