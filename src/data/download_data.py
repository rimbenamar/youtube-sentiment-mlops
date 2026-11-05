"""Phase 2 - Téléchargement du dataset Reddit Sentiment Analysis.

Usage :
    python -m src.data.download_data            # télécharge depuis l'URL officielle
    python -m src.data.download_data --force    # re-télécharge même si le fichier existe
"""
import argparse
import sys
import urllib.request

import pandas as pd

from src.utils.config import DATASET_URL, LABELS, RAW_DATA_PATH, ensure_dirs
from src.utils.logger import get_logger

logger = get_logger("download", "pipeline.log")


def download(url: str = DATASET_URL, dest=RAW_DATA_PATH, force: bool = False, timeout: int = 60):
    ensure_dirs()
    if dest.exists() and not force:
        logger.info("Fichier déjà présent : %s (utiliser --force pour re-télécharger)", dest)
        return dest
    logger.info("Téléchargement de %s", url)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "youtube-sentiment-mlops"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read()
    except Exception as exc:  # réseau indisponible, URL invalide…
        logger.error("Échec du téléchargement : %s", exc)
        raise SystemExit(1) from exc
    dest.write_bytes(content)
    logger.info("Sauvegardé dans %s (%.1f Ko)", dest, len(content) / 1024)
    return dest


def show_stats(path=RAW_DATA_PATH) -> pd.DataFrame:
    df = pd.read_csv(path)
    text_col = "clean_comment" if "clean_comment" in df.columns else df.columns[0]
    label_col = "category" if "category" in df.columns else df.columns[-1]
    print("\n========== STATISTIQUES DU DATASET ==========")
    print(f"Fichier            : {path}")
    print(f"Colonnes           : {list(df.columns)}")
    print(f"Nombre de lignes   : {len(df):,}")
    print(f"Valeurs manquantes : {int(df[text_col].isna().sum())} (texte)")
    print(f"Doublons           : {int(df.duplicated(subset=[text_col]).sum())}")
    print("\nDistribution des labels :")
    counts = df[label_col].value_counts().sort_index()
    for lab, n in counts.items():
        name = LABELS.get(int(lab), str(lab)) if pd.notna(lab) else "NaN"
        print(f"  {int(lab):>2} ({name:<8}) : {n:>6,}  ({n / len(df):.1%})")
    print("=============================================\n")
    return df


def main(argv=None):
    p = argparse.ArgumentParser(description="Télécharge le dataset Reddit")
    p.add_argument("--url", default=DATASET_URL)
    p.add_argument("--force", action="store_true")
    args = p.parse_args(argv)
    path = download(args.url, force=args.force)
    show_stats(path)


if __name__ == "__main__":
    sys.exit(main())
