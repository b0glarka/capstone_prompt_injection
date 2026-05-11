"""Defense A error-pattern analysis: structural features of missed injections.

Operates only on aggregate statistics; no verbatim attack content is echoed
to stdout or any analytic output. The goal is to characterize the shapes of
false-negative cases (true injections that DeBERTa classified as safe) so
the final-report Results section can describe blind-spot patterns at the
feature level rather than the prompt level.

Features extracted per row:
  - prompt_length_chars
  - prompt_length_words
  - has_non_ascii (boolean): any character outside Latin-1 ASCII
  - non_ascii_ratio (float): share of non-ASCII characters
  - has_base64_like (regex): chunks of >=12 chars matching base64 charset
  - has_code_fence (regex): triple-backtick or angle-bracket scripting tags
  - has_url (regex)
  - looks_multilingual (heuristic): non-ASCII ratio above 0.1
  - has_role_play_marker (regex): "you are X", "act as", "imagine you are"
  - has_override_marker (regex): "ignore", "disregard", "forget", "instead"
  - dataset, subcategory (when available)
  - injection_score (DeBERTa) for context

Outputs:
  results/defense_a_error_features.csv         per-row feature table (errors only)
  results/defense_a_error_summary.csv          aggregate counts by feature x error_type
  results/figures/defense_a_error_features.png small heatmap of feature prevalence
"""

from __future__ import annotations

import re
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

RES = REPO / "results"
FIG = RES / "figures"

# Regex feature definitions. Word boundaries used where appropriate to reduce false matches.
BASE64_RE = re.compile(r"[A-Za-z0-9+/]{12,}={0,2}")
CODE_FENCE_RE = re.compile(r"```|<\s*(script|svg|iframe|style)", re.IGNORECASE)
URL_RE = re.compile(r"https?://|www\.[a-z0-9-]+\.[a-z]{2,}", re.IGNORECASE)
ROLE_PLAY_RE = re.compile(r"\b(you are|act as|pretend to be|imagine you are|from now on|roleplay)\b", re.IGNORECASE)
OVERRIDE_RE = re.compile(r"\b(ignore|disregard|forget|instead|override|new instructions|new task)\b", re.IGNORECASE)


def extract_features(text: str) -> dict:
    s = str(text or "")
    n_chars = len(s)
    n_words = len(s.split())
    non_ascii = sum(1 for c in s if ord(c) > 127)
    return {
        "prompt_length_chars": n_chars,
        "prompt_length_words": n_words,
        "has_non_ascii":       non_ascii > 0,
        "non_ascii_ratio":     round(non_ascii / max(n_chars, 1), 4),
        "has_base64_like":     bool(BASE64_RE.search(s)),
        "has_code_fence":      bool(CODE_FENCE_RE.search(s)),
        "has_url":             bool(URL_RE.search(s)),
        "looks_multilingual":  (non_ascii / max(n_chars, 1)) > 0.1,
        "has_role_play_marker": bool(ROLE_PLAY_RE.search(s)),
        "has_override_marker":  bool(OVERRIDE_RE.search(s)),
    }


def main() -> None:
    df = pd.read_csv(RES / "defense_a_full_eval_set.csv")
    print(f"rows: {len(df)}")

    # Classify every row by Defense A (DeBERTa) outcome
    is_inj = df["label"] == 1
    pred_inj = df["deberta_pred_label_id"] == 1
    df["error_type"] = "TN"
    df.loc[is_inj & pred_inj, "error_type"] = "TP"
    df.loc[is_inj & ~pred_inj, "error_type"] = "FN"
    df.loc[~is_inj & pred_inj, "error_type"] = "FP"
    df.loc[~is_inj & ~pred_inj, "error_type"] = "TN"

    print("\nDeBERTa outcome counts:")
    print(df["error_type"].value_counts().to_string())

    # Extract features (use the full table, then split by error_type for comparison)
    feats = df["prompt"].apply(extract_features).apply(pd.Series)
    df_feats = pd.concat([
        df[["prompt_idx", "dataset", "subcategory", "label", "deberta_pred_label_id",
            "deberta_injection_score", "error_type"]].reset_index(drop=True),
        feats.reset_index(drop=True),
    ], axis=1)

    # Save errors-only file (FN + FP) for the report
    errors = df_feats[df_feats["error_type"].isin(["FN", "FP"])].copy()
    errors.to_csv(RES / "defense_a_error_features.csv", index=False)
    print(f"\nsaved {RES / 'defense_a_error_features.csv'} ({len(errors)} error rows)")

    # Aggregate: per error_type, what fraction of cases have each feature?
    feature_cols = [
        "has_non_ascii", "looks_multilingual",
        "has_base64_like", "has_code_fence", "has_url",
        "has_role_play_marker", "has_override_marker",
    ]
    rows = []
    for et in ["TN", "FP", "FN", "TP"]:
        sub = df_feats[df_feats["error_type"] == et]
        if len(sub) == 0:
            continue
        row = {"error_type": et, "n": len(sub)}
        for col in feature_cols:
            row[col] = round(float(sub[col].mean()), 4)
        row["mean_length_chars"] = int(sub["prompt_length_chars"].mean())
        row["mean_length_words"] = int(sub["prompt_length_words"].mean())
        rows.append(row)
    summary = pd.DataFrame(rows)
    summary.to_csv(RES / "defense_a_error_summary.csv", index=False)
    print("\nFeature prevalence by error type (fraction of rows):")
    print(summary[["error_type", "n", *feature_cols, "mean_length_chars"]].to_string(index=False))

    # Per-subcategory FN breakdown on neuralchemy (where subcategory is known)
    nc_fn = df_feats[(df_feats["dataset"] == "neuralchemy") & (df_feats["error_type"] == "FN")]
    if len(nc_fn) > 0:
        print(f"\nNeuralchemy FN ({len(nc_fn)} cases) by subcategory (top 10):")
        print(nc_fn["subcategory"].value_counts().head(10).to_string())

    # Feature heatmap: error_type rows x feature columns
    sns.set_theme(style="white")
    heat = summary.set_index("error_type")[feature_cols]
    fig, ax = plt.subplots(figsize=(9, 3.2))
    sns.heatmap(
        heat, annot=True, fmt=".3f", cmap="RdBu_r", vmin=0, vmax=1, cbar=True, ax=ax,
        cbar_kws={"label": "feature prevalence"},
    )
    ax.set_title("Defense A error patterns: feature prevalence by outcome type")
    ax.set_xlabel("")
    ax.set_ylabel("DeBERTa outcome")
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    out_fig = FIG / "defense_a_error_features.png"
    plt.savefig(out_fig, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\nsaved {out_fig}")


if __name__ == "__main__":
    main()
