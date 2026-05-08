"""Three-panel score-distribution histogram across deepset, neuralchemy, SPML.

Replaces the earlier two-panel version with a third panel for SPML, completing
the cross-dataset visual story. Log-y axis to make the small-count tails visible.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

REPO = Path(__file__).resolve().parent.parent
RES = REPO / "results"
FIG = RES / "figures"

DATASETS = [
    ("deepset",     "label",            RES / "defense_a_deepset.csv"),
    ("neuralchemy", "label",            RES / "defense_a_neuralchemy.csv"),
    ("SPML",        "Prompt injection", RES / "defense_a_spml.csv"),
]


def main() -> None:
    sns.set_theme(style="whitegrid")
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.4))
    bins = np.linspace(0, 1, 41)

    for ax, (name, lbl_col, csv_path) in zip(axes, DATASETS):
        df = pd.read_csv(csv_path)
        n = len(df)
        inj  = df.loc[df[lbl_col] == 1, "injection_score"]
        safe = df.loc[df[lbl_col] == 0, "injection_score"]
        ax.hist(safe, bins=bins, alpha=0.6, color="#3498db", label=f"true SAFE   (n={len(safe)})")
        ax.hist(inj,  bins=bins, alpha=0.6, color="#e67e22", label=f"true INJECTION (n={len(inj)})")
        ax.axvline(0.5, ls=":", color="gray", alpha=0.7)
        zero_inj = (inj < 0.001).sum()
        zero_pct = zero_inj / max(len(inj), 1)
        ax.set_title(f"{name} (n={n})\n{zero_inj} of {len(inj)} ({zero_pct:.1%}) true injections scored 0.000")
        ax.set_xlabel("DeBERTa injection_score")
        ax.set_ylabel("Count")
        ax.set_yscale("log")
        ax.legend(loc="upper center", fontsize=9)

    fig.suptitle(
        "Score distributions: deepset is bimodal (40.9% spike at 0); neuralchemy and SPML are graduated",
        y=1.03,
    )
    plt.tight_layout()
    out = FIG / "defense_a_score_distributions.png"
    plt.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"saved {out} ({out.stat().st_size/1024:.1f} KB)")


if __name__ == "__main__":
    main()
