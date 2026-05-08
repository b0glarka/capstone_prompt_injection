"""Run Meta Prompt Guard 2 86M on all three datasets used in the Defense A pilot.

Mirrors the DeBERTa runs already done. Reuses existing prompt_idx scheme so
predictions can be paired with the DeBERTa predictions for within-Defense-A
comparison.

Caches:
  - cache/defense_a_pg2_deepset.jsonl
  - cache/defense_a_pg2_neuralchemy.jsonl
  - cache/defense_a_pg2_spml.jsonl

Outputs:
  - results/defense_a_pg2_deepset.csv
  - results/defense_a_pg2_neuralchemy.csv
  - results/defense_a_pg2_spml.csv
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from datasets import load_from_disk
from dotenv import load_dotenv
from tqdm import tqdm

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
load_dotenv(REPO_ROOT / ".env")

from src.cache import append_records, existing_keys, load_records
from src.defense_a.prompt_guard import PromptGuard2Detector

DATA = REPO_ROOT / "data"
RES = REPO_ROOT / "results"
CACHE = REPO_ROOT / "cache"
CACHE.mkdir(parents=True, exist_ok=True)


def load_dataset_with_idx(name: str) -> pd.DataFrame:
    if name == "deepset":
        df = load_from_disk(DATA / "deepset")["train"].to_pandas().reset_index(drop=True)
        df["prompt_idx"] = "deepset_train_" + df.index.astype(str).str.zfill(4)
        return df[["prompt_idx", "text", "label"]]
    if name == "neuralchemy":
        df = load_from_disk(DATA / "neuralchemy")["train"].to_pandas().reset_index(drop=True)
        df["prompt_idx"] = "neuralchemy_train_" + df.index.astype(str).str.zfill(5)
        return df[["prompt_idx", "text", "label", "category"]]
    if name == "spml":
        sample = pd.read_parquet(RES / "spml_sample_2k.parquet")
        sample = sample.rename(columns={"User Prompt": "text", "Prompt injection": "label"})
        return sample[["prompt_idx", "text", "label"]]
    raise ValueError(name)


def run_one(name: str, detector: PromptGuard2Detector, batch: int = 32) -> None:
    cache_path = CACHE / f"defense_a_pg2_{name}.jsonl"
    df = load_dataset_with_idx(name)
    print(f"\n=== {name}: {len(df)} rows ===")
    done = existing_keys(cache_path, key="prompt_idx")
    todo = df[~df["prompt_idx"].isin(done)]
    print(f"cached: {len(done)}, to run: {len(todo)}")

    if len(todo) > 0:
        for start in tqdm(range(0, len(todo), batch), desc=f"{name} inference"):
            chunk = todo.iloc[start : start + batch]
            preds = detector.predict(chunk["text"].tolist())
            records = [
                {"prompt_idx": row["prompt_idx"], **pred}
                for (_, row), pred in zip(chunk.iterrows(), preds)
            ]
            append_records(cache_path, records)

    preds = pd.DataFrame(load_records(cache_path))
    preds = preds.rename(columns={
        "label": "pred_label",
        "label_id": "pred_label_id",
        "score": "pred_score",
    })
    out = df.merge(preds, on="prompt_idx", how="inner")
    out_csv = RES / f"defense_a_pg2_{name}.csv"
    out.to_csv(out_csv, index=False)
    print(f"saved {out_csv} ({len(out)} rows)")


def main() -> None:
    detector = PromptGuard2Detector(batch_size=16)
    print(f"device: {detector.device}, model: {detector.model_name}")
    for ds in ["deepset", "neuralchemy", "spml"]:
        run_one(ds, detector)


if __name__ == "__main__":
    main()
