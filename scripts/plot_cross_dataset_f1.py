"""Cross-dataset F1 bar chart (the report's headline finding).

Reads results/defense_a_full_metrics.csv and produces a grouped bar chart
showing F1 with 95% CI whiskers for ProtectAI DeBERTa and Meta Prompt
Guard 2 across the three datasets (deepset, neuralchemy, SPML).

Output: reports/figures/cross_dataset_f1.{png,pdf}
"""

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "results" / "defense_a_full_metrics.csv"
OUT = ROOT / "reports" / "figures" / "cross_dataset_f1"


def main() -> None:
    df = pd.read_csv(DATA)
    df = df[df["scope"].isin(["deepset", "neuralchemy", "spml"])].copy()

    datasets = ["deepset", "neuralchemy", "spml"]
    dataset_labels = ["deepset", "neuralchemy", "SPML"]
    classifiers = ["deberta", "pg2"]
    classifier_labels = ["ProtectAI DeBERTa", "Meta Prompt Guard 2"]
    colors = ["#1f77b4", "#ff7f0e"]

    fig, ax = plt.subplots(figsize=(8.5, 5))
    bar_w = 0.36
    x = np.arange(len(datasets))

    for i, (clf, lbl, c) in enumerate(zip(classifiers, classifier_labels, colors)):
        f1 = []
        lo = []
        hi = []
        for d in datasets:
            row = df[(df["classifier"] == clf) & (df["scope"] == d)].iloc[0]
            f1.append(row["f1"])
            lo.append(row["f1"] - row["f1_lo"])
            hi.append(row["f1_hi"] - row["f1"])
        offset = (i - 0.5) * bar_w
        bars = ax.bar(
            x + offset, f1, bar_w,
            yerr=[lo, hi], capsize=4,
            label=lbl, color=c, edgecolor="black", linewidth=0.5,
        )
        for bar, v in zip(bars, f1):
            ax.text(
                bar.get_x() + bar.get_width() / 2, v + 0.015,
                f"{v:.2f}", ha="center", va="bottom", fontsize=9,
            )

    ax.set_xticks(x)
    ax.set_xticklabels(dataset_labels, fontsize=11)
    ax.set_ylabel("F1 (injection class)", fontsize=11)
    ax.set_ylim(0, 1.05)
    ax.set_axisbelow(True)
    ax.grid(axis="y", linestyle="--", alpha=0.4)
    ax.legend(loc="lower right", frameon=True, fontsize=10)

    fig.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(f"{OUT}.png", dpi=200)
    fig.savefig(f"{OUT}.pdf")
    print(f"Wrote {OUT}.png and {OUT}.pdf")


if __name__ == "__main__":
    main()
