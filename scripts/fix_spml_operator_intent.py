"""Re-judge SPML rows with operator_intent properly passed.

The v1.21 re-judge pass passed operator_intent=None for ALL rows, including
SPML. The judges then defaulted to baseline helpful-assistant intent for the
§3.2 Step 0 anchor, systematically missing H3 persona-substitution attacks
against SPML deployed operator roles (Finance Bot, Healthcare Advisor, etc.).

This script fixes that. For each affected CSV, it:
1. Backs up the file to _local/pre_spml_fix/<filename>
2. Loads SPML dataset to get each SPML row's system_prompt (joining on prompt_idx)
3. For SPML rows only, re-calls each relevant judge with operator_intent=system_prompt
4. Updates the SPML rows' v1.21 judge verdict columns in place
5. Leaves deepset/neuralchemy/BIPIA rows untouched (their §3.2 Step 0 anchors
   were already correct because they don't have role-specific system_prompts)
6. Leaves human-labeled columns (human_verdict, hijack_categories, notes)
   untouched on every row

Output CSVs are written back to the same paths, utf-8-sig.

Cost ceiling per file: $2. Resumable via JSONL caches under
cache/spml_fix/<filename_stem>_<judge>.jsonl.
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

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
load_dotenv(REPO / ".env")

from src.cache import append_records, existing_keys, load_records
from src.defense_b.judge import ClaudeJudge, GPT4oJudge

RES = REPO / "results"
CACHE = REPO / "cache" / "spml_fix"
CACHE.mkdir(parents=True, exist_ok=True)
BACKUP_DIR = REPO / "_local" / "pre_spml_fix"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

SPML_DIR = REPO / "data" / "spml"


def _build_spml_system_prompt_map() -> dict[str, str]:
    """Build a {prompt_idx: system_prompt} map for all SPML rows."""
    sp = load_from_disk(SPML_DIR)["train"].to_pandas().reset_index(drop=True)
    sp["prompt_idx"] = "spml_train_" + sp.index.astype(str).str.zfill(5)
    return sp.set_index("prompt_idx")["System Prompt"].to_dict()


def _build_spml_user_prompt_map() -> dict[str, str]:
    """Build a {prompt_idx: user_prompt} map for all SPML rows.

    `defense_b_pilot.csv` and the cross-family pilot CSVs do not preserve
    the user prompt, so we load it from the SPML dataset for the judge call.
    """
    sp = load_from_disk(SPML_DIR)["train"].to_pandas().reset_index(drop=True)
    sp["prompt_idx"] = "spml_train_" + sp.index.astype(str).str.zfill(5)
    return sp.set_index("prompt_idx")["User Prompt"].to_dict()


def _judge_call(judge_name: str, user_prompt: str, agent_response: str, operator_intent: str) -> dict:
    """Call the right judge_v121 method by name with SPML operator_intent.

    Uses the same default model IDs that the original v1.21 re-judge used,
    so the comparison is apples-to-apples (only operator_intent changes).
    """
    if judge_name == "sonnet":
        judge = ClaudeJudge(model="claude-sonnet-4-6")
        out = judge.judge_v121(user_prompt, agent_response, dataset="spml", operator_intent=operator_intent)
    elif judge_name == "haiku":
        judge = ClaudeJudge(model="claude-haiku-4-5")
        out = judge.judge_v121(user_prompt, agent_response, dataset="spml", operator_intent=operator_intent)
    elif judge_name == "gpt4mini":
        judge = GPT4oJudge(model="gpt-4o-mini")
        out = judge.judge_v121(user_prompt, agent_response, dataset="spml", operator_intent=operator_intent)
    else:
        raise ValueError(f"unknown judge {judge_name}")
    return out


def _judge_all_spml(
    df: pd.DataFrame,
    judge_name: str,
    cache_path: Path,
    user_prompt_col: str | None,
    agent_response_col: str,
    system_prompt_map: dict[str, str],
    user_prompt_fallback: dict[str, str] | None = None,
    agent_response_fallback: dict[str, str] | None = None,
) -> dict[str, dict]:
    """Re-judge all SPML rows with the given judge. Caches per prompt_idx.

    If `user_prompt_col` is None or the column is absent, falls back to
    `user_prompt_fallback[prompt_idx]` (typically loaded from the SPML dataset).

    If `agent_response_col` is absent from df, falls back to
    `agent_response_fallback[prompt_idx]` (typically loaded from the pilot CSV).
    """
    done = existing_keys(cache_path, key="prompt_idx")
    spml = df[df["dataset"] == "spml"]
    use_up_col = user_prompt_col is not None and user_prompt_col in df.columns
    use_ar_col = agent_response_col in df.columns
    todo = []
    for _, r in spml.iterrows():
        pid = r["prompt_idx"]
        if pid in done:
            continue
        up = r[user_prompt_col] if use_up_col else (user_prompt_fallback or {}).get(pid, "")
        ar = r[agent_response_col] if use_ar_col else (agent_response_fallback or {}).get(pid, "")
        todo.append((pid, up, ar))
    if not todo:
        print(f"  [{judge_name}] all {len(spml)} SPML rows already cached")
    else:
        print(f"  [{judge_name}] re-judging {len(todo)} SPML rows ({len(done)} already cached)")
        for pid, up, ar in tqdm(todo, desc=f"{judge_name} SPML re-judge"):
            sp = system_prompt_map.get(pid, "")
            if not sp:
                print(f"    WARNING: no system_prompt for {pid}; skipping")
                continue
            out = _judge_call(judge_name, str(up) if pd.notna(up) else "", str(ar) if pd.notna(ar) else "", sp)
            append_records(cache_path, [{"prompt_idx": pid, **out}])
    return {r["prompt_idx"]: r for r in load_records(cache_path)}


def _update_spml_columns(df: pd.DataFrame, judge_records: dict, prefix: str) -> pd.DataFrame:
    """Update SPML rows' v1.21 judge columns from re-judge records."""
    spml_mask = df["dataset"] == "spml"
    for idx, row in df[spml_mask].iterrows():
        pid = row["prompt_idx"]
        rec = judge_records.get(pid)
        if rec is None:
            continue
        df.at[idx, f"{prefix}_verdict_v121"] = rec.get("verdict", "")
        cats = rec.get("hijack_categories", [])
        if isinstance(cats, list):
            df.at[idx, f"{prefix}_categories_v121"] = json.dumps(cats)
        else:
            df.at[idx, f"{prefix}_categories_v121"] = str(cats)
        df.at[idx, f"{prefix}_reason_v121"] = rec.get("reason", "")
        if f"{prefix}_blocked_v121" in df.columns:
            df.at[idx, f"{prefix}_blocked_v121"] = rec.get("judge_blocked_v121", False)
    return df


def fix_file(
    csv_path: Path,
    judges_to_rerun: list[str],
    judge_col_prefixes: dict[str, str],
    user_prompt_col: str | None,
    agent_response_col: str,
    system_prompt_map: dict[str, str],
    user_prompt_fallback: dict[str, str] | None = None,
    agent_response_fallback: dict[str, str] | None = None,
) -> None:
    """Apply the SPML operator_intent fix to one CSV file.

    Args:
        csv_path: path to the CSV file to update in place.
        judges_to_rerun: e.g. ["sonnet"] or ["sonnet", "haiku", "gpt4mini"].
        judge_col_prefixes: maps judge name to its column prefix in this CSV
            (e.g. {"sonnet": "sonnet", "haiku": "haiku45", "gpt4mini": "gpt4mini"}).
        user_prompt_col: column name for the user prompt in this CSV.
        agent_response_col: column name for the agent response in this CSV.
    """
    print(f"\n=== {csv_path.name} ===")

    # Backup
    backup_path = BACKUP_DIR / csv_path.name
    if not backup_path.exists():
        shutil.copy2(csv_path, backup_path)
        print(f"  backed up to {backup_path.relative_to(REPO)}")

    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    spml_count = int((df["dataset"] == "spml").sum())
    print(f"  loaded {len(df)} rows; {spml_count} are SPML")
    if spml_count == 0:
        print(f"  no SPML rows; nothing to fix")
        return

    for judge_name in judges_to_rerun:
        prefix = judge_col_prefixes[judge_name]
        cache_path = CACHE / f"{csv_path.stem}__{judge_name}.jsonl"
        records = _judge_all_spml(
            df, judge_name, cache_path,
            user_prompt_col=user_prompt_col,
            agent_response_col=agent_response_col,
            system_prompt_map=system_prompt_map,
            user_prompt_fallback=user_prompt_fallback,
            agent_response_fallback=agent_response_fallback,
        )
        df = _update_spml_columns(df, records, prefix)

    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"  wrote {csv_path.relative_to(REPO)} (SPML rows updated in place)")


def main() -> None:
    print("Loading SPML system_prompt + user_prompt maps ...")
    sys_prompt_map = _build_spml_system_prompt_map()
    user_prompt_map = _build_spml_user_prompt_map()
    print(f"  {len(sys_prompt_map)} SPML rows indexed")

    # Load pilot agent responses for cost_comparison fallback (cost_comparison
    # doesn't store agent_response; only pilot does).
    pilot_df = pd.read_csv(RES / "defense_b_pilot.csv")
    pilot_agent_response_map = dict(zip(pilot_df["prompt_idx"], pilot_df["agent_response"]))
    print(f"  {len(pilot_agent_response_map)} pilot agent responses indexed (for cost_comparison fallback)")

    # 1. Defense B 500-row pilot (Llama agent): re-judge SPML rows with Sonnet v1.21
    # The pilot CSV doesn't store user prompts; we fall back to the SPML dataset.
    fix_file(
        RES / "defense_b_pilot.csv",
        judges_to_rerun=["sonnet"],
        judge_col_prefixes={"sonnet": "sonnet"},
        user_prompt_col=None,
        agent_response_col="agent_response",
        system_prompt_map=sys_prompt_map,
        user_prompt_fallback=user_prompt_map,
    )

    # 2. Cheap-judge sweep CSV: re-judge SPML rows with Haiku and GPT-4o-mini.
    # This CSV has 'prompt' but not 'agent_response'; fall back to the pilot's responses.
    fix_file(
        RES / "defense_b_judge_cost_comparison.csv",
        judges_to_rerun=["haiku", "gpt4mini"],
        judge_col_prefixes={"haiku": "haiku45", "gpt4mini": "gpt4mini"},
        user_prompt_col="prompt",
        agent_response_col="agent_response",
        system_prompt_map=sys_prompt_map,
        user_prompt_fallback=user_prompt_map,
        agent_response_fallback=pilot_agent_response_map,
    )

    # 3. Gold subset: re-judge SPML rows with all 3 judges
    fix_file(
        RES / "judge_gold_subset_audited.csv",
        judges_to_rerun=["sonnet", "haiku", "gpt4mini"],
        judge_col_prefixes={"sonnet": "sonnet", "haiku": "haiku45", "gpt4mini": "gpt4mini"},
        user_prompt_col="prompt",
        agent_response_col="agent_response",
        system_prompt_map=sys_prompt_map,
        user_prompt_fallback=user_prompt_map,
    )

    # 4. Cross-family pilots (Sonnet judge only on each)
    for fname in ["defense_b_pilot_qwen.csv", "defense_b_pilot_mistral.csv", "defense_b_pilot_deepseek.csv"]:
        path = RES / fname
        if not path.exists():
            print(f"\n[skip] {fname} not yet present (cross-family pilot may still be running)")
            continue
        fix_file(
            path,
            judges_to_rerun=["sonnet"],
            judge_col_prefixes={"sonnet": "sonnet"},
            user_prompt_col=None,
            agent_response_col="agent_response",
            system_prompt_map=sys_prompt_map,
            user_prompt_fallback=user_prompt_map,
        )

    print("\nDone.")


if __name__ == "__main__":
    main()
