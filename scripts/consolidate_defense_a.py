"""Consolidate Defense A predictions from per-dataset caches into one unified output.

Pulls per-dataset predictions for both classifiers (ProtectAI DeBERTa,
Meta Prompt Guard 2) from their JSONL caches, joins each per-classifier
union onto the frozen evaluation set on `prompt_idx`, and produces a
single tidy CSV: `results/defense_a_full_eval_set.csv`.

Schema (one row per eval-set prompt):
  prompt_idx, dataset, subcategory, severity, label,
  deberta_pred_label, deberta_pred_label_id, deberta_injection_score, deberta_pred_score,
  pg2_pred_label,     pg2_pred_label_id,     pg2_injection_score,     pg2_pred_score,
  prompt, system_prompt

The eval set filters naturally: neuralchemy 4,391 rows -> 2,000 sampled,
SPML's full 16K -> 2,000 sampled.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from src.cache import load_records

RES = REPO / "results"
CACHE = REPO / "cache"

# Per-classifier cache files, one per dataset
DEBERTA_FILES = {
    "deepset":     CACHE / "defense_a_deberta_deepset.jsonl",
    "neuralchemy": CACHE / "defense_a_deberta_neuralchemy.jsonl",
    "spml":        CACHE / "defense_a_deberta_spml.jsonl",
}
PG2_FILES = {
    "deepset":     CACHE / "defense_a_pg2_deepset.jsonl",
    "neuralchemy": CACHE / "defense_a_pg2_neuralchemy.jsonl",
    "spml":        CACHE / "defense_a_pg2_spml.jsonl",
}


def union_predictions(file_map: dict[str, Path], prefix: str) -> pd.DataFrame:
    """Concatenate per-dataset prediction caches into one frame; rename columns with prefix."""
    parts = []
    for ds, path in file_map.items():
        if not path.exists():
            raise FileNotFoundError(f"missing prediction cache: {path}")
        df = pd.DataFrame(load_records(path))
        parts.append(df)
    full = pd.concat(parts, ignore_index=True)
    rename = {
        "label":           f"{prefix}_pred_label",
        "label_id":        f"{prefix}_pred_label_id",
        "injection_score": f"{prefix}_injection_score",
        "score":           f"{prefix}_pred_score",
    }
    return full.rename(columns=rename)


def main() -> None:
    eval_set = pd.read_parquet(RES / "eval_set.parquet")
    print(f"frozen eval set: {len(eval_set)} rows")

    deberta = union_predictions(DEBERTA_FILES, "deberta")
    pg2 = union_predictions(PG2_FILES, "pg2")
    print(f"deberta predictions union: {len(deberta)} rows")
    print(f"pg2 predictions union:     {len(pg2)} rows")

    # Inner-join: only eval-set rows where BOTH classifiers have predictions
    merged = (
        eval_set
        .merge(deberta, on="prompt_idx", how="left")
        .merge(pg2,     on="prompt_idx", how="left")
    )

    # Sanity: every eval-set row should have predictions from both classifiers
    n_missing_deberta = merged["deberta_pred_label_id"].isna().sum()
    n_missing_pg2     = merged["pg2_pred_label_id"].isna().sum()
    if n_missing_deberta or n_missing_pg2:
        print(f"WARNING: {n_missing_deberta} rows missing DeBERTa, {n_missing_pg2} rows missing PG2")
        print("Missing prompt_idx examples (deberta):")
        print(merged[merged["deberta_pred_label_id"].isna()]["prompt_idx"].head(5).to_list())

    # Reorder columns for readability
    front = [
        "prompt_idx", "dataset", "subcategory", "severity", "label",
        "deberta_pred_label_id", "deberta_injection_score",
        "pg2_pred_label_id",     "pg2_injection_score",
    ]
    rest = [c for c in merged.columns if c not in front]
    out = merged[front + rest]

    out_path = RES / "defense_a_full_eval_set.csv"
    out.to_csv(out_path, index=False)
    print(f"\nsaved {out_path} ({len(out)} rows, {len(out.columns)} columns)")

    # Quick sanity summary
    print("\nLabel x dataset cross-tab:")
    print(out.groupby(["dataset", "label"]).size().to_string())
    print("\nPer-classifier prediction balance overall:")
    print("DeBERTa:", out["deberta_pred_label_id"].value_counts().to_dict())
    print("PG2:    ", out["pg2_pred_label_id"].value_counts().to_dict())


if __name__ == "__main__":
    main()
