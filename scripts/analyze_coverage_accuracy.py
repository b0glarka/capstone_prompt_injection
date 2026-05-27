"""Defense A coverage/accuracy curve on the frozen 4,546-row eval set.

Selective-prediction analysis: at confidence threshold T, auto-classify only
rows where max(injection_score, 1 - injection_score) >= T; defer the rest to
Defense B (LLM-as-judge) or human review.

Produces:
  - results/defense_a_coverage_curve.csv  : per-threshold metrics
  - results/figures/defense_a_coverage_accuracy.png : two-panel plot

Course-derived methodology: ECBS5200 Week 5/6 selective-prediction discipline.
The deployment artifact for cost-conscious operators: "at threshold T, X% of
prompts auto-classified at Y% precision on flagged injections; the rest go to
the more expensive Defense B."
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, precision_recall_fscore_support

REPO = Path(__file__).resolve().parents[1]
PRED_CSV = REPO / "results" / "defense_a_full_eval_set.csv"
OUT_CSV = REPO / "results" / "defense_a_coverage_curve.csv"
FIG_PATH = REPO / "results" / "figures" / "defense_a_coverage_accuracy.png"

THRESHOLDS = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 0.99]


def selective_metrics(y_true: np.ndarray, y_pred: np.ndarray, mask: np.ndarray) -> dict:
    yt = y_true[mask]
    yp = y_pred[mask]
    out = {
        "n_covered": int(mask.sum()),
        "n_deferred": int((~mask).sum()),
        "coverage": float(mask.mean()),
    }
    if len(yt) == 0:
        return {**out, "accuracy": float("nan"), "precision_inj": float("nan"),
                "recall_inj": float("nan"), "f1_inj": float("nan")}
    out["accuracy"] = float(accuracy_score(yt, yp))
    if len(np.unique(yt)) == 1 or len(np.unique(yp)) == 1:
        # degenerate; report what we can
        out["precision_inj"] = float("nan")
        out["recall_inj"] = float("nan")
        out["f1_inj"] = float("nan")
    else:
        p, r, f, _ = precision_recall_fscore_support(
            yt, yp, average="binary", pos_label=1, zero_division=0
        )
        out["precision_inj"] = float(p)
        out["recall_inj"] = float(r)
        out["f1_inj"] = float(f)
    return out


def main() -> None:
    df = pd.read_csv(PRED_CSV)
    n = len(df)
    if n != 4546:
        raise RuntimeError(f"Expected 4,546 eval rows; got {n}")

    y_true = df["label"].to_numpy()
    y_pred = df["deberta_pred_label_id"].to_numpy()
    score = df["deberta_injection_score"].to_numpy()
    confidence = np.maximum(score, 1.0 - score)

    rows = []
    for t in THRESHOLDS:
        mask = confidence >= t
        m = selective_metrics(y_true, y_pred, mask)
        m["confidence_threshold"] = t
        rows.append(m)

    out = pd.DataFrame(rows)[
        ["confidence_threshold", "coverage", "n_covered", "n_deferred",
         "accuracy", "precision_inj", "recall_inj", "f1_inj"]
    ]
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_CSV, index=False, float_format="%.4f")
    print(f"Wrote {OUT_CSV.relative_to(REPO)}")
    print(out.to_string(index=False))

    # Plot
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:
        print(f"matplotlib not available; skipping figure ({exc})")
        return

    fig, (ax_acc, ax_inj) = plt.subplots(1, 2, figsize=(11, 4.2))

    cov = out["coverage"].to_numpy()
    acc = out["accuracy"].to_numpy()
    ax_acc.plot(cov, acc, marker="o", linewidth=1.5)
    for i, t in enumerate(out["confidence_threshold"]):
        ax_acc.annotate(f"{t:.2f}", (cov[i], acc[i]), textcoords="offset points",
                        xytext=(4, 4), fontsize=8, color="gray")
    ax_acc.set_xlabel("Coverage (fraction auto-classified)")
    ax_acc.set_ylabel("Selective accuracy on covered rows")
    ax_acc.set_title("Coverage vs accuracy (DeBERTa)")
    ax_acc.grid(True, alpha=0.3)
    ax_acc.set_xlim(0, 1.02)

    p = out["precision_inj"].to_numpy()
    r = out["recall_inj"].to_numpy()
    f = out["f1_inj"].to_numpy()
    ax_inj.plot(cov, p, marker="o", label="precision", linewidth=1.5)
    ax_inj.plot(cov, r, marker="s", label="recall",    linewidth=1.5)
    ax_inj.plot(cov, f, marker="^", label="F1",        linewidth=1.5)
    ax_inj.set_xlabel("Coverage (fraction auto-classified)")
    ax_inj.set_ylabel("Selective metric on injection class")
    ax_inj.set_title("Injection-class P/R/F1 vs coverage (DeBERTa)")
    ax_inj.legend(loc="lower right")
    ax_inj.grid(True, alpha=0.3)
    ax_inj.set_xlim(0, 1.02)

    fig.suptitle("Defense A selective prediction: coverage vs deployment metrics", y=1.02)
    fig.tight_layout()
    FIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_PATH, dpi=140, bbox_inches="tight")
    print(f"Wrote {FIG_PATH.relative_to(REPO)}")


if __name__ == "__main__":
    main()
