"""Run ProtectAI DeBERTa on the full neuralchemy dataset (4391 rows)."""

import sys
from pathlib import Path

import pandas as pd
from datasets import load_from_disk
from tqdm import tqdm

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.cache import append_records, existing_keys
from src.defense_a.deberta import DebertaInjectionDetector

DATA_DIR  = REPO_ROOT / "data"
CACHE_DIR = REPO_ROOT / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_PATH = CACHE_DIR / "defense_a_deberta_neuralchemy.jsonl"

df = load_from_disk(DATA_DIR / "neuralchemy")["train"].to_pandas().reset_index(drop=True)
df["prompt_idx"] = "neuralchemy_train_" + df.index.astype(str).str.zfill(5)
print(f"loaded {len(df)} rows")

done = existing_keys(CACHE_PATH, key="prompt_idx")
todo = df[~df["prompt_idx"].isin(done)]
print(f"cached: {len(done)}, to run: {len(todo)}")

if len(todo) > 0:
    detector = DebertaInjectionDetector(batch_size=16)
    print(f"device: {detector.device}")
    BATCH = 32
    for start in tqdm(range(0, len(todo), BATCH), desc="inference"):
        chunk = todo.iloc[start:start + BATCH]
        preds = detector.predict(chunk["text"].tolist())
        records = [
            {"prompt_idx": row["prompt_idx"], **pred}
            for (_, row), pred in zip(chunk.iterrows(), preds)
        ]
        append_records(CACHE_PATH, records)
    print("inference complete")
else:
    print("all rows already cached")
