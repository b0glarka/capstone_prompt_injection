"""Cross-classifier ensemble analysis: DeBERTa + Prompt Guard 2 combined.

Three combination strategies tested against each single classifier:
  OR-gate:  flag INJECTION if EITHER classifier says INJECTION (max sensitivity)
  AND-gate: flag INJECTION only if BOTH classifiers say INJECTION (max specificity)
  Mean-score: average the injection_score of both, threshold at 0.5

Reports per-defense headline metrics with bootstrap 95% CIs, overall and per
dataset, and a paired McNemar test against the best single classifier.

Outputs:
  results/defense_a_ensemble_metrics.csv
  results/defense_a_ensemble_mcnemar.csv
  results/figures/ensemble_f1_compare.png
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from src.metrics import bootstrap_ci, headline_metrics, mcnemar

RES = REPO / "results"
FIG = RES / "figures"
FIG.mkdir(parents=True, exist_ok=True)


def main() -> None:
    df = pd.read_csv(RES / "defense_a_full_eval_set.csv")
    print(f"rows: {len(df)}")

    # Build ensemble columns
    df["or_pred"]   = ((df["deberta_pred_label_id"] == 1) | (df["pg2_pred_label_id"] == 1)).astype(int)
    df["and_pred"]  = ((df["deberta_pred_label_id"] == 1) & (df["pg2_pred_label_id"] == 1)).astype(int)
    df["mean_score"] = (df["deberta_injection_score"] + df["pg2_injection_score"]) / 2
    df["mean_pred"]  = (df["mean_score"] >= 0.5).astype(int)

    pred_cols = {
        "DeBERTa":      ("deberta_pred_label_id", "deberta_injection_score"),
        "PG2":          ("pg2_pred_label_id",     "pg2_injection_score"),
        "OR-gate":      ("or_pred",               None),
        "AND-gate":     ("and_pred",              None),
        "Mean-score":   ("mean_pred",             "mean_score"),
    }
    scopes = [("overall", df)] + [(ds, df[df["dataset"] == ds]) for ds in ["deepset", "neuralchemy", "spml"]]

    # Headline metrics + CIs
    rows = []
    for defense, (pred_col, score_col) in pred_cols.items():
        for scope_name, scope in scopes:
            y = scope["label"].values
            yp = scope[pred_col].values
            ys = scope[score_col].values if score_col else None
            m = headline_metrics(y, yp, ys)
            ci_args = {"y_score": ys} if ys is not None else {}
            ci = bootstrap_ci(y, yp, ys, n_iter=1000, seed=42)
            row = {"defense": defense, "scope": scope_name, "n": len(scope), **m}
            for k, (lo, hi) in ci.items():
                row[f"{k}_lo"] = round(lo, 4)
                row[f"{k}_hi"] = round(hi, 4)
            rows.append(row)
    metrics_df = pd.DataFrame(rows)
    for c in ["accuracy", "precision", "recall", "f1", "auc"]:
        if c in metrics_df.columns:
            metrics_df[c] = metrics_df[c].round(4)
    metrics_df.to_csv(RES / "defense_a_ensemble_metrics.csv", index=False)
    print("\nOverall metrics:")
    print(metrics_df[metrics_df["scope"] == "overall"][["defense", "n", "precision", "recall", "f1", "auc"]].to_string(index=False))

    # Paired McNemar: each ensemble vs best single classifier (DeBERTa overall)
    rows = []
    for defense, (pred_col, _) in pred_cols.items():
        if defense == "DeBERTa":
            continue
        for scope_name, scope in scopes:
            y = scope["label"].values
            base = scope["deberta_pred_label_id"].values
            challenger = scope[pred_col].values
            res = mcnemar(y, base, challenger, exact=False)
            rows.append({
                "defense": defense,
                "scope": scope_name,
                "n": len(scope),
                "b_deberta_only_correct": res["b"],
                "c_challenger_only_correct": res["c"],
                "p_value": res["p_value"],
            })
    mcnemar_df = pd.DataFrame(rows)
    mcnemar_df.to_csv(RES / "defense_a_ensemble_mcnemar.csv", index=False)
    print("\nPaired McNemar (vs DeBERTa as baseline):")
    print(mcnemar_df.to_string(index=False))

    # F1 comparison figure
    sns.set_theme(style="whitegrid")
    overall = metrics_df[metrics_df["scope"] == "overall"].sort_values("f1")
    fig, ax = plt.subplots(figsize=(8, 4))
    y = np.arange(len(overall))
    f1_vals = overall["f1"].values
    f1_lo = overall["f1_lo"].values
    f1_hi = overall["f1_hi"].values
    err_lo = f1_vals - f1_lo
    err_hi = f1_hi - f1_vals
    palette = ["#4878D0", "#EE854A", "#6ACC65", "#D65F5F", "#956CB4"]
    ax.barh(y, f1_vals, xerr=[err_lo, err_hi],
            color=palette[:len(overall)], edgecolor="white", linewidth=0.8,
            error_kw=dict(ecolor="#333333", capsize=4, capthick=1.2))
    for i, (v, hi_e) in enumerate(zip(f1_vals, err_hi)):
        ax.text(v + hi_e + 0.005, i, f"{v:.3f}", va="center", ha="left", fontsize=9.5)
    ax.set_yticks(y)
    ax.set_yticklabels(overall["defense"].tolist())
    ax.set_xlim(0.5, 1.02)
    ax.set_xlabel("F1 [95% CI]")
    ax.set_title("Defense A ensemble F1 vs single classifiers (full eval set, n=4,546)")
    plt.tight_layout()
    out_fig = FIG / "ensemble_f1_compare.png"
    plt.savefig(out_fig, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\nsaved {out_fig}")

    # Plain-English summary at the end
    overall_only = metrics_df[metrics_df["scope"] == "overall"].set_index("defense")
    best_single = "DeBERTa" if overall_only.loc["DeBERTa", "f1"] >= overall_only.loc["PG2", "f1"] else "PG2"
    best_ensemble = overall_only.loc[["OR-gate", "AND-gate", "Mean-score"], "f1"].idxmax()
    print(f"\nBest single: {best_single} (F1 = {overall_only.loc[best_single, 'f1']})")
    print(f"Best ensemble: {best_ensemble} (F1 = {overall_only.loc[best_ensemble, 'f1']})")
    lift = overall_only.loc[best_ensemble, 'f1'] - overall_only.loc[best_single, 'f1']
    print(f"Ensemble lift over best single: {lift:+.4f}")


if __name__ == "__main__":
    main()
