"""Generate a 200-row stratified label-audit sample across the three datasets.

Output: results/label_audit_sample.csv
Schema: prompt_idx, dataset, prompt, dataset_label, audit_label, ambiguous, notes

The audit_label, ambiguous, and notes columns are blank, ready to be filled in
by the auditor (Boga) using the operational definitions in
reports/operational_definitions.md.

Allocation: 67 deepset + 67 neuralchemy + 66 SPML = 200 rows total.
Within each dataset, stratified by gold label (50/50 SAFE / INJECTION).
Random seed 42, deterministic.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from datasets import load_from_disk

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
DATA = REPO / "data"
RES = REPO / "results"

SEED = 42
PER_DS = {"deepset": 67, "neuralchemy": 67, "spml": 66}


def stratified(df: pd.DataFrame, label_col: str, n: int, rng: np.random.Generator) -> pd.DataFrame:
    """Sample ~half-and-half across the binary label column. Deterministic given rng."""
    half = n // 2
    extra = n - 2 * half
    safe = df[df[label_col] == 0]
    inj  = df[df[label_col] == 1]
    safe_n = min(half, len(safe))
    inj_n  = min(half + extra, len(inj))
    s_idx = rng.choice(safe.index.values, size=safe_n, replace=False)
    i_idx = rng.choice(inj.index.values,  size=inj_n,  replace=False)
    chosen = pd.concat([safe.loc[s_idx], inj.loc[i_idx]])
    return chosen.sample(frac=1, random_state=SEED).reset_index(drop=True)


def main() -> None:
    rng = np.random.default_rng(SEED)
    rows = []

    # deepset
    d = load_from_disk(DATA / "deepset")["train"].to_pandas().reset_index(drop=True)
    d["prompt_idx"] = "deepset_train_" + d.index.astype(str).str.zfill(4)
    d_sample = stratified(d, "label", PER_DS["deepset"], rng)
    for _, r in d_sample.iterrows():
        rows.append({
            "prompt_idx": r["prompt_idx"],
            "dataset": "deepset",
            "prompt": r["text"],
            "dataset_label": int(r["label"]),
        })

    # neuralchemy
    nc = load_from_disk(DATA / "neuralchemy")["train"].to_pandas().reset_index(drop=True)
    nc["prompt_idx"] = "neuralchemy_train_" + nc.index.astype(str).str.zfill(5)
    nc_sample = stratified(nc, "label", PER_DS["neuralchemy"], rng)
    for _, r in nc_sample.iterrows():
        rows.append({
            "prompt_idx": r["prompt_idx"],
            "dataset": "neuralchemy",
            "prompt": r["text"],
            "dataset_label": int(r["label"]),
        })

    # spml: stratify on User Prompt + Prompt injection
    sp = load_from_disk(DATA / "spml")["train"].to_pandas().reset_index(drop=True)
    sp["prompt_idx"] = "spml_train_" + sp.index.astype(str).str.zfill(5)
    sp = sp.rename(columns={"Prompt injection": "label", "User Prompt": "text"})
    sp_sample = stratified(sp, "label", PER_DS["spml"], rng)
    for _, r in sp_sample.iterrows():
        rows.append({
            "prompt_idx": r["prompt_idx"],
            "dataset": "spml",
            "prompt": r["text"],
            "dataset_label": int(r["label"]),
        })

    out = pd.DataFrame(rows)
    out["audit_label"] = ""       # to be filled in: 0, 1, or "ambiguous"
    out["ambiguous"]   = ""        # boolean flag, optional
    out["notes"]       = ""        # free text

    out_path = RES / "label_audit_sample.csv"
    out.to_csv(out_path, index=False)
    print(f"saved {out_path} ({len(out)} rows)")
    print("Per-dataset counts:")
    print(out["dataset"].value_counts().to_string())
    print("\nPer-dataset label balance:")
    print(out.groupby(["dataset", "dataset_label"]).size().to_string())


if __name__ == "__main__":
    main()
