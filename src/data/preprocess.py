"""Phase 2 - Nettoyage des données + split train/test reproductible.

Entrée  : data/raw/reddit.csv  (colonnes clean_comment, category)
Sorties : data/processed/reddit_clean.csv, train.csv, test.csv (colonnes text, label)
"""
import argparse
import json

import pandas as pd
from sklearn.model_selection import train_test_split

from src.utils.config import (CLEAN_DATA_PATH, REPORTS_DIR, LABEL_ORDER, MIN_TEXT_LENGTH, RANDOM_STATE,
                              RAW_DATA_PATH, TEST_PATH, TEST_SIZE, TRAIN_PATH, ensure_dirs)
from src.utils.logger import get_logger
from src.utils.text_cleaning import clean_text

logger = get_logger("preprocess", "pipeline.log")
CLEANING_STATS: dict = {}


def load_raw(path=RAW_DATA_PATH) -> pd.DataFrame:
    df = pd.read_csv(path)
    rename = {}
    if "clean_comment" in df.columns:
        rename["clean_comment"] = "text"
    if "category" in df.columns:
        rename["category"] = "label"
    df = df.rename(columns=rename)
    if not {"text", "label"}.issubset(df.columns):
        raise ValueError(f"Colonnes attendues text/label, trouvées : {list(df.columns)}")
    return df[["text", "label"]]


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    n0 = len(df)
    df = df.dropna(subset=["text", "label"]).copy()
    df["label"] = df["label"].astype(int)
    df = df[df["label"].isin(LABEL_ORDER)]
    df["text"] = df["text"].astype(str).map(clean_text)
    n_na = n0 - len(df)
    n1 = len(df)
    df = df[df["text"].str.len() >= MIN_TEXT_LENGTH]
    n_empty = n1 - len(df)
    # Textes identiques avec des labels différents : contradictoires, on les retire tous
    # (garder « le premier » reviendrait à choisir un label au hasard).
    n_labels = df.groupby("text")["label"].transform("nunique")
    conflicts = int(df.loc[n_labels > 1, "text"].nunique())
    n2 = len(df)
    df = df[n_labels == 1]
    n_conflict_rows = n2 - len(df)
    n3 = len(df)
    df = df.drop_duplicates(subset=["text"])
    n_dupes = n3 - len(df)
    df = df.reset_index(drop=True)
    CLEANING_STATS.update({"rows_raw": n0, "missing_or_invalid": n_na, "empty_after_cleaning": n_empty,
                           "conflicting_texts": conflicts, "conflicting_rows_removed": n_conflict_rows,
                           "duplicates_removed": n_dupes, "rows_clean": len(df)})
    logger.info("Nettoyage : %d -> %d lignes | manquants %d, vides %d, conflits %d lignes (%d textes), doublons %d",
                n0, len(df), n_na, n_empty, n_conflict_rows, conflicts, n_dupes)
    return df


def check_spec(df: pd.DataFrame) -> None:
    counts = df["label"].value_counts()
    ok_size = len(df) >= 1000
    ok_class = all(counts.get(lab, 0) >= 300 for lab in LABEL_ORDER)
    logger.info("Spécification taille >= 1000 : %s | >= 300 par classe : %s", ok_size, ok_class)
    if not (ok_size and ok_class):
        raise ValueError("Le dataset ne respecte pas la taille minimale du cahier des charges")


def split(df: pd.DataFrame):
    train, test = train_test_split(df, test_size=TEST_SIZE, random_state=RANDOM_STATE,
                                   stratify=df["label"])
    return train.reset_index(drop=True), test.reset_index(drop=True)


def main(argv=None):
    p = argparse.ArgumentParser(description="Nettoie le dataset et crée le split train/test")
    p.add_argument("--input", default=str(RAW_DATA_PATH))
    args = p.parse_args(argv)
    ensure_dirs()
    df = clean_dataframe(load_raw(args.input))
    check_spec(df)
    df.to_csv(CLEAN_DATA_PATH, index=False)
    train, test = split(df)
    train.to_csv(TRAIN_PATH, index=False)
    test.to_csv(TEST_PATH, index=False)
    logger.info("Train : %d | Test : %d (stratifié, random_state=%d)", len(train), len(test), RANDOM_STATE)
    logger.info("Distribution train : %s", train["label"].value_counts().sort_index().to_dict())
    CLEANING_STATS.update({"train_rows": len(train), "test_rows": len(test), "test_size": TEST_SIZE,
                           "random_state": RANDOM_STATE})
    (REPORTS_DIR / "cleaning_stats.json").write_text(json.dumps(CLEANING_STATS, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
