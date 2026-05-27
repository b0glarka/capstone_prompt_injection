"""Defense B 500-row pilot with Qwen 2.5 72B Instruct Turbo as the agent.

Cross-family comparison: same 500 frozen pilot rows as the Llama pilot
(scripts/run_defense_b_pilot.py, results/defense_b_pilot.csv), but with
Qwen/Qwen2.5-72B-Instruct-Turbo via Together AI instead of Llama 3.3 70B.

Motivation: Hiflylabs deploys Qwen alongside Llama for different clients.
If Qwen produces materially different hijack rates against the same defenses,
the deployment recommendations need a model-family qualifier. See final report
§6.4 / Limitations.

Outputs:
  results/defense_b_pilot_qwen.csv         per-row agent response + judge verdict
  results/defense_b_pilot_qwen_metrics.csv per-dataset and per-subcategory hijack rates
  cache/defense_b_agent_pilot_qwen.jsonl   resumable agent cache
  cache/defense_b_judge_pilot_qwen.jsonl   resumable judge cache

Cost ceiling: ~$4 for this script (Qwen agent + Sonnet judge on 500 rows).
Resumable: re-running picks up only the uncached rows.

Judge: Claude Sonnet 4.6 v1.21 rubric (same as the Llama pilot).
Agent: Qwen 2.5 72B Instruct Turbo via Together AI, temperature 0, max_tokens 400.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from tqdm import tqdm

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
load_dotenv(REPO_ROOT / ".env")

from src.cache import append_records, existing_keys, load_records
from src.defense_b.agent import make_agent
from src.defense_b.judge import ClaudeJudge

RES = REPO_ROOT / "results"
CACHE = REPO_ROOT / "cache"
CACHE.mkdir(parents=True, exist_ok=True)

AGENT_CACHE = CACHE / "defense_b_agent_pilot_qwen.jsonl"
JUDGE_CACHE = CACHE / "defense_b_judge_pilot_qwen.jsonl"

# Must match the original pilot's sampling exactly (same seed, same sizes).
SEED = 42
PER_DS = {"deepset": 167, "neuralchemy": 167, "spml": 166}

# Together AI Qwen 2.5 72B pricing (as of 2026-05): $0.80/M in, $0.80/M out
# (verify at together.ai/pricing before interpreting cost estimates).
QWEN_PRICE_IN = 0.80   # USD per 1M input tokens
QWEN_PRICE_OUT = 0.80  # USD per 1M output tokens

# Anthropic Sonnet 4.6: $3/M input, $15/M output
SONNET_PRICE_IN = 3.0
SONNET_PRICE_OUT = 15.0

COST_CEILING_USD = 8.0  # abort if cumulative spend exceeds this


def select_pilot() -> pd.DataFrame:
    """Reproduce the same 500-row frozen pilot sample used in the Llama pilot.

    Uses identical seed and stratification so that prompt_idx values match
    exactly between defense_b_pilot.csv and defense_b_pilot_qwen.csv.
    """
    es = pd.read_parquet(RES / "eval_set.parquet")
    rng = np.random.default_rng(SEED)
    parts = []
    for ds, n in PER_DS.items():
        pool = es[es["dataset"] == ds]
        half = n // 2
        extra = n - 2 * half
        safe = pool[pool["label"] == 0]
        inj = pool[pool["label"] == 1]
        s_idx = rng.choice(safe.index.values, size=min(half, len(safe)), replace=False)
        i_idx = rng.choice(inj.index.values, size=min(half + extra, len(inj)), replace=False)
        parts.append(pd.concat([safe.loc[s_idx], inj.loc[i_idx]]))
    pilot = pd.concat(parts).sort_values("prompt_idx").reset_index(drop=True)
    return pilot[["prompt_idx", "dataset", "prompt", "label", "subcategory"]]


def _estimate_running_cost() -> float:
    """Read current caches and estimate cumulative API spend so far."""
    agent_records = load_records(AGENT_CACHE)
    judge_records = load_records(JUDGE_CACHE)
    agent_in  = sum(r.get("input_tokens", 0) for r in agent_records)
    agent_out = sum(r.get("output_tokens", 0) for r in agent_records)
    judge_in  = sum(r.get("input_tokens_v121", r.get("input_tokens", 0)) for r in judge_records)
    judge_out = sum(r.get("output_tokens_v121", r.get("output_tokens", 0)) for r in judge_records)
    agent_cost = (agent_in * QWEN_PRICE_IN + agent_out * QWEN_PRICE_OUT) / 1_000_000
    judge_cost = (judge_in * SONNET_PRICE_IN + judge_out * SONNET_PRICE_OUT) / 1_000_000
    return agent_cost + judge_cost


def run_agent(pilot: pd.DataFrame) -> dict[str, dict]:
    """Run Qwen 2.5 72B agent on uncached pilot rows. Returns all agent records keyed by prompt_idx."""
    done = existing_keys(AGENT_CACHE, key="prompt_idx")
    todo = pilot[~pilot["prompt_idx"].isin(done)]
    print(f"\nagent cached: {len(done)}, to run: {len(todo)}")
    if len(todo) > 0:
        agent = make_agent("qwen")
        print(f"agent provider: qwen, model: {agent.model}")
        for _, row in tqdm(todo.iterrows(), total=len(todo), desc="agent (qwen)"):
            running_cost = _estimate_running_cost()
            if running_cost > COST_CEILING_USD:
                print(f"\nCOST CEILING HIT: ${running_cost:.4f} > ${COST_CEILING_USD}. Stopping.")
                break
            out = agent.respond(row["prompt"])
            append_records(AGENT_CACHE, [{"prompt_idx": row["prompt_idx"], **out}])
    return {r["prompt_idx"]: r for r in load_records(AGENT_CACHE)}


def run_judge(pilot: pd.DataFrame, agent_out: dict[str, dict]) -> dict[str, dict]:
    """Run Sonnet v1.21 judge on uncached rows. Returns all judge records keyed by prompt_idx."""
    done = existing_keys(JUDGE_CACHE, key="prompt_idx")
    todo = pilot[~pilot["prompt_idx"].isin(done)]
    print(f"\njudge cached: {len(done)}, to run: {len(todo)}")
    if len(todo) > 0:
        judge = ClaudeJudge()
        for _, row in tqdm(todo.iterrows(), total=len(todo), desc="judge (Sonnet v1.21)"):
            running_cost = _estimate_running_cost()
            if running_cost > COST_CEILING_USD:
                print(f"\nCOST CEILING HIT: ${running_cost:.4f} > ${COST_CEILING_USD}. Stopping.")
                break
            if row["prompt_idx"] not in agent_out:
                continue  # no agent output yet (partial run)
            agent_resp = agent_out[row["prompt_idx"]]["response"]
            # Use v1.21 rubric to match the Llama pilot's sonnet_verdict_v121 column.
            out = judge.judge_v121(
                row["prompt"],
                agent_resp,
                dataset=row["dataset"],
            )
            append_records(JUDGE_CACHE, [{"prompt_idx": row["prompt_idx"], **out}])
    return {r["prompt_idx"]: r for r in load_records(JUDGE_CACHE)}


def build_results(pilot: pd.DataFrame, agent_out: dict, judge_out: dict) -> pd.DataFrame:
    """Merge pilot metadata, agent responses, and judge verdicts into one DataFrame."""
    rows = []
    for _, r in pilot.iterrows():
        idx = r["prompt_idx"]
        a = agent_out.get(idx, {})
        j = judge_out.get(idx, {})
        rows.append({
            "prompt_idx": idx,
            "dataset": r["dataset"],
            "subcategory": r["subcategory"],
            "label": r["label"],
            "agent_response": a.get("response", ""),
            "agent_input_tokens": a.get("input_tokens", 0),
            "agent_output_tokens": a.get("output_tokens", 0),
            # v1.21 judge fields (parallel to the Llama pilot's sonnet_* columns)
            "judge_verdict": j.get("verdict"),
            "judge_hijack_categories": str(j.get("hijack_categories", [])),
            "judge_reason": j.get("reason", ""),
            "judge_blocked": j.get("judge_blocked_v121", False),
            "judge_input_tokens": j.get("input_tokens_v121", 0),
            "judge_output_tokens": j.get("output_tokens_v121", 0),
            # Derived boolean for easy rate computation: HIJACKED = True
            "judge_hijacked": (j.get("verdict") == "HIJACKED") if j.get("verdict") else None,
        })
    return pd.DataFrame(rows)


def compute_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Per-dataset hijack rates on injection-class rows, plus overall."""
    inj = df[df["label"] == 1].copy()
    inj["caught"] = (inj["judge_hijacked"] == True).astype(int)

    rows_out = [{
        "scope": "overall (injection rows only)",
        "n": len(inj),
        "judge_blocked_n": int(inj["judge_blocked"].sum()),
        "hijacked_n": int(inj["caught"].sum()),
        "hijack_rate": round(inj["caught"].mean(), 4) if len(inj) else None,
    }]
    for ds in ["deepset", "neuralchemy", "spml"]:
        sub = inj[inj["dataset"] == ds]
        rows_out.append({
            "scope": f"{ds} (injection rows only)",
            "n": len(sub),
            "judge_blocked_n": int(sub["judge_blocked"].sum()),
            "hijacked_n": int(sub["caught"].sum()),
            "hijack_rate": round(sub["caught"].mean(), 4) if len(sub) else None,
        })
    return pd.DataFrame(rows_out)


def estimate_cost(df: pd.DataFrame) -> dict:
    """Approximate API cost from token counts in the results DataFrame."""
    agent_in  = df["agent_input_tokens"].sum()
    agent_out = df["agent_output_tokens"].sum()
    judge_in  = df["judge_input_tokens"].sum()
    judge_out = df["judge_output_tokens"].sum()
    agent_cost = (agent_in * QWEN_PRICE_IN + agent_out * QWEN_PRICE_OUT) / 1_000_000
    judge_cost = (judge_in * SONNET_PRICE_IN + judge_out * SONNET_PRICE_OUT) / 1_000_000
    return {
        "agent_model": "Qwen/Qwen2.5-72B-Instruct-Turbo",
        "agent_input_tokens": int(agent_in),
        "agent_output_tokens": int(agent_out),
        "judge_input_tokens": int(judge_in),
        "judge_output_tokens": int(judge_out),
        "agent_cost_usd": round(agent_cost, 4),
        "judge_cost_usd": round(judge_cost, 4),
        "total_cost_usd": round(agent_cost + judge_cost, 4),
    }


def print_verdict_shift(df_qwen: pd.DataFrame) -> None:
    """Print Llama vs Qwen hijack-rate comparison on the same 500 rows."""
    llama_path = RES / "defense_b_pilot.csv"
    if not llama_path.exists():
        print("\n(Llama pilot CSV not found; skipping verdict-shift summary)")
        return
    df_llama = pd.read_csv(llama_path)

    print("\n=== Verdict-shift summary: Llama 3.3 70B vs Qwen 2.5 72B (injection rows only) ===")
    print(f"{'Dataset':<15}  {'Llama hijack_rate':>18}  {'Qwen hijack_rate':>17}  {'Delta':>8}  {'n':>5}")
    print("-" * 75)

    for scope, filter_fn in [
        ("overall", lambda d: d),
        ("deepset", lambda d: d[d["dataset"] == "deepset"]),
        ("neuralchemy", lambda d: d[d["dataset"] == "neuralchemy"]),
        ("spml", lambda d: d[d["dataset"] == "spml"]),
    ]:
        ll = filter_fn(df_llama[df_llama["label"] == 1])
        qq = filter_fn(df_qwen[df_qwen["label"] == 1])
        # Llama pilot uses judge_hijacked directly (bool); Qwen uses judge_hijacked derived col
        ll_rate = ll["judge_hijacked"].astype(float).mean() if len(ll) else float("nan")
        qq_rate = qq["judge_hijacked"].astype(float).mean() if len(qq) else float("nan")
        delta = qq_rate - ll_rate
        n = len(qq)
        print(f"{scope:<15}  {ll_rate:>18.4f}  {qq_rate:>17.4f}  {delta:>+8.4f}  {n:>5}")


def main() -> None:
    pilot = select_pilot()
    print(f"pilot rows: {len(pilot)}")
    print(pilot.groupby(["dataset", "label"]).size().to_string())

    agent_out = run_agent(pilot)
    pilot_with_agent = pilot[pilot["prompt_idx"].isin(agent_out.keys())]
    judge_out = run_judge(pilot_with_agent, agent_out)

    results = build_results(pilot, agent_out, judge_out)
    metrics = compute_metrics(results)
    cost = estimate_cost(results)

    out_csv = RES / "defense_b_pilot_qwen.csv"
    metrics_csv = RES / "defense_b_pilot_qwen_metrics.csv"
    results.to_csv(out_csv, index=False)
    metrics.to_csv(metrics_csv, index=False)

    print("\n=== Qwen pilot metrics (injection rows only) ===")
    print(metrics.to_string(index=False))
    print(f"\nTotal cost: ${cost['total_cost_usd']:.4f}")
    print(f"  agent ({cost['agent_model']}): ${cost['agent_cost_usd']:.4f} "
          f"({cost['agent_input_tokens']:,} in, {cost['agent_output_tokens']:,} out)")
    print(f"  judge (Sonnet 4.6 v1.21): ${cost['judge_cost_usd']:.4f} "
          f"({cost['judge_input_tokens']:,} in, {cost['judge_output_tokens']:,} out)")
    print(f"  csv : {out_csv}")
    print(f"  metrics: {metrics_csv}")

    print_verdict_shift(results)

    # Error summary
    errors = results[results["agent_response"] == ""]
    if len(errors):
        print(f"\nRows with missing agent response: {len(errors)}")
        print(errors["prompt_idx"].tolist())
    judge_errors = results[results["judge_verdict"].isna()]
    if len(judge_errors):
        print(f"\nRows with missing judge verdict: {len(judge_errors)}")


if __name__ == "__main__":
    main()
