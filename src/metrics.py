"""Evaluation metrics consolidated for cross-notebook reuse.

Patterns standardized here:
- Bootstrap 95% confidence intervals on accuracy / precision / recall / F1 / AUC
- Cohen's kappa for inter-judge or human-vs-judge agreement
- McNemar's test for paired classifier comparison

Functions are stateless and pandas/numpy-friendly. Notebooks can drop the
inline copies once they import these.
"""

from __future__ import annotations

from typing import Iterable, Tuple

import numpy as np
import pandas as pd
from scipy.stats import binomtest
from sklearn.metrics import (
    accuracy_score,
    cohen_kappa_score,
    precision_recall_fscore_support,
    roc_auc_score,
)


# ---------------------------------------------------------------------------
# Per-row metrics
# ---------------------------------------------------------------------------

def headline_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_score: np.ndarray | None = None,
    pos_label: int = 1,
) -> dict[str, float]:
    """Standard binary classification metrics. Returns scalars.

    AUC is included only when `y_score` is provided.
    """
    p, r, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average="binary", pos_label=pos_label, zero_division=0
    )
    out = {
        "accuracy":  float(accuracy_score(y_true, y_pred)),
        "precision": float(p),
        "recall":    float(r),
        "f1":        float(f1),
    }
    if y_score is not None:
        try:
            out["auc"] = float(roc_auc_score(y_true, y_score))
        except ValueError:
            out["auc"] = float("nan")
    return out


def f_beta(precision: float, recall: float, beta: float = 1.0) -> float:
    """F-beta score. beta > 1 weights recall higher; beta < 1 weights precision higher."""
    if precision + recall == 0:
        return 0.0
    b2 = beta * beta
    return (1 + b2) * precision * recall / (b2 * precision + recall)


# ---------------------------------------------------------------------------
# Bootstrap CIs
# ---------------------------------------------------------------------------

def bootstrap_ci(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_score: np.ndarray | None = None,
    *,
    n_iter: int = 1000,
    seed: int = 42,
    alpha: float = 0.05,
    pos_label: int = 1,
) -> dict[str, Tuple[float, float]]:
    """Nonparametric bootstrap CIs at (1 - alpha) confidence on the headline metrics.

    Resamples (with replacement) `n_iter` times, computes metrics each time,
    returns (lo, hi) percentile bounds.

    Skips iterations where the resample yields a single class (kappa / AUC undefined).
    """
    rng = np.random.default_rng(seed)
    n = len(y_true)
    idx_full = np.arange(n)
    metrics: dict[str, list[float]] = {"accuracy": [], "precision": [], "recall": [], "f1": []}
    if y_score is not None:
        metrics["auc"] = []

    for _ in range(n_iter):
        s = rng.choice(idx_full, size=n, replace=True)
        yt, yp = y_true[s], y_pred[s]
        if len(np.unique(yt)) < 2:
            continue
        p, r, f, _ = precision_recall_fscore_support(yt, yp, average="binary", pos_label=pos_label, zero_division=0)
        metrics["accuracy"].append(accuracy_score(yt, yp))
        metrics["precision"].append(p)
        metrics["recall"].append(r)
        metrics["f1"].append(f)
        if y_score is not None:
            try:
                metrics["auc"].append(roc_auc_score(yt, y_score[s]))
            except ValueError:
                pass

    lo_q = 100 * (alpha / 2)
    hi_q = 100 * (1 - alpha / 2)
    return {
        k: (float(np.percentile(v, lo_q)), float(np.percentile(v, hi_q)))
        for k, v in metrics.items() if v
    }


# ---------------------------------------------------------------------------
# Inter-rater agreement
# ---------------------------------------------------------------------------

def kappa(rater_a: Iterable, rater_b: Iterable) -> float:
    """Cohen's kappa for two raters on a binary or categorical variable."""
    a = np.asarray(list(rater_a))
    b = np.asarray(list(rater_b))
    return float(cohen_kappa_score(a, b))


# ---------------------------------------------------------------------------
# Paired classifier comparison
# ---------------------------------------------------------------------------

def mcnemar(
    y_true: np.ndarray,
    pred_a: np.ndarray,
    pred_b: np.ndarray,
    *,
    exact: bool = True,
) -> dict[str, float]:
    """McNemar's test on paired binary predictions.

    Returns a dict with the discordant cell counts (b: A right and B wrong;
    c: A wrong and B right) and a two-sided p-value.

    Uses the exact binomial test on b vs c by default; pass `exact=False`
    to use the chi-squared approximation (suitable when b + c is large).
    """
    correct_a = (pred_a == y_true)
    correct_b = (pred_b == y_true)
    b = int(np.sum(correct_a & ~correct_b))
    c = int(np.sum(~correct_a & correct_b))
    n = b + c

    if n == 0:
        return {"b": b, "c": c, "p_value": 1.0, "test": "exact_binomial"}

    if exact:
        result = binomtest(min(b, c), n, p=0.5, alternative="two-sided")
        return {"b": b, "c": c, "p_value": float(result.pvalue), "test": "exact_binomial"}
    else:
        chi2 = ((abs(b - c) - 1) ** 2) / n
        from scipy.stats import chi2 as chi2_dist
        p = float(1 - chi2_dist.cdf(chi2, df=1))
        return {"b": b, "c": c, "chi2": float(chi2), "p_value": p, "test": "chi2_continuity_corrected"}
