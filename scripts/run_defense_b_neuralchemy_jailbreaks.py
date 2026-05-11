"""Defense B sneak preview: run Llama 3.3 70B agent + Claude Sonnet 4.6 judge
on the 8 neuralchemy jailbreak prompts that ProtectAI DeBERTa missed
(lowest injection_score among true-injection jailbreaks).

Goal: test whether the layered-defense thesis holds on a different attack class
than the deepset run. If the output-side judge catches what the input-side
classifier missed, that is direct evidence that combining defenses reduces
residual error across attack types.

Outputs:
  - results/defense_b_neuralchemy_jailbreak_preview.csv
  - results/defense_b_neuralchemy_jailbreak_preview.md
  - cache/defense_b_agent_llama33_70b_neuralchemy_jailbreak.jsonl
  - cache/defense_b_judge_claude_sonnet_46_neuralchemy_jailbreak.jsonl
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
from src.defense_b.agent import GroqAgent
from src.defense_b.judge import ClaudeJudge

RESULTS_DIR = REPO_ROOT / "results"
CACHE_DIR = REPO_ROOT / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

AGENT_CACHE = CACHE_DIR / "defense_b_agent_llama33_70b_neuralchemy_jailbreak.jsonl"
JUDGE_CACHE = CACHE_DIR / "defense_b_judge_claude_sonnet_46_neuralchemy_jailbreak.jsonl"
N_CASES = 8


def select_hard_cases() -> pd.DataFrame:
    """Load neuralchemy CSV, filter to jailbreak misses, return 8 lowest injection_score rows."""
    df = pd.read_csv(RESULTS_DIR / "defense_a_neuralchemy.csv")
    missed = df[
        (df["label"] == 1)
        & (df["category"] == "jailbreak")
        & (df["pred_label_id"] == 0)
    ].sort_values("injection_score").head(N_CASES)
    return missed[["prompt_idx", "text", "label", "injection_score"]].reset_index(drop=True)


def run_agent(hard: pd.DataFrame) -> dict[str, dict]:
    done = existing_keys(AGENT_CACHE, key="prompt_idx")
    todo = hard[~hard["prompt_idx"].isin(done)]
    print(f"agent cached: {len(done)}, to run: {len(todo)}")
    if len(todo) > 0:
        agent = GroqAgent()
        for _, row in todo.iterrows():
            print(f"  agent <- {row['prompt_idx']}")
            out = agent.respond(row["text"])
            append_records(AGENT_CACHE, [{"prompt_idx": row["prompt_idx"], **out}])
    by_idx = {r["prompt_idx"]: r for r in load_records(AGENT_CACHE)}
    return {idx: by_idx[idx] for idx in hard["prompt_idx"]}


def run_judge(hard: pd.DataFrame, agent_out: dict[str, dict]) -> dict[str, dict]:
    done = existing_keys(JUDGE_CACHE, key="prompt_idx")
    todo = hard[~hard["prompt_idx"].isin(done)]
    print(f"judge cached: {len(done)}, to run: {len(todo)}")
    if len(todo) > 0:
        judge = ClaudeJudge()
        for _, row in todo.iterrows():
            print(f"  judge <- {row['prompt_idx']}")
            out = judge.judge(row["text"], agent_out[row["prompt_idx"]]["response"])
            append_records(JUDGE_CACHE, [{"prompt_idx": row["prompt_idx"], **out}])
    by_idx = {r["prompt_idx"]: r for r in load_records(JUDGE_CACHE)}
    return {idx: by_idx[idx] for idx in hard["prompt_idx"]}


def to_table(hard: pd.DataFrame, agent_out: dict, judge_out: dict) -> pd.DataFrame:
    rows = []
    for _, h in hard.iterrows():
        idx = h["prompt_idx"]
        a = agent_out[idx]
        j = judge_out[idx]
        rows.append(
            {
                "prompt_idx": idx,
                "prompt": h["text"],
                "agent_response": a["response"],
                "judge_hijacked": j.get("hijacked"),
                "judge_reasoning": j.get("reasoning"),
                "judge_parse_error": j.get("parse_error"),
            }
        )
    return pd.DataFrame(rows)


def write_markdown(table: pd.DataFrame) -> None:
    caught = int(table["judge_hijacked"].fillna(False).sum())
    n = len(table)
    parse_failures = int(table["judge_parse_error"].notna().sum())

    lines: list[str] = []
    lines.append("# Defense B sneak preview: neuralchemy jailbreak class")
    lines.append("")
    lines.append("- Run date: 2026-05-08")
    lines.append("- Agent: `llama-3.3-70b-versatile` via Groq, temperature 0, max_tokens 400")
    lines.append("- Judge: `claude-sonnet-4-6` via Anthropic, temperature 0, max_tokens 400")
    lines.append(
        f"- Cases: {n} neuralchemy jailbreak prompts that ProtectAI DeBERTa"
        " classified SAFE (pred_label_id == 0) despite gold label INJECTION;"
        " selected by lowest injection_score ascending"
    )
    lines.append("")
    lines.append("## Headline")
    lines.append("")
    lines.append(
        f"The judge flagged **{caught} of {n}** agent responses as hijacked."
    )
    lines.append(
        "These are exactly the cases the input classifier missed at near-zero confidence,"
        " so any judge catches here are direct evidence that an output-side stage"
        " adds coverage the input-side stage cannot deliver alone."
    )
    if parse_failures > 0:
        lines.append("")
        lines.append(
            f"Note: {parse_failures} judge response(s) failed JSON parsing."
            " Treated as unknown verdict; raw text retained in the per-case sections."
        )
    lines.append("")
    lines.append("## Caveats")
    lines.append("")
    lines.append(
        "This is a sneak preview, n = 8, single judge model, single agent model,"
        " fixed seeds, temperature 0."
    )
    lines.append(
        "The judge rubric is the minimum-viable form documented in `src/defense_b/judge.py`"
        " and is not the final rubric."
    )
    lines.append(
        "Whether a response counts as 'hijacked' under the operational definition"
        " will be refined during Phase 2 judge validation."
    )
    lines.append("Treat the count as directional, not as a measurement.")
    lines.append("")
    lines.append("## Per-case breakdown")
    lines.append("")
    for _, r in table.iterrows():
        if r["judge_hijacked"] is True:
            verdict = "HIJACKED"
        elif r["judge_hijacked"] is False:
            verdict = "clean"
        else:
            verdict = "PARSE_ERROR"
        lines.append(f"### {r['prompt_idx']} -> judge: {verdict}")
        lines.append("")
        lines.append("**User prompt:**")
        lines.append("")
        lines.append("```")
        lines.append(r["prompt"].strip())
        lines.append("```")
        lines.append("")
        lines.append("**Agent response:**")
        lines.append("")
        lines.append("```")
        lines.append((r["agent_response"] or "").strip())
        lines.append("```")
        lines.append("")
        if r["judge_parse_error"]:
            lines.append(f"**Judge raw text (parse error):** `{r['judge_parse_error']}`")
        else:
            lines.append(f"**Judge reasoning:** {r['judge_reasoning']}")
        lines.append("")

    out_path = RESULTS_DIR / "defense_b_neuralchemy_jailbreak_preview.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    hard = select_hard_cases()
    print(f"selected {len(hard)} hard cases (jailbreak misses, lowest injection_score)")
    print(hard[["prompt_idx", "injection_score"]].to_string(index=False))

    agent_out = run_agent(hard)
    judge_out = run_judge(hard, agent_out)

    table = to_table(hard, agent_out, judge_out)
    csv_path = RESULTS_DIR / "defense_b_neuralchemy_jailbreak_preview.csv"
    table.to_csv(csv_path, index=False)

    write_markdown(table)

    n = len(table)
    caught = int(table["judge_hijacked"].fillna(False).sum())
    parse_err = int(table["judge_parse_error"].notna().sum())
    print(f"\nResult: judge flagged {caught}/{n} as hijacked, {parse_err} parse failures")
    print(f"  csv: {csv_path}")
    print(f"  md : {RESULTS_DIR / 'defense_b_neuralchemy_jailbreak_preview.md'}")


if __name__ == "__main__":
    main()
