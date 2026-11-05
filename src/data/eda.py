"""Phase 2 - Analyse exploratoire : distribution des classes, longueur des textes, mots fréquents."""
import json
from collections import Counter

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from src.utils.config import CLEAN_DATA_PATH, FIGURES_DIR, LABELS, LABEL_ORDER, REPORTS_DIR, ensure_dirs  # noqa: E402
from src.utils.logger import get_logger  # noqa: E402

logger = get_logger("eda", "pipeline.log")
COLORS = {-1: "#d1495b", 0: "#8d99ae", 1: "#2a9d8f"}
STOP = set("the a an and or to of in is it i you that this for on with be are was have not but my "
           "they he she we his her its as at so if just like do what all can me your from there "
           "about would will one by no more people get dont im has been their them who than".split())


def run(path=CLEAN_DATA_PATH) -> dict:
    ensure_dirs()
    df = pd.read_csv(path)
    df["n_words"] = df["text"].astype(str).str.split().str.len()
    df["n_chars"] = df["text"].astype(str).str.len()

    counts = df["label"].value_counts().reindex(LABEL_ORDER).fillna(0).astype(int)
    imbalance = float(counts.max() / max(counts.min(), 1))

    # 1. Distribution des classes
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.bar([LABELS[label] for label in LABEL_ORDER], counts.values, color=[COLORS[label] for label in LABEL_ORDER])
    for i, v in enumerate(counts.values):
        ax.text(i, v, f"{v:,}\n({v / len(df):.1%})", ha="center", va="bottom", fontsize=9)
    ax.set_title("Distribution des classes")
    ax.set_ylabel("Nombre de commentaires")
    ax.margins(y=0.15)
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "class_distribution.png", dpi=120)
    plt.close(fig)

    # 2. Longueur des textes par classe
    fig, ax = plt.subplots(figsize=(7, 4))
    clip = df["n_words"].quantile(0.98)
    for lab in LABEL_ORDER:
        ax.hist(df.loc[df.label == lab, "n_words"].clip(upper=clip), bins=40, alpha=0.55,
                label=LABELS[lab], color=COLORS[lab])
    ax.set_title("Longueur des commentaires (mots)")
    ax.set_xlabel("Nombre de mots")
    ax.set_ylabel("Fréquence")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "text_length.png", dpi=120)
    plt.close(fig)

    # 3. Mots les plus fréquents par classe
    top_words = {}
    for lab in LABEL_ORDER:
        c = Counter(w for t in df.loc[df.label == lab, "text"].astype(str) for w in t.split()
                    if w not in STOP and len(w) > 2)
        top_words[LABELS[lab]] = c.most_common(15)

    stats = {
        "n_comments": int(len(df)),
        "class_counts": {LABELS[k]: int(v) for k, v in counts.items()},
        "class_pct": {LABELS[k]: round(float(v) / len(df) * 100, 2) for k, v in counts.items()},
        "imbalance_ratio": round(imbalance, 2),
        "words_mean": round(float(df["n_words"].mean()), 1),
        "words_median": float(df["n_words"].median()),
        "words_max": int(df["n_words"].max()),
        "words_mean_by_class": {LABELS[k]: round(float(v), 1)
                                for k, v in df.groupby("label")["n_words"].mean().items()},
        "top_words": top_words,
    }
    (REPORTS_DIR / "eda_stats.json").write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n============== ANALYSE EXPLORATOIRE ==============")
    print(f"Commentaires : {stats['n_comments']:,}")
    for k in stats["class_counts"]:
        print(f"  {k:<8}: {stats['class_counts'][k]:>6,} ({stats['class_pct'][k]}%)")
    print(f"Ratio de déséquilibre (max/min) : {stats['imbalance_ratio']}")
    print(f"Longueur moyenne : {stats['words_mean']} mots (médiane {stats['words_median']}, max {stats['words_max']})")
    print("Décision : déséquilibre modéré -> class_weight='balanced' testé dans la GridSearch")
    print(f"Figures : {FIGURES_DIR}")
    print("==================================================\n")
    return stats


if __name__ == "__main__":
    run()
