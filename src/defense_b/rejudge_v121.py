"""Re-judge cached agent responses with the v1.21 rubric.

This script reads agent responses from existing caches (no agent re-inference),
calls the appropriate judge with the v1.21 rubric, and writes new columns
alongside the original verdicts in the result CSVs.

New columns added (all suffixed _v121):
  sonnet_verdict_v121        CLEAN / HIJACKED / AMBIGUOUS
  sonnet_categories_v121     JSON-encoded list, e.g. '["H1","H3"]'
  sonnet_reason_v121         one-line reason string
  sonnet_blocked_v121        True if judge call was policy-blocked

For the cheap-judge sweep (cost comparison CSV):
  haiku45_verdict_v121, haiku45_categories_v121, haiku45_reason_v121, haiku45_blocked_v121
  gpt4mini_verdict_v121, gpt4mini_categories_v121, gpt4mini_reason_v121, gpt4mini_blocked_v121

For the sensitivity CSV (GPT-4o on 8 deepset rows):
  gpt4o_verdict_v121, gpt4o_categories_v121, gpt4o_reason_v121, gpt4o_blocked_v121

The original columns (judge_hijacked, judge_reasoning, etc.) are preserved
unchanged. The v1.21 columns are additive.

Caches for v1.21 judge calls live in:
  cache/defense_b_judge_pilot_sonnet_v121.jsonl
  cache/defense_b_judge_pilot_haiku45_v121.jsonl
  cache/defense_b_judge_pilot_gpt4o_mini_v121.jsonl
  cache/bipia_email_judge_v121.jsonl
  cache/defense_b_judge_sensitivity_gpt4o_v121.jsonl

Run from repo root:
  .venv/Scripts/python.exe src/defense_b/rejudge_v121.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# Ensure repo root is on sys.path when run directly
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pandas as pd
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv(_REPO_ROOT / ".env")

from src.cache import append_records, existing_keys, load_records
from src.defense_b.judge import ClaudeJudge, GPT4oJudge, HaikuJudge

CACHE = _REPO_ROOT / "cache"
RESULTS = _REPO_ROOT / "results"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_cache_by_key(path: Path, key: str) -> dict:
    """Load JSONL cache into a dict keyed by `key`."""
    return {r[key]: r for r in load_records(path) if key in r}


def _cats_to_str(cats: list) -> str:
    """Serialize hijack_categories list to a compact JSON string for CSV storage."""
    return json.dumps(cats, ensure_ascii=False)


def _add_v121_cols(
    df: pd.DataFrame,
    cache_path: Path,
    id_col: str,
    prefix: str,
    judge_calls: list[tuple],  # list of (id_value, user_prompt, agent_response, dataset, operator_intent)
    judge_fn,
) -> pd.DataFrame:
    """Run v1.21 judge for rows not yet in cache, then merge results into df.

    Args:
        df: result dataframe to augment.
        cache_path: JSONL path for this judge / pipeline.
        id_col: column name used as the row key (prompt_idx or row_id).
        prefix: column prefix, e.g. 'sonnet' -> sonnet_verdict_v121 etc.
        judge_calls: list of tuples (id_val, user_prompt, agent_response, dataset, operator_intent).
        judge_fn: a callable(user_prompt, agent_response, dataset, operator_intent) -> dict.

    Returns:
        df with new columns added.
    """
    done = existing_keys(cache_path, key=id_col)
    todo = [(id_val, up, ar, ds, oi) for (id_val, up, ar, ds, oi) in judge_calls if id_val not in done]
    print(f"  [{cache_path.name}] cached={len(done)}, to_judge={len(todo)}")

    for id_val, user_prompt, agent_response, dataset, operator_intent in tqdm(todo, desc=cache_path.stem):
        result = judge_fn(user_prompt, agent_response, dataset, operator_intent)
        record = {id_col: id_val, **result}
        append_records(cache_path, [record])
        time.sleep(0.05)  # small delay to stay within rate limits

    # Load full cache (including just-written records) and merge
    cache_data = _load_cache_by_key(cache_path, id_col)

    verdict_col = f"{prefix}_verdict_v121"
    cats_col = f"{prefix}_categories_v121"
    reason_col = f"{prefix}_reason_v121"
    blocked_col = f"{prefix}_blocked_v121"

    df[verdict_col] = df[id_col].map(lambda k: cache_data.get(k, {}).get("verdict"))
    df[cats_col] = df[id_col].map(
        lambda k: _cats_to_str(cache_data.get(k, {}).get("hijack_categories", []))
    )
    df[reason_col] = df[id_col].map(lambda k: cache_data.get(k, {}).get("reason", ""))
    df[blocked_col] = df[id_col].map(lambda k: cache_data.get(k, {}).get("judge_blocked_v121", False))

    return df


# ---------------------------------------------------------------------------
# Pipeline 1: Defense B 500-row pilot (Sonnet primary)
# ---------------------------------------------------------------------------

def rejudge_pilot() -> pd.DataFrame:
    """Re-judge defense_b_pilot.csv with Sonnet v1.21."""
    print("\n=== Pipeline 1: Defense B pilot (Sonnet v1.21) ===")
    df = pd.read_csv(RESULTS / "defense_b_pilot.csv")

    # Agent responses are inline in the pilot CSV
    agent_cache = _load_cache_by_key(CACHE / "defense_b_agent_pilot.jsonl", "prompt_idx")

    judge = ClaudeJudge()

    def _judge_fn(user_prompt, agent_response, dataset, operator_intent=None):
        return judge.judge_v121(user_prompt, agent_response, dataset=dataset, operator_intent=operator_intent)

    # Build call list: (prompt_idx, user_prompt, agent_response, dataset, operator_intent)
    calls = []
    for _, row in df.iterrows():
        pid = row["prompt_idx"]
        # agent_response is in the pilot CSV directly
        agent_resp = row["agent_response"] if "agent_response" in row else ""
        # dataset is in the pilot CSV; default to deepset if missing
        dataset = str(row.get("dataset", "deepset")).lower() if "dataset" in row else "deepset"
        # SPML rows would have operator_intent; not present in deepset pilot
        operator_intent = None
        calls.append((pid, "", agent_resp, dataset, operator_intent))
        # Note: user_prompt is not stored in pilot CSV; the judge only needs the
        # agent_response to assess H1-H5 in context. However, passing the prompt
        # improves judge accuracy for H1 (task pivot detection). We fetch it from
        # the agent cache where available.
        if pid in agent_cache:
            # agent cache doesn't store user_prompt either -- use empty string
            pass

    # Try to get prompts from cost comparison CSV (which has a prompt column)
    cost_csv = RESULTS / "defense_b_judge_cost_comparison.csv"
    if cost_csv.exists():
        cost_df = pd.read_csv(cost_csv)
        prompt_map = dict(zip(cost_df["prompt_idx"], cost_df["prompt"]))
    else:
        prompt_map = {}

    calls_with_prompts = []
    for (pid, _, agent_resp, dataset, oi) in calls:
        user_prompt = prompt_map.get(pid, "")
        calls_with_prompts.append((pid, user_prompt, agent_resp, dataset, oi))

    df = _add_v121_cols(
        df,
        CACHE / "defense_b_judge_pilot_sonnet_v121.jsonl",
        id_col="prompt_idx",
        prefix="sonnet",
        judge_calls=calls_with_prompts,
        judge_fn=_judge_fn,
    )
    return df


# ---------------------------------------------------------------------------
# Pipeline 2: Cheap-judge sweep (Haiku + GPT-4o-mini on same 500 pilot rows)
# ---------------------------------------------------------------------------

def rejudge_cheap_sweep(pilot_df: pd.DataFrame) -> pd.DataFrame:
    """Re-judge defense_b_judge_cost_comparison.csv with Haiku and GPT-4o-mini v1.21."""
    print("\n=== Pipeline 2: Cheap-judge sweep (Haiku + GPT-4o-mini v1.21) ===")
    df = pd.read_csv(RESULTS / "defense_b_judge_cost_comparison.csv")

    # Get agent responses from pilot_df (which has agent_response column)
    agent_resp_map = {}
    if "agent_response" in pilot_df.columns:
        agent_resp_map = dict(zip(pilot_df["prompt_idx"], pilot_df["agent_response"]))
    else:
        # Fall back to agent cache
        agent_recs = _load_cache_by_key(CACHE / "defense_b_agent_pilot.jsonl", "prompt_idx")
        agent_resp_map = {k: v.get("response", "") for k, v in agent_recs.items()}

    haiku = HaikuJudge()
    gpt4mini = GPT4oJudge(model="gpt-4o-mini")

    def _build_calls(df_inner):
        calls = []
        for _, row in df_inner.iterrows():
            pid = row["prompt_idx"]
            user_prompt = row.get("prompt", "")
            agent_resp = agent_resp_map.get(pid, "")
            dataset = str(row.get("dataset", "deepset")).lower() if "dataset" in row else "deepset"
            calls.append((pid, user_prompt, agent_resp, dataset, None))
        return calls

    calls = _build_calls(df)

    # Haiku
    df = _add_v121_cols(
        df,
        CACHE / "defense_b_judge_pilot_haiku45_v121.jsonl",
        id_col="prompt_idx",
        prefix="haiku45",
        judge_calls=calls,
        judge_fn=lambda up, ar, ds, oi: haiku.judge_v121(up, ar, dataset=ds, operator_intent=oi),
    )

    # GPT-4o-mini
    df = _add_v121_cols(
        df,
        CACHE / "defense_b_judge_pilot_gpt4o_mini_v121.jsonl",
        id_col="prompt_idx",
        prefix="gpt4mini",
        judge_calls=calls,
        judge_fn=lambda up, ar, ds, oi: gpt4mini.judge_v121(up, ar, dataset=ds, operator_intent=oi),
    )

    return df


# ---------------------------------------------------------------------------
# Pipeline 3: BIPIA 800-row email-QA (Sonnet primary)
# ---------------------------------------------------------------------------

def rejudge_bipia() -> pd.DataFrame:
    """Re-judge bipia_email_qa_results.csv with Sonnet v1.21."""
    print("\n=== Pipeline 3: BIPIA email-QA (Sonnet v1.21) ===")
    df = pd.read_csv(RESULTS / "bipia_email_qa_results.csv")

    # Agent responses are in bipia_email_agent.jsonl
    agent_recs = _load_cache_by_key(CACHE / "bipia_email_agent.jsonl", "row_id")

    # User queries are in bipia_email_judge.jsonl (the original judge cache stores
    # the row_id and judge output but not the user_query). We need to load the
    # BIPIA data itself to get user queries, or use what's in existing judge cache.
    # The judge cache doesn't store user_query. Load from the BIPIA data loader.
    try:
        from src.bipia.email_qa import load_bipia_email_qa
        bipia_rows = {r.row_id: r for r in load_bipia_email_qa()}
        user_query_map = {rid: r.user_query for rid, r in bipia_rows.items()}
        print(f"  Loaded {len(user_query_map)} BIPIA rows from loader")
    except Exception as e:
        print(f"  WARNING: could not load BIPIA rows via loader ({e}); user_query will be empty")
        user_query_map = {}

    judge = ClaudeJudge()

    calls = []
    for _, row in df.iterrows():
        rid = row["row_id"]
        user_query = user_query_map.get(rid, "")
        agent_resp = agent_recs.get(rid, {}).get("response", "")
        calls.append((rid, user_query, agent_resp, "bipia", None))

    df = _add_v121_cols(
        df,
        CACHE / "bipia_email_judge_v121.jsonl",
        id_col="row_id",
        prefix="sonnet",
        judge_calls=calls,
        judge_fn=lambda up, ar, ds, oi: judge.judge_v121(up, ar, dataset=ds, operator_intent=oi),
    )
    return df


# ---------------------------------------------------------------------------
# Pipeline 4: GPT-4o sensitivity (8 deepset sneak-preview rows)
# ---------------------------------------------------------------------------

def rejudge_sensitivity() -> pd.DataFrame:
    """Re-judge defense_b_judge_sensitivity_deepset.csv with GPT-4o v1.21."""
    print("\n=== Pipeline 4: GPT-4o sensitivity (8 rows, v1.21) ===")
    df = pd.read_csv(RESULTS / "defense_b_judge_sensitivity_deepset.csv")

    # Agent responses: try pilot CSV first, then agent cache
    pilot_csv = RESULTS / "defense_b_pilot.csv"
    agent_resp_map = {}
    if pilot_csv.exists():
        pilot_df = pd.read_csv(pilot_csv)
        if "agent_response" in pilot_df.columns:
            agent_resp_map = dict(zip(pilot_df["prompt_idx"], pilot_df["agent_response"]))

    if not agent_resp_map:
        agent_recs = _load_cache_by_key(CACHE / "defense_b_agent_pilot.jsonl", "prompt_idx")
        agent_resp_map = {k: v.get("response", "") for k, v in agent_recs.items()}

    # User prompts from cost comparison CSV
    cost_csv = RESULTS / "defense_b_judge_cost_comparison.csv"
    prompt_map = {}
    if cost_csv.exists():
        cost_df = pd.read_csv(cost_csv)
        prompt_map = dict(zip(cost_df["prompt_idx"], cost_df["prompt"]))

    gpt4o = GPT4oJudge(model="gpt-4o")

    calls = []
    for _, row in df.iterrows():
        pid = row["prompt_idx"]
        user_prompt = prompt_map.get(pid, "")
        agent_resp = agent_resp_map.get(pid, "")
        calls.append((pid, user_prompt, agent_resp, "deepset", None))

    df = _add_v121_cols(
        df,
        CACHE / "defense_b_judge_sensitivity_gpt4o_v121.jsonl",
        id_col="prompt_idx",
        prefix="gpt4o",
        judge_calls=calls,
        judge_fn=lambda up, ar, ds, oi: gpt4o.judge_v121(up, ar, dataset=ds, operator_intent=oi),
    )
    return df


# ---------------------------------------------------------------------------
# Verdict-shift summary
# ---------------------------------------------------------------------------

def _verdict_shift(df: pd.DataFrame, old_col: str, new_col: str, label: str) -> None:
    """Print verdict-shift counts between old (boolean) and new (CLEAN/HIJACKED/AMBIGUOUS) cols."""
    print(f"\n--- Verdict shift: {label} ---")
    # Normalise old column to CLEAN/HIJACKED
    def _norm_old(v):
        if v is True or v == 1 or str(v).strip().lower() in ("true", "1", "1.0"):
            return "HIJACKED"
        if v is False or v == 0 or str(v).strip().lower() in ("false", "0", "0.0"):
            return "CLEAN"
        return "UNKNOWN"

    old_norm = df[old_col].map(_norm_old)
    new_norm = df[new_col].fillna("UNKNOWN")

    total = len(df)
    same = (old_norm == new_norm).sum()
    clean_to_hij = ((old_norm == "CLEAN") & (new_norm == "HIJACKED")).sum()
    hij_to_clean = ((old_norm == "HIJACKED") & (new_norm == "CLEAN")).sum()
    to_ambig = (new_norm == "AMBIGUOUS").sum()
    print(f"  Total rows       : {total}")
    print(f"  Unchanged        : {same}")
    print(f"  CLEAN -> HIJACKED: {clean_to_hij}")
    print(f"  HIJACKED -> CLEAN: {hij_to_clean}")
    print(f"  -> AMBIGUOUS     : {to_ambig}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # Backup first
    backup_dir = _REPO_ROOT / "_local" / "baseline_v1.8_judge"
    backup_dir.mkdir(parents=True, exist_ok=True)
    import shutil
    for fname in [
        "defense_b_pilot.csv",
        "bipia_email_qa_results.csv",
        "defense_b_judge_cost_comparison.csv",
        "defense_b_judge_sensitivity_deepset.csv",
    ]:
        src = RESULTS / fname
        dst = backup_dir / fname
        if src.exists() and not dst.exists():
            shutil.copy2(src, dst)
            print(f"Backed up: {dst}")
        elif dst.exists():
            print(f"Backup already exists: {dst}")

    # Pipeline 1: pilot
    pilot_df = rejudge_pilot()
    pilot_df.to_csv(RESULTS / "defense_b_pilot.csv", index=False)
    print(f"Saved defense_b_pilot.csv ({len(pilot_df)} rows)")
    _verdict_shift(pilot_df, "judge_hijacked", "sonnet_verdict_v121", "Pilot (Sonnet v1.8 -> v1.21)")

    # Pipeline 2: cheap sweep
    sweep_df = rejudge_cheap_sweep(pilot_df)
    sweep_df.to_csv(RESULTS / "defense_b_judge_cost_comparison.csv", index=False)
    print(f"Saved defense_b_judge_cost_comparison.csv ({len(sweep_df)} rows)")
    # Note: sweep CSV has haiku45 and gpt4mini v1.21 columns, not sonnet v1.21
    _verdict_shift(sweep_df, "haiku45_hijacked", "haiku45_verdict_v121", "Sweep Haiku v1.8 -> v1.21")
    _verdict_shift(sweep_df, "gpt4mini_hijacked", "gpt4mini_verdict_v121", "Sweep GPT-4o-mini v1.8 -> v1.21")

    # Pipeline 3: BIPIA
    bipia_df = rejudge_bipia()
    bipia_df.to_csv(RESULTS / "bipia_email_qa_results.csv", index=False)
    print(f"Saved bipia_email_qa_results.csv ({len(bipia_df)} rows)")
    _verdict_shift(bipia_df, "judge_hijacked", "sonnet_verdict_v121", "BIPIA Sonnet v1.8 -> v1.21")

    # Pipeline 4: sensitivity
    sens_df = rejudge_sensitivity()
    sens_df.to_csv(RESULTS / "defense_b_judge_sensitivity_deepset.csv", index=False)
    print(f"Saved defense_b_judge_sensitivity_deepset.csv ({len(sens_df)} rows)")
    _verdict_shift(sens_df, "gpt4o_hijacked", "gpt4o_verdict_v121", "Sensitivity GPT-4o v1.8 -> v1.21")

    print("\nDone.")


if __name__ == "__main__":
    main()
