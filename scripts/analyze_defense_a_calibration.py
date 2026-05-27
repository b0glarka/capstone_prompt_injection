"""Defense A (DeBERTa) calibration analysis: ECE and temperature scaling.

The §5.7b coverage/accuracy curve in the final report shows that DeBERTa's
score distribution is bimodal at 0 and 1, with the curve nearly flat across
confidence thresholds. The natural follow-up question (cited as future work
in §5.7b) is whether post-hoc temperature scaling produces a more graduated
confidence distribution and reduces miscalibration.

This script:
1. Loads Defense A's full-eval-set predictions
   (`results/defense_a_full_eval_set.csv`)
2. Splits into a calibration fold (10% stratified by dataset) and a test
   fold (90%)
3. Fits a single temperature parameter T on the calibration fold using NLL
   loss against the binary labels
4. Applies T to test-fold logits; computes ECE pre/post and reliability
   diagrams
5. Writes a markdown summary to `results/defense_a_calibration_metrics.md`
   and a reliability-diagram PNG to `results/figures/defense_a_calibration.png`

References:
- Guo et al. (2017), "On calibration of modern neural networks". The
  temperature-scaling-on-logits approach this script implements.
- Chidambaram et al. (2024), "How Flawed Is ECE? An Analysis via Logit
  Smoothing". Caveats on ECE that we cite alongside the numbers.
"""
from __future__ import annotations

from pathlib import Path
import math

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F

REPO = Path(__file__).resolve().parents[1]
RES = REPO / "results"
FIG = RES / "figures"
FIG.mkdir(parents=True, exist_ok=True)

INPUT = RES / "defense_a_full_eval_set.csv"
OUT_MD = RES / "defense_a_calibration_metrics.md"
OUT_PNG = FIG / "defense_a_calibration.png"

SEED = 42
N_BINS = 10  # equal-width bins for ECE


def expected_calibration_error(probs: np.ndarray, labels: np.ndarray, n_bins: int = N_BINS) -> tuple[float, list[dict]]:
    """Compute ECE with equal-width binning. Returns (ece, per_bin_diagnostics)."""
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    n = len(probs)
    ece = 0.0
    bins = []
    for i in range(n_bins):
        lo, hi = edges[i], edges[i + 1]
        if i == n_bins - 1:
            mask = (probs >= lo) & (probs <= hi)
        else:
            mask = (probs >= lo) & (probs < hi)
        n_bin = int(mask.sum())
        if n_bin == 0:
            bins.append({"low": lo, "high": hi, "n": 0, "mean_conf": float("nan"), "accuracy": float("nan"), "contrib": 0.0})
            continue
        mean_conf = float(probs[mask].mean())
        accuracy = float(labels[mask].mean())
        contrib = (n_bin / n) * abs(mean_conf - accuracy)
        ece += contrib
        bins.append({"low": lo, "high": hi, "n": n_bin, "mean_conf": mean_conf, "accuracy": accuracy, "contrib": contrib})
    return ece, bins


def fit_temperature(logits: np.ndarray, labels: np.ndarray) -> float:
    """Fit a single temperature parameter T using LBFGS to minimise NLL.

    Args:
        logits: shape (N, 2) raw logits (before softmax). For a single-class
            binary problem, we recover logits as log(p) - log(1-p) which is
            equivalent to the standard binary-logit form.
        labels: binary 0/1 labels of length N.

    Returns:
        The fitted temperature scalar (float). T > 1 sharpens overconfidence
        into more uncertain probabilities; T < 1 sharpens the opposite way.
    """
    logits_t = torch.tensor(logits, dtype=torch.float64)
    labels_t = torch.tensor(labels, dtype=torch.long)
    temperature = torch.tensor(1.0, dtype=torch.float64, requires_grad=True)
    optimizer = torch.optim.LBFGS([temperature], lr=0.01, max_iter=100, line_search_fn="strong_wolfe")

    def closure():
        optimizer.zero_grad()
        scaled = logits_t / temperature
        loss = F.cross_entropy(scaled, labels_t)
        loss.backward()
        return loss

    optimizer.step(closure)
    return float(temperature.detach())


def probs_to_binary_logits(p: np.ndarray, eps: float = 1e-7) -> np.ndarray:
    """Recover (logit_safe, logit_injection) pairs from injection-class probabilities.

    Since the dataset has only injection-class probs (not raw logits), we
    invert the softmax: logit_inj = log(p / (1 - p)), logit_safe = 0. This is
    a standard reconstruction; the temperature fit is invariant to the
    additive constant.
    """
    p = np.clip(p, eps, 1.0 - eps)
    logit_inj = np.log(p / (1.0 - p))
    logit_safe = np.zeros_like(logit_inj)
    return np.stack([logit_safe, logit_inj], axis=1)


def temp_scale_probs(p: np.ndarray, T: float, eps: float = 1e-7) -> np.ndarray:
    """Apply temperature T to injection-class probability p; return calibrated p."""
    logits = probs_to_binary_logits(p, eps)
    scaled = logits / T
    # Softmax to recover calibrated injection-class probability
    exp = np.exp(scaled - scaled.max(axis=1, keepdims=True))
    softmax = exp / exp.sum(axis=1, keepdims=True)
    return softmax[:, 1]


def stratified_split(df: pd.DataFrame, frac: float, seed: int = SEED) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Hold out `frac` of rows per dataset for the calibration fold."""
    rng = np.random.default_rng(seed)
    cal_idx = []
    for ds, sub in df.groupby("dataset"):
        n_cal = max(1, int(round(frac * len(sub))))
        cal_idx.extend(rng.choice(sub.index, size=n_cal, replace=False).tolist())
    cal = df.loc[cal_idx].copy()
    test = df.drop(cal_idx).copy()
    return cal, test


def make_reliability_diagram(probs_pre, labels, probs_post, T, out_path):
    """Save a side-by-side reliability diagram for pre/post temperature scaling."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)

    for ax, probs, title in [(axes[0], probs_pre, "Pre-calibration"),
                              (axes[1], probs_post, f"Post-calibration (T = {T:.3f})")]:
        ece, bins = expected_calibration_error(probs, labels)
        widths = []
        heights_conf = []
        heights_acc = []
        for b in bins:
            if b["n"] == 0:
                continue
            widths.append((b["low"] + b["high"]) / 2)
            heights_conf.append(b["mean_conf"])
            heights_acc.append(b["accuracy"])
        ax.bar(widths, heights_acc, width=0.08, alpha=0.6, label="Accuracy", color="C0", edgecolor="black")
        ax.plot([0, 1], [0, 1], "k--", linewidth=1, label="Perfect calibration")
        ax.scatter(widths, heights_conf, color="red", s=30, zorder=5, label="Mean confidence (bin)")
        ax.set_xlabel("Predicted probability (injection class)")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_title(f"{title}\nECE = {ece:.4f}, n = {len(probs)}")
        ax.legend(loc="upper left", fontsize=8)
        ax.grid(alpha=0.3)

    axes[0].set_ylabel("Empirical accuracy in bin")
    plt.tight_layout()
    plt.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close()


def main() -> None:
    df = pd.read_csv(INPUT)
    print(f"Loaded {len(df)} rows from {INPUT.name}")
    print(f"  columns of interest: deberta_injection_score, label, dataset")

    # Drop rows with NaN in critical columns
    df = df.dropna(subset=["deberta_injection_score", "label", "dataset"]).reset_index(drop=True)
    df["label"] = df["label"].astype(int)
    print(f"  after dropping NaN: {len(df)} rows")

    # Per-dataset label distribution
    print()
    print("Per-dataset label distribution:")
    print(df.groupby(["dataset", "label"]).size())

    # Stratified 10% calibration / 90% test split
    cal, test = stratified_split(df, frac=0.10, seed=SEED)
    print(f"\nCalibration fold: {len(cal)} rows; test fold: {len(test)} rows")

    # Fit temperature on calibration fold
    cal_logits = probs_to_binary_logits(cal["deberta_injection_score"].to_numpy())
    cal_labels = cal["label"].to_numpy()
    T = fit_temperature(cal_logits, cal_labels)
    print(f"Fitted temperature T = {T:.4f}")
    print(f"  Interpretation: T > 1 means the original model was overconfident; T < 1 means underconfident.")

    # Apply to test fold
    test_probs_pre = test["deberta_injection_score"].to_numpy()
    test_probs_post = temp_scale_probs(test_probs_pre, T)
    test_labels = test["label"].to_numpy()

    # Compute ECE pre/post on test fold
    ece_pre, bins_pre = expected_calibration_error(test_probs_pre, test_labels)
    ece_post, bins_post = expected_calibration_error(test_probs_post, test_labels)

    print()
    print(f"ECE pre-calibration (test fold, n={len(test_probs_pre)}): {ece_pre:.4f}")
    print(f"ECE post-calibration: {ece_post:.4f}")
    print(f"  delta-ECE = {ece_post - ece_pre:+.4f} ({'improved' if ece_post < ece_pre else 'worse'})")

    # Per-dataset ECE pre/post (test fold)
    print()
    print("Per-dataset ECE (test fold):")
    per_ds_results = []
    for ds, sub in test.groupby("dataset"):
        idx = sub.index
        probs_pre_sub = test_probs_pre[test.index.isin(idx)]
        probs_post_sub = test_probs_post[test.index.isin(idx)]
        labels_sub = test_labels[test.index.isin(idx)]
        e_pre, _ = expected_calibration_error(probs_pre_sub, labels_sub)
        e_post, _ = expected_calibration_error(probs_post_sub, labels_sub)
        per_ds_results.append((ds, len(sub), e_pre, e_post))
        print(f"  {ds:<12s} n={len(sub):<5d}  pre={e_pre:.4f}  post={e_post:.4f}  delta={e_post - e_pre:+.4f}")

    # Reliability diagram
    make_reliability_diagram(test_probs_pre, test_labels, test_probs_post, T, OUT_PNG)
    print(f"\nWrote reliability diagram: {OUT_PNG.relative_to(REPO)}")

    # Write markdown report
    out = []
    out.append("# Defense A calibration analysis (DeBERTa, full eval set)")
    out.append("")
    out.append(f"- Date: 2026-05-27")
    out.append(f"- Method: post-hoc temperature scaling per Guo et al. (2017), single-parameter T fit by minimising NLL on a stratified 10% calibration fold")
    out.append(f"- Input: `results/defense_a_full_eval_set.csv` ({len(df)} rows after dropping NaN)")
    out.append(f"- Calibration fold: {len(cal)} rows (stratified by dataset, seed {SEED})")
    out.append(f"- Test fold: {len(test)} rows (the calibration metrics below are computed on this fold)")
    out.append(f"- ECE caveat: per Chidambaram et al. (2024), binning-based ECE has known pathologies; the directional comparison pre vs post is reliable; the absolute numbers should be read with the standard ECE caveats in mind")
    out.append("")
    out.append(f"## Fitted temperature")
    out.append("")
    out.append(f"`T = {T:.4f}` (T > 1 means original model was overconfident; T < 1 means underconfident)")
    out.append("")
    out.append(f"## Overall ECE pre vs post temperature scaling")
    out.append("")
    out.append(f"| Scope | n | ECE pre | ECE post | Δ |")
    out.append(f"|---|---|---|---|---|")
    out.append(f"| Overall test fold | {len(test_probs_pre)} | {ece_pre:.4f} | {ece_post:.4f} | {ece_post - ece_pre:+.4f} |")
    for ds, n_ds, e_pre, e_post in per_ds_results:
        out.append(f"| {ds} | {n_ds} | {e_pre:.4f} | {e_post:.4f} | {e_post - e_pre:+.4f} |")
    out.append("")
    out.append(f"## Per-bin diagnostics (test fold, post-calibration)")
    out.append("")
    out.append(f"| Bin range | n | Mean confidence | Empirical accuracy | Contribution to ECE |")
    out.append(f"|---|---|---|---|---|")
    for b in bins_post:
        if b["n"] == 0:
            continue
        out.append(f"| [{b['low']:.2f}, {b['high']:.2f}] | {b['n']} | {b['mean_conf']:.4f} | {b['accuracy']:.4f} | {b['contrib']:.4f} |")
    out.append("")
    out.append(f"## Interpretation")
    out.append("")
    out.append(f"DeBERTa's pre-calibration injection-class probabilities show ECE = {ece_pre:.4f} on the test fold. Post-temperature scaling with T = {T:.4f}, ECE = {ece_post:.4f}, a change of {ece_post - ece_pre:+.4f}.")
    out.append("")
    if T > 1.05:
        out.append(f"The fitted T > 1 indicates the model was systematically overconfident; temperature scaling softens the distribution toward more honest uncertainty.")
    elif T < 0.95:
        out.append(f"The fitted T < 1 indicates the model was systematically underconfident; temperature scaling sharpens the distribution toward higher peaked confidence.")
    else:
        out.append(f"The fitted T ≈ 1 indicates the model was already approximately calibrated; temperature scaling has limited effect.")
    out.append("")
    out.append(f"Implication for the §5.7b coverage/accuracy curve: the curve was nearly flat because DeBERTa's pre-calibration score distribution was bimodal at 0 and 1. The calibrated scores (post temperature scaling) {'should produce a more graduated distribution and a more operationally useful coverage curve' if abs(T - 1) > 0.05 else 'remain similar to the pre-calibration distribution since the temperature is close to 1'}. The reliability diagram at `results/figures/defense_a_calibration.png` visualises pre vs post.")

    OUT_MD.write_text("\n".join(out), encoding="utf-8")
    print(f"Wrote {OUT_MD.relative_to(REPO)}")


if __name__ == "__main__":
    main()
