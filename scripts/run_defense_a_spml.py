"""Run ProtectAI DeBERTa on a 2,000-row stratified subsample of SPML.

Sampling: 1,000 SAFE + 1,000 INJECTION from SPML train (16,012 rows), seed 42.
Input to classifier: User Prompt column (system prompt is internal agent context,
not the surface the input filter sees in a real deployment).
prompt_idx values reference original SPML row positions (zero-padded 5-digit index).
"""

import sys
from pathlib import Path

import pandas as pd
from datasets import load_from_disk
from tqdm import tqdm

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.cache import append_records, existing_keys
from src.defense_a.deberta import DebertaInjectionDetector

DATA_DIR    = REPO_ROOT / "data"
CACHE_DIR   = REPO_ROOT / "cache"
RESULTS_DIR = REPO_ROOT / "results"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
CACHE_PATH  = CACHE_DIR / "defense_a_deberta_spml.jsonl"
SAMPLE_PATH = RESULTS_DIR / "spml_sample_2k.parquet"

RANDOM_SEED = 42
BATCH_SIZE  = 32

# ── Load full SPML train split ────────────────────────────────────────────────
df = load_from_disk(DATA_DIR / "spml")["train"].to_pandas()
# Assign prompt_idx BEFORE sampling, so values reference original row positions.
df["prompt_idx"] = "spml_train_" + df.index.astype(str).str.zfill(5)
print(f"loaded {len(df)} rows")
print("label balance:", df["Prompt injection"].value_counts().to_dict())

# ── Stratified sample: 1,000 SAFE + 1,000 INJECTION ──────────────────────────
safe_sample = (
    df[df["Prompt injection"] == 0]
    .sample(n=1000, random_state=RANDOM_SEED)
)
inj_sample = (
    df[df["Prompt injection"] == 1]
    .sample(n=1000, random_state=RANDOM_SEED)
)
sample = pd.concat([safe_sample, inj_sample]).sort_index().reset_index(drop=True)
assert len(sample) == 2000, f"expected 2000 rows, got {len(sample)}"
assert sample["Prompt injection"].value_counts().to_dict() == {0: 1000, 1: 1000}, \
    "unexpected class balance in sample"

sample.to_parquet(SAMPLE_PATH, index=False)
print(f"saved 2,000-row sample to {SAMPLE_PATH}")

# ── Inference: skip already-cached rows ──────────────────────────────────────
done = existing_keys(CACHE_PATH, key="prompt_idx")
todo = sample[~sample["prompt_idx"].isin(done)].reset_index(drop=True)
print(f"cached: {len(done)}, to run: {len(todo)}")

if len(todo) > 0:
    detector = DebertaInjectionDetector(batch_size=16)
    print(f"device: {detector.device}")

    for start in tqdm(range(0, len(todo), BATCH_SIZE), desc="inference"):
        chunk = todo.iloc[start : start + BATCH_SIZE]
        preds = detector.predict(chunk["User Prompt"].tolist())
        records = [
            {"prompt_idx": row["prompt_idx"], **pred}
            for (_, row), pred in zip(chunk.iterrows(), preds)
        ]
        append_records(CACHE_PATH, records)

    print("inference complete")
else:
    print("all rows already cached")
