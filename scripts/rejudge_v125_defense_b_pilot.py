"""Re-judge the 500-row Defense B pilot under the v1.25 rubric (Sonnet).

The agent responses are already cached in results/defense_b_pilot.csv. This
script re-runs only the judge step, adding sonnet_verdict_v125 columns
alongside the existing v1.21 columns. Cached agent responses are not
modified; no Together AI / Groq calls are made.

Output: results/defense_b_pilot.csv updated with v1.25 columns; cache at
cache/defense_b_judge_sonnet_v125_pilot.jsonl.

Cost: ~$5.50 (500 rows * Sonnet 4.6 list price).

Run from repo root:
  .venv/Scripts/python.exe scripts/rejudge_v125_defense_b_pilot.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pandas as pd
from tqdm import tqdm

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from dotenv import load_dotenv
load_dotenv(REPO / ".env")

from src.cache import append_records, existing_keys, load_records
from src.defense_b.judge import ClaudeJudge

CACHE = REPO / "cache"
RESULTS = REPO / "results"
PILOT_CSV = RESULTS / "defense_b_pilot.csv"
EVAL_SET = RESULTS / "eval_set.parquet"
CACHE_PATH = CACHE / "defense_b_judge_sonnet_v125_pilot.jsonl"


def main() -> None:
    df = pd.read_csv(PILOT_CSV, encoding="utf-8-sig")
    print(f"Loaded {len(df)} rows from {PILOT_CSV.name}")
    print(f"  Dataset distribution: {df['dataset'].value_counts().to_dict()}")
    print(f"  Label distribution: {df['label'].value_counts().to_dict()}")

    # Load the eval set so we can look up the original prompt text (the pilot
    # CSV stores agent responses but not the input prompts) and SPML
    # system_prompts (needed for Step 0 operator intent; matches the
    # post-SPML-fix methodology used for the v1.21 results in this CSV).
    eval_df = pd.read_parquet(EVAL_SET)
    eval_df["prompt_idx"] = eval_df["prompt_idx"].astype(str)
    prompt_map = eval_df.set_index("prompt_idx")["prompt"].to_dict()
    spml_prompts = eval_df[eval_df["dataset"] == "spml"].set_index("prompt_idx")["system_prompt"].to_dict()
    print(f"  Loaded {len(prompt_map)} prompts and {len(spml_prompts)} SPML system_prompts from eval set")

    judge = ClaudeJudge(model="claude-sonnet-4-6")
    print(f"\nUsing judge: ClaudeJudge model=claude-sonnet-4-6 rubric=v1.25\n")

    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    done = existing_keys(CACHE_PATH, key="prompt_idx")
    todo = [r for _, r in df.iterrows() if str(r["prompt_idx"]) not in done]
    print(f"Cached={len(done)}, to_judge={len(todo)}")

    for row in tqdm(todo, desc="Sonnet v1.25"):
        pid = str(row["prompt_idx"])
        ds = str(row.get("dataset", "deepset")).lower()
        user_prompt = prompt_map.get(pid, "") or ""
        # SPML uses per-row system_prompt as operator intent for Step 0.
        oi = spml_prompts.get(pid) if ds == "spml" else None
        result = judge.judge_v125(
            user_prompt=user_prompt,
            agent_response=row.get("agent_response", "") or "",
            dataset=ds,
            operator_intent=oi,
        )
        append_records(CACHE_PATH, [{"prompt_idx": pid, **result}])
        time.sleep(0.05)

    cached = {str(r["prompt_idx"]): r for r in load_records(CACHE_PATH) if "prompt_idx" in r}
    df["sonnet_verdict_v125"] = df["prompt_idx"].astype(str).map(lambda k: cached.get(k, {}).get("verdict"))
    df["sonnet_categories_v125"] = df["prompt_idx"].astype(str).map(
        lambda k: json.dumps(cached.get(k, {}).get("hijack_categories", []))
    )
    df["sonnet_reason_v125"] = df["prompt_idx"].astype(str).map(lambda k: cached.get(k, {}).get("reason", ""))
    df["sonnet_blocked_v125"] = df["prompt_idx"].astype(str).map(
        lambda k: cached.get(k, {}).get("judge_blocked", False)
    )

    df.to_csv(PILOT_CSV, index=False, encoding="utf-8-sig")
    print(f"\nWrote {PILOT_CSV} with v1.25 columns appended.")
    print(f"  v1.25 verdict distribution: {df['sonnet_verdict_v125'].value_counts().to_dict()}")


if __name__ == "__main__":
    main()
