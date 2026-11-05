"""Exécute tout le pipeline ML de bout en bout (Phases 2 et 3).

    python run_pipeline.py            # téléchargement + nettoyage + EDA + entraînement complet
    python run_pipeline.py --fast     # entraînement rapide (grille réduite)
    python run_pipeline.py --skip-download --input chemin/vers/reddit.csv
    python run_pipeline.py --n-jobs 1   # sans parallélisme (si erreur joblib/loky sous Windows)
"""
import argparse
import time

from src.data import download_data, eda, preprocess
from src.models import train
from src.utils.config import RAW_DATA_PATH


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--fast", action="store_true")
    p.add_argument("--skip-download", action="store_true")
    p.add_argument("--input", default=str(RAW_DATA_PATH))
    p.add_argument("--n-jobs", type=int, default=None)
    args = p.parse_args()

    t0 = time.perf_counter()
    if not args.skip_download:
        print(">>> [1/4] Téléchargement du dataset")
        download_data.main([])
    print(">>> [2/4] Nettoyage + split train/test")
    preprocess.main(["--input", args.input])
    print(">>> [3/4] Analyse exploratoire")
    eda.run()
    print(">>> [4/4] Entraînement et évaluation")
    train_args = ["--fast"] if args.fast else []
    if args.n_jobs is not None:
        train_args += ["--n-jobs", str(args.n_jobs)]
    train.main(train_args)
    print(f"Pipeline terminé en {time.perf_counter() - t0:.0f}s")


if __name__ == "__main__":
    main()
