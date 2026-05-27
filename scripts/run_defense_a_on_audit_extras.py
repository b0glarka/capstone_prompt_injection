"""Run Defense A (DeBERTa + Prompt Guard 2) on audit-sample rows outside the eval set.

The 200-row label audit sample was drawn from full source datasets, while the
frozen 4,546-row eval set is a stratified subset. 88 audit rows fall outside
the eval set and therefore have no Defense A predictions in
`results/defense_a_full_eval_set.csv`.

This script runs Defense A on just those 88 rows and writes the predictions
to `results/defense_a_audit_extras.csv` so the active-learning rerank
(`scripts/rerank_label_audit_by_disagreement.py`) can score all 200 audit
rows by classifier disagreement.

Schema matches a subset of `defense_a_full_eval_set.csv` columns:
  prompt_idx, dataset, deberta_pred_label_id, deberta_injection_score,
  pg2_pred_label_id, pg2_injection_score

No re-inference happens on the 112 audit rows already in the eval set; their
predictions stay in `defense_a_full_eval_set.csv` unchanged.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.defense_a.deberta import DebertaInjectionDetector
from src.defense_a.prompt_guard import PromptGuard2Detector

AUDIT_CSV = REPO / "results" / "label_audit_sample.csv"
EVAL_PRED_CSV = REPO / "results" / "defense_a_full_eval_set.csv"
OUT_CSV = REPO / "results" / "defense_a_audit_extras.csv"


def main() -> None:
    audit = pd.read_csv(AUDIT_CSV)
    eval_idx = set(pd.read_csv(EVAL_PRED_CSV, usecols=["prompt_idx"])["prompt_idx"])

    extras = audit[~audit["prompt_idx"].isin(eval_idx)].reset_index(drop=True)
    n = len(extras)
    print(f"Audit rows outside the frozen eval set: {n}")
    if n == 0:
        print("Nothing to do; exiting.")
        return

    prompts = extras["prompt"].astype(str).tolist()

    print("Loading DeBERTa ...")
    deberta = DebertaInjectionDetector()
    print(f"Inferring on {n} prompts ...")
    d_out = deberta.predict(prompts)

    print("Loading Prompt Guard 2 ...")
    pg2 = PromptGuard2Detector()
    print(f"Inferring on {n} prompts ...")
    p_out = pg2.predict(prompts)

    out = pd.DataFrame({
        "prompt_idx": extras["prompt_idx"].values,
        "dataset": extras["dataset"].values,
        "deberta_pred_label_id": [r["label_id"] for r in d_out],
        "deberta_injection_score": [r["injection_score"] for r in d_out],
        "pg2_pred_label_id": [r["label_id"] for r in p_out],
        "pg2_injection_score": [r["injection_score"] for r in p_out],
    })
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_CSV, index=False)
    print(f"Wrote {OUT_CSV.relative_to(REPO)}")
    print("Sanity check: per-dataset counts:")
    print(out["dataset"].value_counts().to_string())


if __name__ == "__main__":
    main()
