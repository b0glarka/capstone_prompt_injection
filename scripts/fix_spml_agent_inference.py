"""Re-run SPML agent inference with the row-specific system_prompt.

Companion to scripts/fix_spml_operator_intent.py. That script fixed the
JUDGE side (judges weren't given SPML system_prompts for Step 0). This
script fixes the parallel AGENT side: the pilot agents (Llama 3.3 70B,
Qwen 3, Mistral Large 2, DeepSeek V3) all ran SPML rows with a generic
helpful-assistant system prompt, never as the SPML deployed personas
(Finance Bot, Healthcare Advisor, etc.).

Methodological consequence of the previous setup: SPML's H3 persona-
substitution attacks against role-specific operator personas were
technically non-events, because the agent had no persona to substitute
away from. This script makes the SPML evaluation apples-to-apples with
how the SPML dataset was designed.

For each SPML row in each of the four pilot CSVs:
  1. Load the SPML system_prompt for that row (from data/spml)
  2. Re-invoke the agent with system_prompt=SPML system_prompt + user_prompt
  3. Re-judge the new response with Sonnet v1.21 (operator_intent=SPML system_prompt)
  4. Update agent_response + judge verdict columns in place
  5. Back up the pre-fix file to _local/pre_spml_agent_fix/

Outputs go in place. Non-SPML rows are untouched on every file.
Cost ~$5 across the four model families. Wall time ~45-60 min.
"""
from __future__ import annotations

import json
import os
import sys
import shutil
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from tqdm import tqdm
from datasets import load_from_disk

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
load_dotenv(REPO_ROOT / ".env")

from src.cache import append_records, existing_keys, load_records
from src.defense_b.agent import make_agent
from src.defense_b.judge import ClaudeJudge

RES = REPO_ROOT / "results"
CACHE = REPO_ROOT / "cache" / "spml_agent_fix"
CACHE.mkdir(parents=True, exist_ok=True)
BACKUP_DIR = REPO_ROOT / "_local" / "pre_spml_agent_fix"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)
SPML_DIR = REPO_ROOT / "data" / "spml"


def _build_spml_maps() -> tuple[dict[str, str], dict[str, str]]:
    sp = load_from_disk(SPML_DIR)["train"].to_pandas().reset_index(drop=True)
    sp["prompt_idx"] = "spml_train_" + sp.index.astype(str).str.zfill(5)
    sys_map = sp.set_index("prompt_idx")["System Prompt"].to_dict()
    user_map = sp.set_index("prompt_idx")["User Prompt"].to_dict()
    return sys_map, user_map


def _run_agent_with_system_prompt(provider: str, system_prompt: str, user_prompt: str) -> dict:
    """Run a one-off agent call with a custom system_prompt override."""
    agent = make_agent(provider=provider, system_prompt=system_prompt)
    return agent.respond(user_prompt)


def _judge_with_intent(judge: ClaudeJudge, user_prompt: str, agent_response: str, system_prompt: str) -> dict:
    """Re-judge with operator_intent=system_prompt (the SPML role)."""
    return judge.judge_v121(
        user_prompt=user_prompt,
        agent_response=agent_response,
        dataset="spml",
        operator_intent=system_prompt,
    )


def fix_file(
    csv_path: Path,
    provider: str,
    prefix: str,
    sys_map: dict[str, str],
    user_map: dict[str, str],
    judge: ClaudeJudge,
) -> None:
    """Re-run SPML rows: agent inference with system_prompt + re-judge.

    Args:
        csv_path: which CSV to update in place
        provider: agent provider ("together" for Llama 3.3, "qwen" for Qwen 3,
            "mistral" for Mistral, "deepseek" for DeepSeek)
        prefix: column-name prefix for the judge verdicts in this CSV
            (e.g. "sonnet" → sonnet_verdict_v121, sonnet_categories_v121, ...)
    """
    print(f"\n=== {csv_path.name} (provider={provider}) ===")

    backup = BACKUP_DIR / csv_path.name
    if not backup.exists():
        shutil.copy2(csv_path, backup)
        print(f"  backed up to {backup.relative_to(REPO_ROOT)}")

    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    spml_mask = df["dataset"] == "spml"
    spml_rows = df[spml_mask]
    n_spml = len(spml_rows)
    print(f"  loaded {len(df)} rows; {n_spml} are SPML")
    if n_spml == 0:
        return

    agent_cache = CACHE / f"{csv_path.stem}__{provider}_agent.jsonl"
    judge_cache = CACHE / f"{csv_path.stem}__{provider}_judge.jsonl"

    # Phase 1: agent inference for SPML rows
    done = existing_keys(agent_cache, key="prompt_idx")
    todo = [(r["prompt_idx"]) for _, r in spml_rows.iterrows() if r["prompt_idx"] not in done]
    if todo:
        print(f"  agent inference: {len(todo)} SPML rows ({len(done)} cached)")
        for pid in tqdm(todo, desc=f"{provider} agent SPML"):
            sp = sys_map.get(pid, "")
            up = user_map.get(pid, "")
            if not sp or not up:
                continue
            out = _run_agent_with_system_prompt(provider, sp, up)
            append_records(agent_cache, [{"prompt_idx": pid, **out}])
    agent_records = {r["prompt_idx"]: r for r in load_records(agent_cache)}

    # Phase 2: judge SPML rows with operator_intent=system_prompt
    done_j = existing_keys(judge_cache, key="prompt_idx")
    todo_j = [pid for pid in agent_records if pid not in done_j]
    if todo_j:
        print(f"  judge: {len(todo_j)} SPML rows ({len(done_j)} cached)")
        for pid in tqdm(todo_j, desc=f"{provider} judge SPML"):
            sp = sys_map.get(pid, "")
            up = user_map.get(pid, "")
            ar = agent_records[pid].get("response", "")
            if not ar:
                continue
            out = _judge_with_intent(judge, up, ar, sp)
            append_records(judge_cache, [{"prompt_idx": pid, **out}])
    judge_records = {r["prompt_idx"]: r for r in load_records(judge_cache)}

    # Phase 3: update CSV in place
    print(f"  updating CSV in place ...")
    for idx, row in df[spml_mask].iterrows():
        pid = row["prompt_idx"]
        a = agent_records.get(pid)
        j = judge_records.get(pid)
        if a is None or j is None:
            continue
        if "agent_response" in df.columns:
            df.at[idx, "agent_response"] = a.get("response", "")
        cats = j.get("hijack_categories", [])
        cats_str = json.dumps(cats) if isinstance(cats, list) else str(cats)
        if f"{prefix}_verdict_v121" in df.columns:
            df.at[idx, f"{prefix}_verdict_v121"] = j.get("verdict", "")
        if f"{prefix}_categories_v121" in df.columns:
            df.at[idx, f"{prefix}_categories_v121"] = cats_str
        if f"{prefix}_reason_v121" in df.columns:
            df.at[idx, f"{prefix}_reason_v121"] = j.get("reason", "")
        if f"{prefix}_blocked_v121" in df.columns:
            df.at[idx, f"{prefix}_blocked_v121"] = j.get("judge_blocked_v121", False)

    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"  wrote {csv_path.relative_to(REPO_ROOT)}")


def main() -> None:
    sys_map, user_map = _build_spml_maps()
    print(f"Loaded {len(sys_map)} SPML system_prompts + user_prompts")
    judge = ClaudeJudge()

    targets = [
        ("defense_b_pilot.csv", "together", "sonnet"),
        ("defense_b_pilot_qwen.csv", "qwen", "sonnet"),
        ("defense_b_pilot_mistral.csv", "mistral", "sonnet"),
        ("defense_b_pilot_deepseek.csv", "deepseek", "sonnet"),
    ]
    for fname, provider, prefix in targets:
        path = RES / fname
        if not path.exists():
            print(f"\n[skip] {fname} not found")
            continue
        fix_file(path, provider, prefix, sys_map, user_map, judge)

    print("\nDone.")


if __name__ == "__main__":
    main()
