"""BIPIA per-category attack success rates (horizontal grouped bar chart).

Reads results/bipia_email_qa_per_category.csv (15 BIPIA attack categories
across four defense configurations) and produces a horizontal grouped bar
chart sorted by mean attack success rate (hardest categories at the top).

Output: reports/figures/bipia_per_category.{png,pdf}
"""

from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "results" / "bipia_email_qa_per_category_v125.csv"
OUT = ROOT / "reports" / "figures" / "bipia_per_category"


def main() -> None:
    df = pd.read_csv(DATA).copy()

    defense_cols = [
        ("DeBERTa_full_prompt_attack_success", "DeBERTa (full prompt)", "#1f77b4"),
        ("PG2_full_prompt_attack_success",     "Prompt Guard 2 (full prompt)", "#9467bd"),
        ("Sonnet_v125_judge_attack_success",   "Sonnet 4.6 judge", "#cc6633"),
        ("Defense_C_v125_attack_success",      "Defense C (DeBERTa + judge)", "#2ca02c"),
    ]
    df["mean_asr"] = df[[c for c, _, _ in defense_cols]].mean(axis=1)
    df = df.sort_values("mean_asr", ascending=True)

    cats = df["category"].tolist()
    y = np.arange(len(cats))
    bar_h = 0.18

    fig, ax = plt.subplots(figsize=(14, 7.5))
    for i, (col, label, color) in enumerate(defense_cols):
        offset = (i - 1.5) * bar_h
        ax.barh(
            y + offset, df[col].values, bar_h,
            label=label, color=color, edgecolor="black", linewidth=0.4,
        )

    ax.set_yticks(y)
    ax.set_yticklabels(cats, fontsize=15)
    ax.tick_params(axis="x", labelsize=14)
    ax.set_xlabel("Attack success rate (lower is better)", fontsize=16)
    ax.set_xlim(0, 1.05)
    ax.set_axisbelow(True)
    ax.grid(axis="x", linestyle="--", alpha=0.4)
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.08),
        ncol=2,
        frameon=True,
        fontsize=13,
    )

    fig.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(f"{OUT}.png", dpi=200)
    fig.savefig(f"{OUT}.pdf")
    print(f"Wrote {OUT}.png and {OUT}.pdf")


if __name__ == "__main__":
    main()
