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
# Wilson score interval for a binomial proportion
# ---------------------------------------------------------------------------

def wilson_ci(
    successes: int,
    n: int,
    alpha: float = 0.05,
) -> Tuple[float, float]:
    """Wilson score 95% (default) confidence interval for a binomial proportion.

    Recommended over the normal-approximation (Wald) interval for any n, and
    over Clopper-Pearson when nominal coverage matters more than guaranteed
    coverage (Brown, Cai and DasGupta 2001, "Interval Estimation for a
    Binomial Proportion", Statistical Science 16(2): 101-133).

    Properties:
    - Documented good coverage down to n approx 5-10
    - Asymmetric: at p_hat = 0 the interval is [0, hi] not [-hw, hw]; at
      p_hat = 1 it is [lo, 1] not [1-hw, 1+hw]
    - No resampling, no random seed

    Args:
        successes: number of positive outcomes (e.g., true positives).
        n: total trials (e.g., positives in the test set for a recall calc).
        alpha: 1 - confidence level. Default 0.05 for 95% CI.

    Returns:
        (lo, hi) tuple of the lower and upper bounds in [0, 1].

    Notes:
        At n = 0 returns (0.0, 1.0) (the only honest interval for no data).
        Uses scipy.stats.binomtest(...).proportion_ci(method="wilson") which
        applies the textbook Wilson formula (no continuity correction).
    """
    if n == 0:
        return (0.0, 1.0)
    result = binomtest(int(successes), int(n))
    lo, hi = result.proportion_ci(confidence_level=1 - alpha, method="wilson")
    return (float(lo), float(hi))


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
# Paired-bootstrap CI on the difference between two defenses
# ---------------------------------------------------------------------------

def bootstrap_paired_difference_ci(
    y_true: np.ndarray,
    pred_a: np.ndarray,
    pred_b: np.ndarray,
    *,
    metric: str = "f1",
    n_iter: int = 1000,
    seed: int = 42,
    alpha: float = 0.05,
    pos_label: int = 1,
) -> dict[str, float | tuple[float, float]]:
    """Paired bootstrap CI on metric(A) - metric(B) on the same rows.

    For each of `n_iter` resamples (with replacement, indices shared by A and B),
    computes the chosen metric for both predictors on the resampled rows and
    records the difference. Returns:

    - "point": point estimate of metric(A) - metric(B) on the full sample
    - "ci": (lo, hi) percentile bounds on the difference at (1 - alpha) confidence
    - "p_share_a_better": share of resamples where metric(A) > metric(B)
    - "n_valid": number of resamples that yielded both classes in y_true

    metric: one of {"f1", "precision", "recall", "accuracy"}. The course's
    Week 4 paired-bootstrap pattern, as recommended in the methodology audit.
    Excludes-zero CIs are stronger evidence than McNemar p-values alone because
    they carry the magnitude of the difference.
    """
    metric = metric.lower()
    if metric not in {"f1", "precision", "recall", "accuracy"}:
        raise ValueError(f"metric must be one of f1/precision/recall/accuracy, got {metric!r}")

    def _score(yt: np.ndarray, yp: np.ndarray) -> float:
        if metric == "accuracy":
            return float(accuracy_score(yt, yp))
        p, r, f, _ = precision_recall_fscore_support(
            yt, yp, average="binary", pos_label=pos_label, zero_division=0
        )
        return {"f1": float(f), "precision": float(p), "recall": float(r)}[metric]

    point = _score(y_true, pred_a) - _score(y_true, pred_b)

    rng = np.random.default_rng(seed)
    n = len(y_true)
    idx_full = np.arange(n)
    diffs: list[float] = []
    a_better = 0

    for _ in range(n_iter):
        s = rng.choice(idx_full, size=n, replace=True)
        yt = y_true[s]
        if len(np.unique(yt)) < 2:
            continue
        diff = _score(yt, pred_a[s]) - _score(yt, pred_b[s])
        diffs.append(diff)
        if diff > 0:
            a_better += 1

    if not diffs:
        return {"point": float(point), "ci": (float("nan"), float("nan")), "p_share_a_better": float("nan"), "n_valid": 0}

    lo = float(np.percentile(diffs, 100 * (alpha / 2)))
    hi = float(np.percentile(diffs, 100 * (1 - alpha / 2)))
    return {
        "point": float(point),
        "ci": (lo, hi),
        "p_share_a_better": float(a_better / len(diffs)),
        "n_valid": int(len(diffs)),
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
