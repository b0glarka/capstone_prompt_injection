"""Re-judge the 800-row BIPIA email-QA evaluation under v1.25 (Sonnet).

The agent responses are cached in cache/bipia_email_agent.jsonl. This script
re-runs only the judge step, adding sonnet_verdict_v125 columns to
results/bipia_email_qa_results.csv alongside the existing v1.21 columns.

BIPIA does not use per-row operator_intent (the judge handles task-from-query
intent for BIPIA email-QA via dataset="bipia").

Output: results/bipia_email_qa_results.csv updated with v1.25 columns;
cache at cache/bipia_email_judge_sonnet_v125.jsonl.

Cost: ~$8.80 (800 rows * Sonnet 4.6 list price).

Run from repo root:
  .venv/Scripts/python.exe scripts/rejudge_v125_bipia.py
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
RESULTS_CSV = RESULTS / "bipia_email_qa_results.csv"
PROMPTS_CSV = RESULTS / "bipia_email_qa_prompts.csv"
AGENT_CACHE = CACHE / "bipia_email_agent.jsonl"
JUDGE_CACHE = CACHE / "bipia_email_judge_sonnet_v125.jsonl"


def main() -> None:
    results = pd.read_csv(RESULTS_CSV)
    prompts = pd.read_csv(PROMPTS_CSV)
    print(f"Loaded {len(results)} BIPIA result rows, {len(prompts)} prompt rows")

    prompt_map = prompts.set_index("row_id")["full_prompt"].to_dict()
    agent_records = {r["row_id"]: r for r in load_records(AGENT_CACHE) if "row_id" in r}
    print(f"  {len(prompt_map)} prompts, {len(agent_records)} agent responses cached")

    judge = ClaudeJudge(model="claude-sonnet-4-6")
    print(f"\nUsing judge: ClaudeJudge model=claude-sonnet-4-6 rubric=v1.25\n")

    JUDGE_CACHE.parent.mkdir(parents=True, exist_ok=True)
    done = existing_keys(JUDGE_CACHE, key="row_id")
    todo = [r for _, r in results.iterrows() if r["row_id"] not in done]
    print(f"Cached={len(done)}, to_judge={len(todo)}")

    for row in tqdm(todo, desc="BIPIA Sonnet v1.25"):
        rid = row["row_id"]
        user_prompt = prompt_map.get(rid, "") or ""
        agent_response = (agent_records.get(rid, {}) or {}).get("response", "") or ""
        result = judge.judge_v125(
            user_prompt=user_prompt,
            agent_response=agent_response,
            dataset="bipia",
            operator_intent=None,
        )
        append_records(JUDGE_CACHE, [{"row_id": rid, **result}])
        time.sleep(0.05)

    cached = {r["row_id"]: r for r in load_records(JUDGE_CACHE) if "row_id" in r}
    results["sonnet_verdict_v125"] = results["row_id"].map(lambda k: cached.get(k, {}).get("verdict"))
    results["sonnet_categories_v125"] = results["row_id"].map(
        lambda k: json.dumps(cached.get(k, {}).get("hijack_categories", []))
    )
    results["sonnet_reason_v125"] = results["row_id"].map(lambda k: cached.get(k, {}).get("reason", ""))
    results["sonnet_blocked_v125"] = results["row_id"].map(
        lambda k: cached.get(k, {}).get("judge_blocked", False)
    )

    results.to_csv(RESULTS_CSV, index=False)
    print(f"\nWrote {RESULTS_CSV} with v1.25 columns appended.")
    print(f"  v1.25 verdict distribution: {results['sonnet_verdict_v125'].value_counts().to_dict()}")


if __name__ == "__main__":
    main()
