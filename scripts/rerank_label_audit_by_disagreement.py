"""Active-learning rerank of the 200-row label audit sample.

Sorts the existing label audit sample by Defense A classifier disagreement
(DeBERTa vs Prompt Guard 2). Rows where the two classifiers disagree are
boundary cases most likely to be either labeling errors or genuinely
ambiguous prompts; concentrating labeling effort on those rows sharpens
the noise-rate estimate at the same labeling cost.

Primary sort: binary disagreement (1 if hard predictions differ, else 0), DESC.
Tiebreaker: |deberta_injection_score - pg2_injection_score|, DESC.

Preserves the original sample's audit_label / ambiguous / notes columns as
empty cells; only the row order changes. Original file is not modified.

Outputs `results/label_audit_sample_disagreement_sorted.csv` with an added
`disagreement_rank` column for traceability (1 = highest-priority labeling
candidate, 200 = lowest).

Course-derived methodology: ECBS5200 Week 4 disagreement-driven monitoring
framing applied to the label-audit selection step.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
SAMPLE_CSV = REPO / "results" / "label_audit_sample.csv"
PRED_CSV = REPO / "results" / "defense_a_full_eval_set.csv"
EXTRAS_CSV = REPO / "results" / "defense_a_audit_extras.csv"
OUT_CSV = REPO / "results" / "label_audit_sample_disagreement_sorted.csv"

PRED_COLS = [
    "prompt_idx", "deberta_pred_label_id", "pg2_pred_label_id",
    "deberta_injection_score", "pg2_injection_score",
]


def main() -> None:
    sample = pd.read_csv(SAMPLE_CSV)
    pred = pd.read_csv(PRED_CSV)[PRED_COLS]
    if EXTRAS_CSV.exists():
        extras = pd.read_csv(EXTRAS_CSV)[PRED_COLS]
        pred = pd.concat([pred, extras], ignore_index=True)
        print(f"Merged predictions from {PRED_CSV.name} and {EXTRAS_CSV.name}")
    else:
        print(f"No {EXTRAS_CSV.name}; using only frozen-eval-set predictions")

    if len(sample) != 200:
        raise RuntimeError(f"Expected 200 audit rows; got {len(sample)}")

    merged = sample.merge(pred, on="prompt_idx", how="left", validate="one_to_one")
    has_pred = merged["deberta_pred_label_id"].notna()
    n_missing = int((~has_pred).sum())
    if n_missing:
        print(f"Note: {n_missing} of 200 audit rows still have no Defense A predictions; "
              f"they will appear at the bottom of the priority list in their original order.")

    merged["binary_disagreement"] = (
        merged["deberta_pred_label_id"] != merged["pg2_pred_label_id"]
    ).astype("Int64")
    merged["score_distance"] = np.abs(
        merged["deberta_injection_score"] - merged["pg2_injection_score"]
    )
    merged["has_eval_prediction"] = has_pred.astype(int)

    # Sort: rows with predictions first (ordered by disagreement, then score distance),
    # then unmatched rows in their original order.
    merged["__orig"] = np.arange(len(merged))
    merged = merged.sort_values(
        by=["has_eval_prediction", "binary_disagreement", "score_distance", "__orig"],
        ascending=[False, False, False, True],
        kind="mergesort",
    ).reset_index(drop=True)
    merged = merged.drop(columns="__orig")
    merged["disagreement_rank"] = np.arange(1, len(merged) + 1)

    cols = [
        "disagreement_rank", "prompt_idx", "dataset", "prompt",
        "dataset_label", "audit_label", "ambiguous", "notes",
        "has_eval_prediction", "binary_disagreement", "score_distance",
        "deberta_pred_label_id", "pg2_pred_label_id",
        "deberta_injection_score", "pg2_injection_score",
    ]
    out = merged[cols]
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_CSV, index=False)

    matched = out[out["has_eval_prediction"] == 1]
    n_matched = len(matched)
    n_disagree = int(matched["binary_disagreement"].sum())
    print(f"Wrote {OUT_CSV.relative_to(REPO)}")
    print(f"Audit rows with Defense A predictions: {n_matched} / 200")
    print(f"Among those, binary classifier disagreement: {n_disagree} / {n_matched} "
          f"({100*n_disagree/max(n_matched,1):.1f}%)")
    print("Top 5 boundary cases (rank, dataset, gold label, deberta score, pg2 score):")
    print(out.head(5)[
        ["disagreement_rank", "dataset", "dataset_label",
         "deberta_injection_score", "pg2_injection_score"]
    ].to_string(index=False))


if __name__ == "__main__":
    main()
