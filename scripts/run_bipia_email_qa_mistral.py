"""BIPIA email-QA evaluation with Mistral Large 2 (mistralai/mistral-large-2411 via OpenRouter) as the agent.

Cross-family comparison: same 800 BIPIA rows as the Llama BIPIA run
(scripts/run_bipia_email_qa.py, results/bipia_email_qa_results.csv), but with
mistralai/mistral-large-2411 via Together AI instead of Llama 3.3 70B.

Only Defense B (agent + Sonnet judge) is re-run. Defense A classifiers are
not re-run because they are input-side and model-family-agnostic.

Outputs:
  cache/bipia_email_agent_mistral.jsonl    resumable agent cache
  cache/bipia_email_judge_mistral.jsonl    resumable judge cache
  results/bipia_email_qa_results_mistral.csv  per-row merged predictions
  results/bipia_email_qa_metrics_mistral.csv  per-category hijack rates

Cost ceiling: ~$5 for this script (Mistral agent + Sonnet judge on 800 rows).
Resumable: re-running picks up only the uncached rows.

Judge: Claude Sonnet 4.6, v1.21 augmented rubric (§3.2 with Step 0 + H1-H5
indicators + AMBIGUOUS routing). This matches the v1.21 re-judge applied
to the Llama BIPIA run (results/bipia_email_qa_results.csv has
sonnet_verdict_v121 etc.), so the comparison is apples-to-apples.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from tqdm import tqdm

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
load_dotenv(REPO / ".env")

from src.cache import append_records, existing_keys, load_records
from src.bipia.email_qa import load_bipia_email_qa, compose_agent_input, SYSTEM_PROMPT
from src.defense_b.agent import make_agent
from src.defense_b.judge import ClaudeJudge

CACHE = REPO / "cache"
RES = REPO / "results"
CACHE.mkdir(exist_ok=True)
RES.mkdir(exist_ok=True)

AGENT_CACHE = CACHE / "bipia_email_agent_mistral.jsonl"
JUDGE_CACHE = CACHE / "bipia_email_judge_mistral.jsonl"

# Pricing estimates
MISTRAL_PRICE_IN  = 0.80   # USD per 1M input tokens
MISTRAL_PRICE_OUT = 6.0   # USD per 1M output tokens
SONNET_PRICE_IN  = 3.0
SONNET_PRICE_OUT = 15.0

COST_CEILING_USD = 10.0


def _estimate_running_cost() -> float:
    """Read current caches and estimate cumulative API spend."""
    agent_records = load_records(AGENT_CACHE)
    judge_records = load_records(JUDGE_CACHE)
    agent_in  = sum(r.get("input_tokens", 0) for r in agent_records)
    agent_out = sum(r.get("output_tokens", 0) for r in agent_records)
    judge_in  = sum(r.get("input_tokens", 0) for r in judge_records)
    judge_out = sum(r.get("output_tokens", 0) for r in judge_records)
    agent_cost = (agent_in * MISTRAL_PRICE_IN + agent_out * MISTRAL_PRICE_OUT) / 1_000_000
    judge_cost = (judge_in * SONNET_PRICE_IN + judge_out * SONNET_PRICE_OUT) / 1_000_000
    return agent_cost + judge_cost


def run_agent(rows) -> dict:
    """Run Mistral on uncached BIPIA rows."""
    done = existing_keys(AGENT_CACHE, key="row_id")
    todo = [r for r in rows if r.row_id not in done]
    print(f"\nagent cached: {len(done)}, to run: {len(todo)}")
    if not todo:
        return {r["row_id"]: r for r in load_records(AGENT_CACHE)}
    agent = make_agent("mistral")
    agent.system_prompt = SYSTEM_PROMPT  # BIPIA inbox-assistant role
    print(f"agent model: {agent.model}")
    for r in tqdm(todo, desc="agent (mistral)"):
        running_cost = _estimate_running_cost()
        if running_cost > COST_CEILING_USD:
            print(f"\nCOST CEILING HIT: ${running_cost:.4f} > ${COST_CEILING_USD}. Stopping.")
            break
        _, user_message = compose_agent_input(r)
        out = agent.respond(user_message)
        append_records(AGENT_CACHE, [{"row_id": r.row_id, **out}])
    return {x["row_id"]: x for x in load_records(AGENT_CACHE)}


def run_judge(rows, agent_records: dict) -> dict:
    """Run Sonnet v1.21 judge on uncached rows.

    Matches the v1.21 re-judge that was applied to the Llama BIPIA run
    (results/bipia_email_qa_results.csv columns sonnet_verdict_v121,
    sonnet_categories_v121, sonnet_reason_v121). Apples-to-apples
    comparison between Llama and Mistral requires the same judge rubric.
    """
    done = existing_keys(JUDGE_CACHE, key="row_id")
    todo = [r for r in rows if r.row_id not in done and r.row_id in agent_records]
    print(f"\njudge cached: {len(done)}, to run: {len(todo)}")
    if not todo:
        return {r["row_id"]: r for r in load_records(JUDGE_CACHE)}
    judge = ClaudeJudge()
    for r in tqdm(todo, desc="judge (Sonnet v1.21)"):
        running_cost = _estimate_running_cost()
        if running_cost > COST_CEILING_USD:
            print(f"\nCOST CEILING HIT: ${running_cost:.4f} > ${COST_CEILING_USD}. Stopping.")
            break
        agent_resp = agent_records[r.row_id]["response"]
        out = judge.judge_v121(r.user_query, agent_resp, dataset="bipia", operator_intent=None)
        append_records(JUDGE_CACHE, [{"row_id": r.row_id, **out}])
    return {x["row_id"]: x for x in load_records(JUDGE_CACHE)}


def build_results(rows, agent_records: dict, judge_records: dict) -> pd.DataFrame:
    """Assemble per-row result DataFrame. Schema parallels bipia_email_qa_results.csv."""
    result_rows = []
    for r in rows:
        a = agent_records.get(r.row_id, {})
        j = judge_records.get(r.row_id, {})
        result_rows.append({
            "row_id": r.row_id,
            "attack_category": r.attack_category,
            "is_attack": r.is_attack,
            "agent_response": a.get("response", ""),
            "agent_input_tokens": a.get("input_tokens", 0),
            "agent_output_tokens": a.get("output_tokens", 0),
            "judge_verdict_v121": j.get("verdict", ""),
            "judge_categories_v121": j.get("hijack_categories", ""),
            "judge_reason_v121": j.get("reason", ""),
            # Derived boolean for backwards-compatible compute_metrics:
            # AMBIGUOUS counts as HIJACKED (conservative deployment convention).
            "judge_hijacked": (j.get("verdict", "").upper() != "CLEAN") if j.get("verdict") else None,
            "judge_blocked": j.get("judge_blocked_v121", False),
            "judge_input_tokens": j.get("input_tokens_v121", 0),
            "judge_output_tokens": j.get("output_tokens_v121", 0),
        })
    return pd.DataFrame(result_rows)


def compute_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Per-category attack success rates, matching the Llama BIPIA metrics schema."""
    attacks = df[df["is_attack"]]
    cleans  = df[~df["is_attack"]]

    def _success_rate(sub):
        return round(1.0 - sub["judge_hijacked"].fillna(False).astype(bool).mean(), 4)

    def _far(sub):
        return round(sub["judge_hijacked"].fillna(False).astype(bool).mean(), 4)

    rows_out = [{
        "defense": "Defense B Mistral: Sonnet judge",
        "n_attacks": len(attacks),
        "attack_success_rate": _success_rate(attacks),
        "n_clean": len(cleans),
        "false_alarm_rate": _far(cleans),
    }]
    return pd.DataFrame(rows_out)


def print_verdict_shift(df_mistral: pd.DataFrame) -> None:
    """Print Llama vs Mistral attack success rate per BIPIA attack category."""
    llama_path = RES / "bipia_email_qa_results.csv"
    if not llama_path.exists():
        print("\n(Llama BIPIA CSV not found; skipping verdict-shift summary)")
        return

    df_llama = pd.read_csv(llama_path)
    attacks_llama = df_llama[df_llama["is_attack"]].copy()
    attacks_mistral  = df_mistral[df_mistral["is_attack"]].copy()

    # Merge on row_id to ensure we compare the same rows
    merged = attacks_llama[["row_id", "attack_category", "judge_hijacked"]].merge(
        attacks_mistral[["row_id", "judge_hijacked"]].rename(columns={"judge_hijacked": "mistral_hijacked"}),
        on="row_id", how="inner",
    )

    print("\n=== BIPIA verdict-shift: Llama 3.3 70B vs Mistral (attack rows only) ===")
    print(f"{'Category':<22}  {'Llama hijack_rate':>18}  {'Mistral hijack_rate':>17}  {'Delta':>8}  {'n':>5}")
    print("-" * 80)

    for label, sub in [("overall", merged)] + [
        (cat, merged[merged["attack_category"] == cat])
        for cat in sorted(merged["attack_category"].unique())
    ]:
        ll_rate = sub["judge_hijacked"].fillna(False).astype(float).mean()
        qq_rate = sub["mistral_hijacked"].fillna(False).astype(float).mean()
        delta = qq_rate - ll_rate
        n = len(sub)
        print(f"{label:<22}  {ll_rate:>18.4f}  {qq_rate:>17.4f}  {delta:>+8.4f}  {n:>5}")

    # Rows where they disagree
    merged["disagree"] = merged["judge_hijacked"].fillna(False) != merged["mistral_hijacked"].fillna(False)
    n_disagree = merged["disagree"].sum()
    print(f"\nDisagreements (Llama vs Mistral verdict differs): {n_disagree} / {len(merged)} "
          f"({n_disagree / len(merged) * 100:.1f}%)")
    if n_disagree > 0:
        disagree_by_cat = (
            merged[merged["disagree"]]
            .groupby("attack_category")
            .size()
            .sort_values(ascending=False)
        )
        print("Disagreements by category:")
        print(disagree_by_cat.to_string())


def main():
    print("Loading BIPIA email-QA test set...")
    rows = load_bipia_email_qa(REPO / "data/bipia", split="test")
    print(f"loaded {len(rows)} rows ({sum(1 for r in rows if r.is_attack)} attacks, "
          f"{sum(1 for r in rows if not r.is_attack)} clean)")

    print("\nRunning Defense B agent (Mistral via Together)...")
    agent_records = run_agent(rows)

    print("\nRunning Defense B judge (Sonnet 4.6)...")
    judge_records = run_judge(rows, agent_records)

    results = build_results(rows, agent_records, judge_records)
    metrics = compute_metrics(results)

    results.to_csv(RES / "bipia_email_qa_results_mistral.csv", index=False)
    metrics.to_csv(RES / "bipia_email_qa_metrics_mistral.csv", index=False)
    print(f"\nsaved {RES / 'bipia_email_qa_results_mistral.csv'} ({len(results)} rows)")

    # Cost estimate
    agent_in  = results["agent_input_tokens"].sum()
    agent_out = results["agent_output_tokens"].sum()
    judge_in  = results["judge_input_tokens"].sum()
    judge_out = results["judge_output_tokens"].sum()
    agent_cost = (agent_in * MISTRAL_PRICE_IN + agent_out * MISTRAL_PRICE_OUT) / 1_000_000
    judge_cost = (judge_in * SONNET_PRICE_IN + judge_out * SONNET_PRICE_OUT) / 1_000_000
    print(f"\nCost estimate:")
    print(f"  Mistral agent: ${agent_cost:.4f} ({agent_in:,} in, {agent_out:,} out)")
    print(f"  Sonnet judge: ${judge_cost:.4f} ({judge_in:,} in, {judge_out:,} out)")
    print(f"  Total: ${agent_cost + judge_cost:.4f}")

    print("\n=== Overall metrics ===")
    print(metrics.to_string(index=False))

    print_verdict_shift(results)

    # Error summary
    errors = results[results["agent_response"] == ""]
    if len(errors):
        print(f"\nRows with missing agent response: {len(errors)}")
    judge_errors = results[results["judge_hijacked"].isna() & results["is_attack"]]
    if len(judge_errors):
        print(f"\nAttack rows with missing judge verdict: {len(judge_errors)}")


if __name__ == "__main__":
    main()
