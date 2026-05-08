"""1x3 confusion-matrix grid for Defense A on deepset, neuralchemy, SPML."""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from sklearn.metrics import confusion_matrix

REPO = Path(__file__).resolve().parent.parent
RES = REPO / "results"
FIG = RES / "figures"

DATASETS = [
    ("deepset",     "label",            "pred_label_id", RES / "defense_a_deepset.csv"),
    ("neuralchemy", "label",            "pred_label_id", RES / "defense_a_neuralchemy.csv"),
    ("SPML",        "Prompt injection", "pred_label_id", RES / "defense_a_spml.csv"),
]


def main() -> None:
    sns.set_theme(style="whitegrid")
    fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.4))
    for ax, (name, lbl, pred, csv_path) in zip(axes, DATASETS):
        df = pd.read_csv(csv_path)
        cm = confusion_matrix(df[lbl].values, df[pred].values, labels=[0, 1])
        sns.heatmap(
            cm, annot=True, fmt="d", cmap="Blues", cbar=False,
            xticklabels=["pred SAFE", "pred INJECTION"],
            yticklabels=["true SAFE", "true INJECTION"],
            ax=ax,
        )
        ax.set_title(f"{name} (n={len(df)})")

    fig.suptitle("Defense A confusion matrices, default threshold", y=1.04, fontweight="bold")
    plt.tight_layout()
    out = FIG / "defense_a_confusion_grid.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"saved {out} ({out.stat().st_size/1024:.1f} KB)")


if __name__ == "__main__":
    main()
