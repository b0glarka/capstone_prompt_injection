"""
make_cross_dataset_figure.py
-----------------------------
Builds a composite one-frame meeting summary of Defense A performance
across three benchmark datasets (deepset, neuralchemy, SPML).

Inputs
------
results/defense_a_cross_dataset.csv   -- point estimates
results/defense_a_bootstrap_cis.csv   -- 1,000-iter nonparametric bootstrap 95% CIs

Output
------
results/figures/defense_a_cross_dataset_summary.png  (dpi=150)

Author : capstone pipeline
Date   : 2026-05-08
"""

import sys
import os
import re
from pathlib import Path

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker
import seaborn as sns
import numpy as np

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO = Path(__file__).resolve().parent.parent
POINTS_CSV  = REPO / "results" / "defense_a_cross_dataset.csv"
CIS_CSV     = REPO / "results" / "defense_a_bootstrap_cis.csv"
OUT_DIR     = REPO / "results" / "figures"
OUT_FILE    = OUT_DIR / "defense_a_cross_dataset_summary.png"

OUT_DIR.mkdir(parents=True, exist_ok=True)


def _bare_name(raw: str) -> str:
    """Strip trailing ' (n=...)' suffix and lowercase for safe joining.

    Examples
    --------
    'deepset (n=546)' -> 'deepset'
    'SPML (n=2000)'   -> 'spml'
    'neuralchemy'     -> 'neuralchemy'
    """
    cleaned = re.sub(r"\s*\(n=\d+\)\s*$", "", raw, flags=re.IGNORECASE)
    return cleaned.strip().lower()


def load_and_merge() -> pd.DataFrame:
    """Load point estimates and bootstrap CIs, merge on normalised dataset name.

    Returns a DataFrame with columns:
        label, n, f1, f1_lo, f1_hi, auc, auc_lo, auc_hi
    """
    pts = pd.read_csv(POINTS_CSV)
    cis = pd.read_csv(CIS_CSV)

    # normalise join key
    pts["_key"] = pts["dataset"].apply(_bare_name)
    cis["_key"] = cis["dataset"].apply(_bare_name)

    merged = pts.merge(cis, on="_key", suffixes=("_pt", "_ci"))

    # sanity: warn on unmatched rows
    n_pts = len(pts)
    n_mer = len(merged)
    if n_mer < n_pts:
        unmatched = set(pts["_key"]) - set(cis["_key"])
        print(f"WARNING: {n_pts - n_mer} point-estimate row(s) had no CI match: {unmatched}",
              file=sys.stderr)

    # build tidy display labels (Title Case + n)
    def _label(row):
        name = row["_key"].upper() if row["_key"] == "spml" else row["_key"].capitalize()
        n = int(row["n"])
        return f"{name}\n(n={n:,})"

    merged["label"] = merged.apply(_label, axis=1)

    # rename metric columns unambiguously
    merged = merged.rename(columns={
        "f1":      "f1",
        "roc_auc": "auc",
    })

    # verify required columns exist
    required = ["label", "f1", "f1_lo", "f1_hi", "auc", "auc_lo", "auc_hi"]
    missing = [c for c in required if c not in merged.columns]
    if missing:
        raise KeyError(f"Merged DataFrame is missing columns: {missing}. "
                       f"Available: {list(merged.columns)}")

    return merged


def build_figure(df: pd.DataFrame) -> plt.Figure:
    """Build a two-panel horizontal (transposed to vertical bars) figure.

    Left panel  : F1 score with 95% CI error bars
    Right panel : ROC AUC with 95% CI error bars
    """
    sns.set_theme(style="whitegrid", font_scale=1.05)

    # dataset order: sort by F1 descending so best-performing is on top
    df = df.sort_values("f1", ascending=True).reset_index(drop=True)

    labels   = df["label"].tolist()
    n_ds     = len(labels)
    x_pos    = np.arange(n_ds)

    # Palette: muted, accessible, distinct
    palette = ["#4878D0", "#EE854A", "#6ACC65"]   # blue, orange, green
    colors  = palette[:n_ds]

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), sharey=True)
    fig.subplots_adjust(wspace=0.10)

    metrics = [
        {
            "ax":    axes[0],
            "col":   "f1",
            "lo":    "f1_lo",
            "hi":    "f1_hi",
            "title": "F1 Score",
            "xlim":  (0.40, 1.02),
        },
        {
            "ax":    axes[1],
            "col":   "auc",
            "lo":    "auc_lo",
            "hi":    "auc_hi",
            "title": "ROC AUC",
            "xlim":  (0.75, 1.02),
        },
    ]

    for m in metrics:
        ax   = m["ax"]
        vals = df[m["col"]].values
        lo   = df[m["lo"]].values
        hi   = df[m["hi"]].values
        err_lo = vals - lo
        err_hi = hi - vals

        bars = ax.barh(
            x_pos,
            vals,
            xerr=[err_lo, err_hi],
            color=colors,
            edgecolor="white",
            linewidth=0.8,
            error_kw=dict(ecolor="#333333", capsize=4, capthick=1.2, elinewidth=1.2),
            height=0.55,
        )

        # annotate value at bar tip
        for i, (val, h_err) in enumerate(zip(vals, err_hi)):
            ax.text(
                val + h_err + 0.005,
                i,
                f"{val:.2f}",
                va="center",
                ha="left",
                fontsize=9.5,
                color="#222222",
            )

        ax.set_xlim(*m["xlim"])
        ax.set_title(m["title"], fontsize=12, fontweight="bold", pad=8)
        ax.set_xlabel("Score", fontsize=10)
        ax.xaxis.set_minor_locator(matplotlib.ticker.AutoMinorLocator(2))
        ax.grid(axis="x", which="minor", linewidth=0.4, alpha=0.5)
        ax.tick_params(axis="y", length=0)

    # y-axis labels only on left panel
    axes[0].set_yticks(x_pos)
    axes[0].set_yticklabels(labels, fontsize=10)
    axes[0].set_ylabel("")

    # ---- titles and caption ------------------------------------------------
    fig.suptitle(
        "Defense A on three benchmarks: cross-dataset variance is the headline",
        fontsize=13,
        fontweight="bold",
        y=1.01,
    )

    fig.text(
        0.5, -0.04,
        "Error bars: 95% CI from 1,000-iteration nonparametric bootstrap   |   "
        "Classifier: ProtectAI DeBERTa-v3-base-prompt-injection-v2, default threshold",
        ha="center",
        fontsize=8,
        color="#555555",
    )

    return fig


def main():
    print("Loading CSVs...")
    df = load_and_merge()
    print(f"  Merged {len(df)} dataset rows: {df['_key'].tolist()}")
    print(f"  Columns available: {list(df.columns)}")

    print("Building figure...")
    fig = build_figure(df)

    print(f"Saving to {OUT_FILE} ...")
    fig.savefig(OUT_FILE, dpi=150, bbox_inches="tight")
    plt.close(fig)

    size_bytes = OUT_FILE.stat().st_size
    size_kb    = size_bytes / 1024
    print(f"Saved. File size: {size_kb:.1f} KB")

    if size_kb < 50:
        print("WARNING: file is suspiciously small (<50 KB) -- figure may be blank.",
              file=sys.stderr)
    elif size_kb > 500:
        print("WARNING: file is larger than expected (>500 KB).", file=sys.stderr)
    else:
        print(f"File size OK ({size_kb:.1f} KB, expected 50-200 KB).")

    return OUT_FILE


if __name__ == "__main__":
    out = main()
    print(f"Done: {out}")
