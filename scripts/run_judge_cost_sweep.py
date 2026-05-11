"""Cheap-judge cost-sensitivity sweep on the Defense B 500-row pilot.

Reuses the cached (prompt, agent_response) pairs from the Sonnet pilot and
re-judges them with two cheaper alternative judges:
  - Claude Haiku 4.5 (~5x cheaper than Sonnet 4.6)
  - GPT-4o-mini    (~20x cheaper than Sonnet 4.6)

Same minimum rubric, same temperature 0. Computes per-pair hijack-flag
agreement and Cohen's kappa to answer the cost-vs-accuracy question with
real data at n = 500.

Caches:
  cache/defense_b_judge_pilot_haiku45.jsonl
  cache/defense_b_judge_pilot_gpt4o_mini.jsonl

Outputs:
  results/defense_b_judge_cost_comparison.csv
  results/defense_b_judge_cost_comparison.md

Cost: ~$0.70 total for 500 rows × 2 judges.
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
from src.defense_b.judge import ClaudeJudge, GPT4oJudge
from src.metrics import kappa

RES = REPO_ROOT / "results"
CACHE = REPO_ROOT / "cache"

AGENT_CACHE = CACHE / "defense_b_agent_pilot.jsonl"
SONNET_CACHE = CACHE / "defense_b_judge_pilot.jsonl"
HAIKU_CACHE = CACHE / "defense_b_judge_pilot_haiku45.jsonl"
GPT_MINI_CACHE = CACHE / "defense_b_judge_pilot_gpt4o_mini.jsonl"

HAIKU_MODEL = "claude-haiku-4-5"
GPT_MINI_MODEL = "gpt-4o-mini"


def run_one_judge(pilot: pd.DataFrame, agent_records: dict, judge, cache_path: Path, label: str) -> dict:
    done = existing_keys(cache_path, key="prompt_idx")
    todo = pilot[~pilot["prompt_idx"].isin(done)]
    print(f"\n[{label}] cached: {len(done)}, to run: {len(todo)}")
    if len(todo) > 0:
        for _, row in tqdm(todo.iterrows(), total=len(todo), desc=label):
            agent_resp = agent_records[row["prompt_idx"]]["response"]
            out = judge.judge(row["prompt"], agent_resp)
            append_records(cache_path, [{"prompt_idx": row["prompt_idx"], **out}])
    return {r["prompt_idx"]: r for r in load_records(cache_path)}


def harmonize(records: dict, idx_list) -> pd.Series:
    """Pull `judge_hijacked` for each prompt_idx; None where blocked or missing."""
    out = []
    for idx in idx_list:
        r = records.get(idx, {})
        if r.get("judge_blocked") or r.get("hijacked") is None:
            out.append(np.nan)
        else:
            out.append(int(bool(r.get("hijacked"))))
    return pd.Series(out)


def main() -> None:
    # Load pilot rows and cached Sonnet verdicts
    pilot = pd.read_csv(RES / "defense_b_pilot.csv")  # built by run_defense_b_pilot.py
    pilot = pilot[["prompt_idx", "dataset", "subcategory", "label"]].copy()
    # We also need the original prompts and agent responses
    es = pd.read_parquet(RES / "eval_set.parquet")[["prompt_idx", "prompt"]]
    pilot = pilot.merge(es, on="prompt_idx", how="left")
    agent_records = {r["prompt_idx"]: r for r in load_records(AGENT_CACHE)}
    sonnet_records = {r["prompt_idx"]: r for r in load_records(SONNET_CACHE)}

    # Run the two cheaper judges
    haiku = ClaudeJudge(model=HAIKU_MODEL)
    gpt_mini = GPT4oJudge(model=GPT_MINI_MODEL)
    haiku_records = run_one_judge(pilot, agent_records, haiku, HAIKU_CACHE, "haiku45")
    gpt_mini_records = run_one_judge(pilot, agent_records, gpt_mini, GPT_MINI_CACHE, "gpt4o_mini")

    # Harmonize to a comparison table
    idx_list = pilot["prompt_idx"].tolist()
    cmp = pilot.copy()
    cmp["sonnet_hijacked"]   = harmonize(sonnet_records, idx_list).values
    cmp["haiku45_hijacked"]  = harmonize(haiku_records, idx_list).values
    cmp["gpt4mini_hijacked"] = harmonize(gpt_mini_records, idx_list).values
    cmp["sonnet_blocked"]   = [sonnet_records.get(i, {}).get("judge_blocked", False) for i in idx_list]
    cmp["haiku45_blocked"]  = [haiku_records.get(i, {}).get("judge_blocked", False) for i in idx_list]
    cmp["gpt4mini_blocked"] = [gpt_mini_records.get(i, {}).get("judge_blocked", False) for i in idx_list]
    cmp.to_csv(RES / "defense_b_judge_cost_comparison.csv", index=False)

    # Agreement on rows where all three judges produced a verdict
    valid = cmp.dropna(subset=["sonnet_hijacked", "haiku45_hijacked", "gpt4mini_hijacked"])
    n_valid = len(valid)
    n_total = len(cmp)
    s = valid["sonnet_hijacked"].astype(int)
    h = valid["haiku45_hijacked"].astype(int)
    g = valid["gpt4mini_hijacked"].astype(int)

    pairwise = {
        "sonnet_vs_haiku45": {
            "agreement_rate": float((s == h).mean()),
            "kappa": kappa(s, h),
        },
        "sonnet_vs_gpt4mini": {
            "agreement_rate": float((s == g).mean()),
            "kappa": kappa(s, g),
        },
        "haiku45_vs_gpt4mini": {
            "agreement_rate": float((h == g).mean()),
            "kappa": kappa(h, g),
        },
    }
    all3_agree_rate = float(((s == h) & (h == g)).mean())

    # Cost per judge: use Anthropic / OpenAI per-million prices, observed token totals
    def _cost(records, in_price, out_price):
        in_tok  = sum(r.get("input_tokens", 0) for r in records.values())
        out_tok = sum(r.get("output_tokens", 0) for r in records.values())
        return (in_tok * in_price + out_tok * out_price) / 1_000_000, in_tok, out_tok

    sonnet_cost,  s_in,  s_out  = _cost(sonnet_records,   3.0, 15.0)
    haiku_cost,   h_in,  h_out  = _cost(haiku_records,    1.0,  5.0)
    gpt_mini_cost,g_in,  g_out  = _cost(gpt_mini_records, 0.15, 0.60)

    # Write summary markdown
    lines = [
        "# Judge cost-vs-accuracy sweep (Defense B 500-row pilot)\n",
        "- Run date: 2026-05-11",
        f"- Sample: same 500 (prompt, agent response) pairs as the formal Sonnet pilot",
        f"- Judges: Claude Sonnet 4.6 (primary), Claude Haiku 4.5 (5x cheaper), GPT-4o-mini (~20x cheaper)",
        f"- Same minimum-rubric judge prompt, temperature 0, max_tokens 400 for all three",
        "",
        "## Headline",
        "",
        f"At n = {n_valid} pairs where all three judges produced a verdict (of {n_total} total), pairwise agreement and Cohen's kappa:",
        "",
        "| Pair | Agreement | Cohen's kappa |",
        "|---|---|---|",
        f"| Sonnet 4.6 vs Haiku 4.5 | {pairwise['sonnet_vs_haiku45']['agreement_rate']:.3f} | {pairwise['sonnet_vs_haiku45']['kappa']:.3f} |",
        f"| Sonnet 4.6 vs GPT-4o-mini | {pairwise['sonnet_vs_gpt4mini']['agreement_rate']:.3f} | {pairwise['sonnet_vs_gpt4mini']['kappa']:.3f} |",
        f"| Haiku 4.5 vs GPT-4o-mini | {pairwise['haiku45_vs_gpt4mini']['agreement_rate']:.3f} | {pairwise['haiku45_vs_gpt4mini']['kappa']:.3f} |",
        "",
        f"All three judges agree on **{all3_agree_rate:.3f}** of pairs.",
        "",
        "## Cost per judge (500 rows)",
        "",
        "| Judge | Input tokens | Output tokens | Cost (USD) | Implied cost at 4,546 rows |",
        "|---|---|---|---|---|",
        f"| Sonnet 4.6 | {s_in:,} | {s_out:,} | ${sonnet_cost:.4f} | ${sonnet_cost * 4546 / 500:.2f} |",
        f"| Haiku 4.5 | {h_in:,} | {h_out:,} | ${haiku_cost:.4f} | ${haiku_cost * 4546 / 500:.2f} |",
        f"| GPT-4o-mini | {g_in:,} | {g_out:,} | ${gpt_mini_cost:.4f} | ${gpt_mini_cost * 4546 / 500:.2f} |",
        "",
        "## Per-dataset agreement",
        "",
    ]
    for ds in ["deepset", "neuralchemy", "spml"]:
        sub = valid[valid["dataset"] == ds]
        if len(sub) == 0:
            continue
        ss = sub["sonnet_hijacked"].astype(int)
        hh = sub["haiku45_hijacked"].astype(int)
        gg = sub["gpt4mini_hijacked"].astype(int)
        lines.append(
            f"- {ds} (n={len(sub)}): Sonnet/Haiku agreement {(ss==hh).mean():.3f}, "
            f"Sonnet/GPT-mini {(ss==gg).mean():.3f}, all three {((ss==hh)&(hh==gg)).mean():.3f}"
        )
    lines += [
        "",
        "## Reading",
        "",
        "Cohen's kappa above 0.8 is conventionally read as strong agreement; 0.6 to 0.8 substantial; 0.4 to 0.6 moderate. Use those thresholds to decide whether the cheaper judge can replace Sonnet at scale. Pair the agreement number with the cost-extrapolation column: a judge that's 20x cheaper with kappa above 0.8 is a clear win for the production run.",
        "",
        "## Caveats",
        "",
        "Same minimum-rubric judge prompt for all three. Single agent model (Llama 3.3 70B). Pilot scale, not full eval set. Cohen's kappa is sensitive to class balance; values reported here are unadjusted. Judge-blocked rows (content-policy refusals) are excluded from the agreement denominator. Production rubric iteration is a separate Phase 2 step and may shift these numbers.",
    ]
    (RES / "defense_b_judge_cost_comparison.md").write_text("\n".join(lines), encoding="utf-8")

    print("\n=== Headline ===")
    print(f"Sonnet vs Haiku 4.5:   agreement {pairwise['sonnet_vs_haiku45']['agreement_rate']:.3f}, kappa {pairwise['sonnet_vs_haiku45']['kappa']:.3f}")
    print(f"Sonnet vs GPT-4o-mini: agreement {pairwise['sonnet_vs_gpt4mini']['agreement_rate']:.3f}, kappa {pairwise['sonnet_vs_gpt4mini']['kappa']:.3f}")
    print(f"Cost: Sonnet ${sonnet_cost:.3f}, Haiku ${haiku_cost:.3f}, GPT-4o-mini ${gpt_mini_cost:.3f}")
    print(f"  csv: {RES / 'defense_b_judge_cost_comparison.csv'}")
    print(f"  md : {RES / 'defense_b_judge_cost_comparison.md'}")


if __name__ == "__main__":
    main()
