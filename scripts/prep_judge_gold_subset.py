"""Prepare the 150-row judge gold subset for Task 3 human labeling.

Three augmentations:
1. Add v1.21 judge verdicts (Sonnet, Haiku, GPT-4o-mini) by joining on
   prompt_idx from the 500-row pilot (`defense_b_pilot.csv` and
   `defense_b_judge_cost_comparison.csv`). The existing v1.8 minimum-rubric
   verdicts are kept under their original column names for comparison.
2. Add system_prompt column for SPML rows (deepset and neuralchemy stay blank).
3. Add langdetect-derived language column.

Re-saves as utf-8-sig so Excel renders non-ASCII correctly.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from langdetect import detect_langs, DetectorFactory
from datasets import load_from_disk

DetectorFactory.seed = 42

REPO = Path(__file__).resolve().parents[1]
GOLD_PATH = REPO / "results" / "judge_gold_subset.csv"
PILOT_PATH = REPO / "results" / "defense_b_pilot.csv"
SWEEP_PATH = REPO / "results" / "defense_b_judge_cost_comparison.csv"
SPML_DIR = REPO / "data" / "spml"


def detect_lang(text) -> str:
    if pd.isna(text) or not str(text).strip():
        return "unknown"
    try:
        guesses = detect_langs(str(text))
        if not guesses:
            return "unknown"
        top = guesses[0]
        if top.prob < 0.6:
            others = "+".join(g.lang for g in guesses[:3])
            return f"mixed({others})"
        return top.lang
    except Exception:
        return "error"


def main() -> None:
    df = pd.read_csv(GOLD_PATH)
    print(f"Loaded gold subset: {len(df)} rows, {len(df.columns)} columns")
    print(f"  Existing columns: {list(df.columns)}")

    # 1. Add v1.21 judge verdicts from pilot + cheap-sweep
    pilot = pd.read_csv(PILOT_PATH)
    sweep = pd.read_csv(SWEEP_PATH)

    sonnet_v121 = pilot.set_index("prompt_idx")[
        ["sonnet_verdict_v121", "sonnet_categories_v121", "sonnet_reason_v121"]
    ].to_dict("index")
    sweep_v121 = sweep.set_index("prompt_idx")[
        ["haiku45_verdict_v121", "haiku45_categories_v121", "haiku45_reason_v121",
         "gpt4mini_verdict_v121", "gpt4mini_categories_v121", "gpt4mini_reason_v121"]
    ].to_dict("index")

    new_cols = {
        "sonnet_verdict_v121": [], "sonnet_categories_v121": [], "sonnet_reason_v121": [],
        "haiku45_verdict_v121": [], "haiku45_categories_v121": [], "haiku45_reason_v121": [],
        "gpt4mini_verdict_v121": [], "gpt4mini_categories_v121": [], "gpt4mini_reason_v121": [],
    }
    n_v121_added = 0
    for _, row in df.iterrows():
        pid = row["prompt_idx"]
        s = sonnet_v121.get(pid, {})
        w = sweep_v121.get(pid, {})
        if s:
            n_v121_added += 1
        for col in ["sonnet_verdict_v121", "sonnet_categories_v121", "sonnet_reason_v121"]:
            new_cols[col].append(s.get(col, ""))
        for col in ["haiku45_verdict_v121", "haiku45_categories_v121", "haiku45_reason_v121",
                    "gpt4mini_verdict_v121", "gpt4mini_categories_v121", "gpt4mini_reason_v121"]:
            new_cols[col].append(w.get(col, ""))

    for col, vals in new_cols.items():
        df[col] = vals
    print(f"  Added v1.21 verdict columns; matched {n_v121_added}/{len(df)} rows in pilot")

    # 2. Add system_prompt column for SPML rows
    if SPML_DIR.exists():
        sp = load_from_disk(SPML_DIR)["train"].to_pandas().reset_index(drop=True)
        sp["prompt_idx"] = "spml_train_" + sp.index.astype(str).str.zfill(5)
        spml_lookup = sp.set_index("prompt_idx")["System Prompt"].to_dict()
        system_prompts = []
        n_spml = 0
        for _, row in df.iterrows():
            if row["dataset"] == "spml":
                sp_text = spml_lookup.get(row["prompt_idx"], "")
                system_prompts.append(sp_text)
                if sp_text:
                    n_spml += 1
            else:
                system_prompts.append("")
        df["system_prompt"] = system_prompts
        print(f"  Added system_prompt column; populated for {n_spml} SPML rows")
    else:
        print(f"  WARNING: SPML data not found at {SPML_DIR}; system_prompt column not added")

    # 3. Add language column
    print("  Detecting languages ...")
    df["language"] = df["prompt"].apply(detect_lang)
    print(f"  Added language column; distribution:")
    print(df["language"].value_counts().to_string())

    # Reorder columns for human-readable Excel display:
    # prompt_idx, dataset, language, label, prompt, system_prompt, agent_response,
    # then the human-labeling columns (still empty for Boga to fill),
    # then judge verdicts (v1.8 and v1.21) for reference,
    # then any remaining columns.
    desired_front = [
        "prompt_idx", "dataset", "language", "label", "subcategory",
        "prompt", "system_prompt", "agent_response",
        "human_verdict", "hijack_categories", "notes",
        "sonnet_verdict", "sonnet_reasoning",
        "sonnet_verdict_v121", "sonnet_categories_v121", "sonnet_reason_v121",
        "haiku45_hijacked", "haiku45_verdict_v121", "haiku45_categories_v121", "haiku45_reason_v121",
        "gpt4mini_hijacked", "gpt4mini_verdict_v121", "gpt4mini_categories_v121", "gpt4mini_reason_v121",
    ]
    existing_front = [c for c in desired_front if c in df.columns]
    rest = [c for c in df.columns if c not in existing_front]
    df = df[existing_front + rest]

    df.to_csv(GOLD_PATH, index=False, encoding="utf-8-sig")
    print(f"\nWrote {GOLD_PATH.relative_to(REPO)} ({len(df)} rows, {len(df.columns)} columns, utf-8-sig)")


if __name__ == "__main__":
    main()
