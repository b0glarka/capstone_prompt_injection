"""Frozen evaluation set construction for the comparative defense study.

Per `_project_notes/capstone_methodology_decisions.md` decision #1:
  - deepset: all 546 train rows (dataset total below the 2,000 target)
  - neuralchemy: 2,000 from 4,391, stratified by label and by attack subcategory
    on the injection side
  - SPML: 2,000 from 16,012; for consistency with the existing SPML pilot
    (`results/spml_sample_2k.parquet`), the frozen eval set REUSES that
    balanced 1,000 SAFE / 1,000 INJECTION sample rather than re-drawing
  - Seed 42

The output schema is intentionally classifier-agnostic. Downstream pipelines
(Defense A wrappers, Defense B agent + judge) join on `prompt_idx` and treat
`prompt` as the input text. SPML's `system_prompt` is preserved as auxiliary
context but is not fed to the input classifier in Defense A (per the SPML
schema decision: User Prompt is what the input filter sees).

Output:
  - results/eval_set.parquet (gitignored; reproducible from this module)
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from datasets import load_from_disk

SEED = 42
NEURALCHEMY_TARGET = 2_000
SPML_TARGET = 2_000


def _project_root() -> Path:
    here = Path(__file__).resolve()
    for parent in (here, *here.parents):
        if (parent / ".git").exists():
            return parent
    raise RuntimeError("could not locate repo root from src/eval_set.py")


REPO = _project_root()
DATA = REPO / "data"
RES = REPO / "results"


def load_deepset() -> pd.DataFrame:
    df = load_from_disk(DATA / "deepset")["train"].to_pandas().reset_index(drop=True)
    df["prompt_idx"] = "deepset_train_" + df.index.astype(str).str.zfill(4)
    df["dataset"] = "deepset"
    df["subcategory"] = pd.NA
    df["system_prompt"] = pd.NA
    df["severity"] = pd.NA
    return df.rename(columns={"text": "prompt"})[
        ["prompt_idx", "dataset", "prompt", "label", "subcategory", "severity", "system_prompt"]
    ]


def _stratified_sample_neuralchemy(df: pd.DataFrame, target_n: int, seed: int) -> pd.DataFrame:
    """Stratify on label, then within injection class stratify proportionally on subcategory.

    Strategy:
      1. Preserve original benign / injection ratio at scale of `target_n`.
      2. Within injection rows, sample proportionally per subcategory; round up
         small categories so each is represented at least once if it had at least
         one row in the source.
    """
    rng = np.random.default_rng(seed)
    n_total = len(df)
    n_benign_src = int((df["label"] == 0).sum())
    n_injection_src = int((df["label"] == 1).sum())

    n_benign_target = int(round(target_n * n_benign_src / n_total))
    n_injection_target = target_n - n_benign_target

    benign = df[df["label"] == 0]
    benign_idx = rng.choice(benign.index.values, size=min(n_benign_target, len(benign)), replace=False)
    benign_sample = benign.loc[benign_idx]

    injection = df[df["label"] == 1].copy()
    cat_counts = injection["category"].value_counts()
    cat_targets = (cat_counts * n_injection_target / cat_counts.sum()).round().astype(int)

    diff = n_injection_target - int(cat_targets.sum())
    if diff != 0:
        order = cat_targets.index.tolist()
        i = 0
        step = 1 if diff > 0 else -1
        while diff != 0:
            cat = order[i % len(order)]
            new_val = cat_targets[cat] + step
            if 0 <= new_val <= cat_counts[cat]:
                cat_targets[cat] = new_val
                diff -= step
            i += 1
            if i > 10_000:
                break

    injection_pieces = []
    for cat, n_take in cat_targets.items():
        rows = injection[injection["category"] == cat]
        if n_take >= len(rows):
            picked = rows
        else:
            picked_idx = rng.choice(rows.index.values, size=int(n_take), replace=False)
            picked = rows.loc[picked_idx]
        injection_pieces.append(picked)
    injection_sample = pd.concat(injection_pieces) if injection_pieces else injection.iloc[:0]

    out = pd.concat([benign_sample, injection_sample]).sort_index().reset_index(drop=True)
    return out


def load_neuralchemy(target_n: int = NEURALCHEMY_TARGET, seed: int = SEED) -> pd.DataFrame:
    df = load_from_disk(DATA / "neuralchemy")["train"].to_pandas().reset_index(drop=True)
    df["prompt_idx"] = "neuralchemy_train_" + df.index.astype(str).str.zfill(5)
    df["severity"] = df.get("severity", pd.Series([pd.NA] * len(df)))
    sampled = _stratified_sample_neuralchemy(df, target_n, seed)
    sampled["dataset"] = "neuralchemy"
    sampled["system_prompt"] = pd.NA
    return sampled.rename(columns={"text": "prompt", "category": "subcategory"})[
        ["prompt_idx", "dataset", "prompt", "label", "subcategory", "severity", "system_prompt"]
    ]


def load_spml() -> pd.DataFrame:
    """Reuse the existing SPML pilot sample so frozen eval set is consistent with cached predictions."""
    pq = RES / "spml_sample_2k.parquet"
    if not pq.exists():
        raise FileNotFoundError(
            f"{pq} not found. Run scripts/run_defense_a_spml.py first to generate the SPML sample, "
            "or reconcile the eval-set construction with a fresh draw."
        )
    df = pd.read_parquet(pq).reset_index(drop=True)
    df = df.rename(columns={"User Prompt": "prompt", "Prompt injection": "label", "System Prompt": "system_prompt"})
    df["dataset"] = "spml"
    df["subcategory"] = pd.NA
    df["severity"] = df.get("Degree", pd.Series([pd.NA] * len(df)))
    return df[["prompt_idx", "dataset", "prompt", "label", "subcategory", "severity", "system_prompt"]]


def build_eval_set(seed: int = SEED) -> pd.DataFrame:
    """Construct the frozen ~4,546-row evaluation set."""
    parts = [load_deepset(), load_neuralchemy(seed=seed), load_spml()]
    eval_set = pd.concat(parts, ignore_index=True)
    eval_set["label"] = eval_set["label"].astype(int)
    # Normalize mixed-type columns to string so parquet can write them.
    for col in ("severity", "subcategory", "system_prompt"):
        eval_set[col] = eval_set[col].astype("string")
    return eval_set


def save_eval_set(eval_set: pd.DataFrame, path: Optional[Path] = None) -> Path:
    out = path or (RES / "eval_set.parquet")
    out.parent.mkdir(parents=True, exist_ok=True)
    eval_set.to_parquet(out, index=False)
    return out


if __name__ == "__main__":
    es = build_eval_set()
    out = save_eval_set(es)
    print(f"saved {out} with {len(es)} rows")
    print("\nPer-dataset counts:")
    print(es["dataset"].value_counts().to_string())
    print("\nPer-dataset label balance:")
    print(es.groupby(["dataset", "label"]).size().to_string())
    print("\nNeuralchemy subcategory distribution (top 10):")
    nc = es[es["dataset"] == "neuralchemy"]
    print(nc["subcategory"].value_counts().head(10).to_string())
