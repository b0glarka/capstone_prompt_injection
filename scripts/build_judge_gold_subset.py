"""Build the 150-row judge gold subset from Defense B pilot output.

Stratified sampling design (per `_local/user_todo_audit_and_curation.md` Task 3):
  - ~50 cases where Sonnet said CLEAN but the prompt was an injection (potential
    judge misses; high-information for false-negative analysis)
  - ~50 cases where Sonnet said HIJACKED (verify the judge's hits)
  - ~25 cases where Sonnet and a cheap-judge sweep disagreed (most informative for
    rubric robustness; requires the cheap-judge sweep to be run first)
  - ~25 cases that are unambiguous anchors (Sonnet flagged HIJACKED with high
    confidence reasoning, OR Sonnet flagged CLEAN on a benign prompt)

Falls back gracefully if the cheap-judge sweep is not yet complete (skips the
disagreement-stratum and fills with additional unambiguous anchors).

Outputs:
  results/judge_gold_subset.csv
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

RES = REPO / "results"
SEED = 42

PILOT_CSV = RES / "defense_b_pilot.csv"
SWEEP_CSV = RES / "defense_b_judge_cost_comparison.csv"
OUT_CSV   = RES / "judge_gold_subset.csv"

# Stratum sizes (sum to 150)
N_SONNET_MISS  = 50  # Sonnet said clean, prompt is labeled injection
N_SONNET_HIT   = 50  # Sonnet said hijacked
N_DISAGREEMENT = 25  # Sonnet and a cheap judge disagree
N_ANCHOR       = 25  # Unambiguous one-way-or-other anchors


def _take(df: pd.DataFrame, n: int, seed: int) -> pd.DataFrame:
    if len(df) <= n:
        return df.copy()
    return df.sample(n=n, random_state=seed)


def main() -> None:
    if not PILOT_CSV.exists():
        raise FileNotFoundError(f"{PILOT_CSV} not found. Run scripts/run_defense_b_pilot.py first.")
    pilot = pd.read_csv(PILOT_CSV)
    print(f"pilot rows: {len(pilot)}")

    # Merge in the prompt text from the frozen eval set (pilot CSV doesn't duplicate prompt text)
    es = pd.read_parquet(REPO / "results" / "eval_set.parquet")[["prompt_idx", "prompt"]]
    pilot = pilot.merge(es, on="prompt_idx", how="left")
    assert pilot["prompt"].notna().all(), "merge with eval_set.parquet left missing prompts"

    rng = np.random.default_rng(SEED)
    sweep_available = SWEEP_CSV.exists()
    if sweep_available:
        sweep = pd.read_csv(SWEEP_CSV)
        merged = pilot.merge(
            sweep[["prompt_idx", "haiku45_hijacked", "gpt4mini_hijacked"]],
            on="prompt_idx", how="left",
        )
        print(f"cheap-judge sweep available; merged on {len(merged)} rows")
    else:
        merged = pilot.copy()
        merged["haiku45_hijacked"]  = np.nan
        merged["gpt4mini_hijacked"] = np.nan
        print("cheap-judge sweep not yet run; disagreement stratum will fall back to anchors")

    # Normalize fields
    merged["sonnet_hijacked"] = merged["judge_hijacked"].astype("boolean").astype("Int64")
    merged["is_attack"] = (merged["label"] == 1)

    # Stratum 1: Sonnet said clean but the prompt is a labeled injection (potential miss)
    miss_pool = merged[(merged["sonnet_hijacked"] == 0) & (merged["is_attack"])]
    miss = _take(miss_pool, N_SONNET_MISS, SEED)

    # Stratum 2: Sonnet said hijacked (sample across datasets to keep balance)
    hit_pool = merged[merged["sonnet_hijacked"] == 1]
    hit = _take(hit_pool, N_SONNET_HIT, SEED + 1)

    # Stratum 3: Sonnet vs cheap-judge disagreement
    if sweep_available:
        disagree_pool = merged[
            (merged["sonnet_hijacked"].notna())
            & ((merged["sonnet_hijacked"] != merged["haiku45_hijacked"]) |
               (merged["sonnet_hijacked"] != merged["gpt4mini_hijacked"]))
        ]
        disagree = _take(disagree_pool, N_DISAGREEMENT, SEED + 2)
    else:
        disagree = pd.DataFrame(columns=merged.columns)

    # Stratum 4: anchors. Confident clean (Sonnet clean on benign prompt) and confident hijacked
    anchor_clean_pool = merged[(merged["sonnet_hijacked"] == 0) & (~merged["is_attack"])]
    anchor_hij_pool   = merged[(merged["sonnet_hijacked"] == 1)]
    half = (N_ANCHOR + (N_DISAGREEMENT if not sweep_available else 0)) // 2
    anchor_clean = _take(anchor_clean_pool, half, SEED + 3)
    anchor_hij = _take(
        anchor_hij_pool,
        (N_ANCHOR + (N_DISAGREEMENT if not sweep_available else 0)) - half,
        SEED + 4,
    )

    parts = [miss, hit, disagree, anchor_clean, anchor_hij]
    gold = pd.concat(parts).drop_duplicates("prompt_idx").reset_index(drop=True)

    # If we collected fewer than 150 unique cases (small pilot, overlapping pools), pad from the leftover pool
    if len(gold) < 150:
        leftover = merged[~merged["prompt_idx"].isin(gold["prompt_idx"])]
        pad = _take(leftover, 150 - len(gold), SEED + 5)
        gold = pd.concat([gold, pad]).reset_index(drop=True)

    # Trim to 150 and shuffle (avoid stratum-order anchoring bias during labeling)
    gold = gold.head(150).sample(frac=1, random_state=SEED + 6).reset_index(drop=True)

    # Slim the column set to what the human labeler needs, plus internal-use columns
    keep_cols = [
        "prompt_idx", "dataset", "subcategory", "label",
        "prompt", "agent_response",
        "judge_hijacked", "judge_reasoning",
    ]
    if sweep_available:
        keep_cols += ["haiku45_hijacked", "gpt4mini_hijacked"]
    gold = gold[keep_cols].rename(columns={"judge_hijacked": "sonnet_verdict", "judge_reasoning": "sonnet_reasoning"})

    # Add blank human-labeling columns
    gold["human_verdict"]    = ""  # 0, 1, or 'ambiguous'
    gold["hijack_categories"] = ""  # comma-separated H1..H5
    gold["notes"]            = ""

    gold.to_csv(OUT_CSV, index=False)
    print(f"saved {OUT_CSV} with {len(gold)} rows")
    print("\nStratum counts (approximate; deduped):")
    print(f"  Sonnet potential misses (label=1, judge=clean): up to {len(miss)} rows")
    print(f"  Sonnet hits (judge=hijacked):                   up to {len(hit)} rows")
    print(f"  Cross-judge disagreement:                       up to {len(disagree)} rows")
    print(f"  Anchors (clean benign + confident hijacks):     up to {len(anchor_clean) + len(anchor_hij)} rows")
    print("\nDataset distribution of gold subset:")
    print(gold.groupby("dataset").size().to_string())


if __name__ == "__main__":
    main()
