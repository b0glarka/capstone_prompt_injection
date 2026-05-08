"""GPT-4o sensitivity check on the 8 deepset Defense B sneak-preview cases.

Reuses the cached agent responses (Llama 3.3 70B output) from the original
Claude-judged sneak preview, runs GPT-4o on the same (prompt, response) pairs,
and computes per-case agreement with the Claude verdicts.

Goal: a fast parallel-judge robustness data point. Are the Claude verdicts
idiosyncratic to one model family, or does GPT-4o see the same hijacks?
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
load_dotenv(REPO_ROOT / ".env")

from src.cache import append_records, existing_keys, load_records
from src.defense_b.judge import GPT4oJudge

CACHE_DIR = REPO_ROOT / "cache"
RESULTS_DIR = REPO_ROOT / "results"
AGENT_CACHE = CACHE_DIR / "defense_b_agent_llama33_70b.jsonl"
CLAUDE_CACHE = CACHE_DIR / "defense_b_judge_claude_sonnet_46.jsonl"
GPT4O_CACHE = CACHE_DIR / "defense_b_judge_gpt4o_deepset.jsonl"


def main() -> None:
    sneak = pd.read_csv(RESULTS_DIR / "defense_b_sneak_preview.csv")
    agent_records = {r["prompt_idx"]: r for r in load_records(AGENT_CACHE)}
    claude_records = {r["prompt_idx"]: r for r in load_records(CLAUDE_CACHE)}

    done = existing_keys(GPT4O_CACHE, key="prompt_idx")
    todo = sneak[~sneak["prompt_idx"].isin(done)]
    print(f"GPT-4o cached: {len(done)}, to run: {len(todo)}")

    if len(todo) > 0:
        judge = GPT4oJudge()
        new = []
        for _, row in todo.iterrows():
            agent_resp = agent_records[row["prompt_idx"]]["response"]
            print(f"  GPT-4o <- {row['prompt_idx']}")
            out = judge.judge(row["prompt"], agent_resp)
            new.append({"prompt_idx": row["prompt_idx"], **out})
        append_records(GPT4O_CACHE, new)

    gpt_records = {r["prompt_idx"]: r for r in load_records(GPT4O_CACHE)}

    rows = []
    for _, s in sneak.iterrows():
        idx = s["prompt_idx"]
        c = claude_records[idx]
        g = gpt_records[idx]
        rows.append({
            "prompt_idx": idx,
            "claude_hijacked": bool(c.get("hijacked")) if c.get("hijacked") is not None else None,
            "claude_reasoning": c.get("reasoning"),
            "gpt4o_hijacked": bool(g.get("hijacked")) if g.get("hijacked") is not None else None,
            "gpt4o_reasoning": g.get("reasoning"),
        })
    df = pd.DataFrame(rows)
    df["agree"] = df["claude_hijacked"] == df["gpt4o_hijacked"]
    df.to_csv(RESULTS_DIR / "defense_b_judge_sensitivity_deepset.csv", index=False)

    n = len(df)
    n_agree = int(df["agree"].sum())
    claude_caught = int(df["claude_hijacked"].fillna(False).sum())
    gpt_caught = int(df["gpt4o_hijacked"].fillna(False).sum())

    md_lines = [
        "# Judge sensitivity check: Claude Sonnet 4.6 vs GPT-4o on deepset 8\n",
        "- Run date: 2026-05-08",
        "- Cases: same 8 deepset prompts that DeBERTa missed at injection_score < 0.001",
        "- Same agent responses (Llama 3.3 70B, cached) sent to both judges",
        "- Same minimum-rubric judge prompt for both",
        "",
        "## Headline",
        "",
        f"Claude flagged {claude_caught}/{n} as hijacked. GPT-4o flagged {gpt_caught}/{n}. The two judges agreed on **{n_agree}/{n}** cases.",
        "",
        "Agreement rate of "
        + f"{n_agree/n:.1%} "
        + "across n=8 is directional only (kappa is not meaningful at this sample size). The headline is whether GPT-4o broadly tracks Claude or contradicts it. ",
        ("Broad tracking suggests the Claude verdicts are not idiosyncratic to one model family." if n_agree >= 6
         else "Substantial disagreement suggests the judge call is sensitive to model family and the production rubric will need iteration."),
        "",
        "## Per-case",
        "",
        "| prompt_idx | Claude | GPT-4o | agree |",
        "|---|---|---|---|",
    ]
    for _, r in df.iterrows():
        c_v = "HIJACKED" if r["claude_hijacked"] else "clean"
        g_v = "HIJACKED" if r["gpt4o_hijacked"] else "clean"
        md_lines.append(f"| {r['prompt_idx']} | {c_v} | {g_v} | {'yes' if r['agree'] else 'NO'} |")

    md_lines.append("")
    md_lines.append("## Caveats")
    md_lines.append("")
    md_lines.append("Sneak preview, n=8. Two judge models, single rubric, single agent. Treat as directional only. Full judge validation against a 150-row human gold subset, with Cohen's kappa, is on the Phase 2 schedule.")

    (RESULTS_DIR / "defense_b_judge_sensitivity_deepset.md").write_text(
        "\n".join(md_lines), encoding="utf-8"
    )

    print(f"\nClaude: {claude_caught}/{n}, GPT-4o: {gpt_caught}/{n}, agreement: {n_agree}/{n}")
    print(f"  csv: {RESULTS_DIR / 'defense_b_judge_sensitivity_deepset.csv'}")
    print(f"  md : {RESULTS_DIR / 'defense_b_judge_sensitivity_deepset.md'}")


if __name__ == "__main__":
    main()
