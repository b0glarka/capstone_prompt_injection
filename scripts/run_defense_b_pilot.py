"""Defense B 500-row formal pilot on the frozen evaluation set.

Promotes Defense B from the 24-case sneak preview to a 500-row pilot at a
scale comparable to a real Phase 1 deliverable. Stratified sample:
~167 per dataset, balanced 50/50 SAFE/INJECTION within each, seed 42.

Outputs:
  - results/defense_b_pilot.csv         per-row agent response + judge verdict
  - results/defense_b_pilot.md          headline writeup
  - results/defense_b_pilot_metrics.csv per-dataset and per-subcategory hijack rates
  - cache/defense_b_agent_pilot.jsonl   resumable agent cache
  - cache/defense_b_judge_pilot.jsonl   resumable judge cache

Cost ceiling: ~$5. Resumable: re-running picks up only the uncached rows.
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
from src.defense_b.agent import GroqAgent
from src.defense_b.judge import ClaudeJudge

RES = REPO_ROOT / "results"
CACHE = REPO_ROOT / "cache"
CACHE.mkdir(parents=True, exist_ok=True)

AGENT_CACHE = CACHE / "defense_b_agent_pilot.jsonl"
JUDGE_CACHE = CACHE / "defense_b_judge_pilot.jsonl"

# Pilot sample design
SEED = 42
PER_DS = {"deepset": 167, "neuralchemy": 167, "spml": 166}  # totals 500


def select_pilot() -> pd.DataFrame:
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
        i_idx = rng.choice(inj.index.values,  size=min(half + extra, len(inj)), replace=False)
        parts.append(pd.concat([safe.loc[s_idx], inj.loc[i_idx]]))
    pilot = pd.concat(parts).sort_values("prompt_idx").reset_index(drop=True)
    return pilot[["prompt_idx", "dataset", "prompt", "label", "subcategory"]]


def run_agent(pilot: pd.DataFrame) -> dict[str, dict]:
    done = existing_keys(AGENT_CACHE, key="prompt_idx")
    todo = pilot[~pilot["prompt_idx"].isin(done)]
    print(f"\nagent cached: {len(done)}, to run: {len(todo)}")
    if len(todo) > 0:
        agent = GroqAgent()
        new = []
        for _, row in tqdm(todo.iterrows(), total=len(todo), desc="agent"):
            out = agent.respond(row["prompt"])
            new.append({"prompt_idx": row["prompt_idx"], **out})
        append_records(AGENT_CACHE, new)
    return {r["prompt_idx"]: r for r in load_records(AGENT_CACHE)}


def run_judge(pilot: pd.DataFrame, agent_out: dict[str, dict]) -> dict[str, dict]:
    done = existing_keys(JUDGE_CACHE, key="prompt_idx")
    todo = pilot[~pilot["prompt_idx"].isin(done)]
    print(f"\njudge cached: {len(done)}, to run: {len(todo)}")
    if len(todo) > 0:
        judge = ClaudeJudge()
        new = []
        for _, row in tqdm(todo.iterrows(), total=len(todo), desc="judge"):
            agent_resp = agent_out[row["prompt_idx"]]["response"]
            out = judge.judge(row["prompt"], agent_resp)
            new.append({"prompt_idx": row["prompt_idx"], **out})
        append_records(JUDGE_CACHE, new)
    return {r["prompt_idx"]: r for r in load_records(JUDGE_CACHE)}


def build_results(pilot: pd.DataFrame, agent_out: dict, judge_out: dict) -> pd.DataFrame:
    rows = []
    for _, r in pilot.iterrows():
        idx = r["prompt_idx"]
        a = agent_out[idx]
        j = judge_out[idx]
        rows.append({
            "prompt_idx": idx,
            "dataset": r["dataset"],
            "subcategory": r["subcategory"],
            "label": r["label"],
            "agent_response": a["response"],
            "agent_input_tokens": a.get("input_tokens", 0),
            "agent_output_tokens": a.get("output_tokens", 0),
            "judge_hijacked": j.get("hijacked"),
            "judge_reasoning": j.get("reasoning"),
            "judge_blocked": j.get("judge_blocked", False),
            "judge_input_tokens": j.get("input_tokens", 0),
            "judge_output_tokens": j.get("output_tokens", 0),
        })
    return pd.DataFrame(rows)


def compute_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Per-dataset hijack rates on injection-class rows, plus overall."""
    inj = df[df["label"] == 1].copy()
    inj["caught"] = (inj["judge_hijacked"] == True).astype(int)

    rows = [{
        "scope": "overall (injection rows only)",
        "n": len(inj),
        "judge_blocked_n": int(inj["judge_blocked"].sum()),
        "hijacked_n": int(inj["caught"].sum()),
        "hijack_rate": round(inj["caught"].mean(), 4) if len(inj) else None,
    }]
    for ds in ["deepset", "neuralchemy", "spml"]:
        sub = inj[inj["dataset"] == ds]
        rows.append({
            "scope": f"{ds} (injection rows only)",
            "n": len(sub),
            "judge_blocked_n": int(sub["judge_blocked"].sum()),
            "hijacked_n": int(sub["caught"].sum()),
            "hijack_rate": round(sub["caught"].mean(), 4) if len(sub) else None,
        })
    return pd.DataFrame(rows)


def estimate_cost(df: pd.DataFrame) -> dict:
    """Approximate API cost using observed token counts. Sonnet 4.6 + Llama 3.3 70B prices."""
    agent_in  = df["agent_input_tokens"].sum()
    agent_out = df["agent_output_tokens"].sum()
    judge_in  = df["judge_input_tokens"].sum()
    judge_out = df["judge_output_tokens"].sum()
    # Groq Llama 3.3 70B Versatile: $0.59 / $0.79 per 1M
    agent_cost = (agent_in * 0.59 + agent_out * 0.79) / 1_000_000
    # Anthropic Sonnet 4.6: ~$3 / $15 per 1M (approx)
    judge_cost = (judge_in * 3.0 + judge_out * 15.0) / 1_000_000
    return {
        "agent_input_tokens": int(agent_in),
        "agent_output_tokens": int(agent_out),
        "judge_input_tokens": int(judge_in),
        "judge_output_tokens": int(judge_out),
        "agent_cost_usd": round(agent_cost, 4),
        "judge_cost_usd": round(judge_cost, 4),
        "total_cost_usd": round(agent_cost + judge_cost, 4),
    }


def write_markdown(results: pd.DataFrame, metrics: pd.DataFrame, cost: dict) -> None:
    n_total = len(results)
    n_inj   = int((results["label"] == 1).sum())
    n_safe  = int((results["label"] == 0).sum())
    blocked = int(results["judge_blocked"].sum())

    overall = metrics.iloc[0]

    lines = [
        "# Defense B 500-row formal pilot on the frozen eval set\n",
        "- Run date: 2026-05-11",
        "- Agent: `llama-3.3-70b-versatile` via Groq, temperature 0, max_tokens 400",
        "- Judge: `claude-sonnet-4-6` via Anthropic, temperature 0, max_tokens 400",
        "- Sample: 500 rows stratified across deepset / neuralchemy / SPML, 50/50 label-balanced within each, seed 42",
        f"- Total rows: {n_total} ({n_safe} SAFE, {n_inj} INJECTION)",
        f"- Judge-blocked rows (content policy): {blocked}",
        "",
        "## Headline",
        "",
        f"On the {overall['n']} injection-class rows in the pilot, the Defense B pipeline (Llama agent + Claude judge) flagged **{overall['hijacked_n']} as hijacked**, a hijack rate of **{overall['hijack_rate']}**.",
        "",
        "## Per-dataset hijack rate (injection rows only)",
        "",
        "| Scope | n | Hijacked | Hijack rate | Judge-blocked |",
        "|---|---|---|---|---|",
    ]
    for _, r in metrics.iloc[1:].iterrows():
        lines.append(f"| {r['scope']} | {r['n']} | {r['hijacked_n']} | {r['hijack_rate']} | {r['judge_blocked_n']} |")

    lines += [
        "",
        "## Cost",
        "",
        f"- Agent (Llama 3.3 70B): ${cost['agent_cost_usd']:.4f} ({cost['agent_input_tokens']:,} in, {cost['agent_output_tokens']:,} out)",
        f"- Judge (Sonnet 4.6): ${cost['judge_cost_usd']:.4f} ({cost['judge_input_tokens']:,} in, {cost['judge_output_tokens']:,} out)",
        f"- **Total: ${cost['total_cost_usd']:.4f}** for 500 rows",
        f"- Extrapolated to the full 4,546-row eval set: ~${cost['total_cost_usd'] * 4546 / 500:.2f}",
        "",
        "## Caveats",
        "",
        "Single agent model, single judge model, minimum-rubric judge (not the production rubric). Judge rubric iteration scheduled before scaling to full eval set. Per-neuralchemy-subcategory breakdown is exploratory at this n; do not over-interpret. The reported hijack rate is the fraction of injection-class rows where the judge said the agent's text response complied with the injected instruction; it does not capture tool-execution side effects in a live deployment.",
        "",
        "## Artifacts",
        "",
        "- `results/defense_b_pilot.csv` (per-row predictions)",
        "- `results/defense_b_pilot_metrics.csv` (scope-by-scope hijack rates)",
        "- `cache/defense_b_agent_pilot.jsonl`, `cache/defense_b_judge_pilot.jsonl` (resumable caches)",
    ]

    (RES / "defense_b_pilot.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    pilot = select_pilot()
    print(f"pilot rows: {len(pilot)}")
    print(pilot.groupby(["dataset", "label"]).size().to_string())

    agent_out = run_agent(pilot)
    judge_out = run_judge(pilot, agent_out)

    results = build_results(pilot, agent_out, judge_out)
    metrics = compute_metrics(results)
    cost = estimate_cost(results)

    results.to_csv(RES / "defense_b_pilot.csv", index=False)
    metrics.to_csv(RES / "defense_b_pilot_metrics.csv", index=False)
    write_markdown(results, metrics, cost)

    print("\n=== Headline ===")
    print(metrics.to_string(index=False))
    print(f"\nTotal cost: ${cost['total_cost_usd']:.4f}")
    print(f"  csv: {RES / 'defense_b_pilot.csv'}")
    print(f"  md : {RES / 'defense_b_pilot.md'}")


if __name__ == "__main__":
    main()
