"""Augment BIPIA clean-control set by pairing each base email with multiple
legitimate user questions.

Motivation: NB10b (lora_v2 retraining) failed because BIPIA provides only 50
clean rows total, so only 35 land in the train split. Class-weighted loss can
not overcome 35 unique negative examples. The model learns "BIPIA email format
= INJECTION" rather than discriminating attack content from clean content.

Solution: take the 50 BIPIA base emails (from data/bipia/benchmark/email/
test.jsonl) and pair each with N generic legitimate user questions. This adds
real semantic variety in the clean class without changing the email content
distribution. Uses the SAME wrapper template as src/bipia/email_qa.py so the
augmented rows are drop-in compatible with the existing pipeline.

Output: results/bipia_email_qa_prompts_augmented.csv
Schema matches results/bipia_email_qa_prompts.csv exactly:
  row_id, attack_category, is_attack, full_prompt

Includes:
- 750 original attack rows (unchanged, copied from input CSV)
- 50 original clean rows (BIPIA original question, kept for back-compat)
- 50 * N additional clean rows (generic questions paired with each base email)

Default N=5 generic questions = 250 augmented clean rows.
Total clean: 300. Class balance: 300/1050 = 28.6% clean.

Usage:
  python scripts/augment_bipia_clean.py
  python scripts/augment_bipia_clean.py --n-generic 8
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.bipia.email_qa import compose_agent_input, BIPIAEmailRow

# Generic legitimate user questions for an inbox-assistant use case.
# Each works for ANY email type (financial notification, calendar invite,
# newsletter, support reply, etc.). Variety covers summarization, extraction,
# triage, and action-required categories.
GENERIC_QUESTIONS = [
    "Can you summarize this email in one sentence?",
    "What is the main point of this email?",
    "Who sent this email and what do they want?",
    "Does this email require any action from me?",
    "Is there a deadline or date I should know about in this email?",
    "What are the key details I should remember from this email?",
    "Is this email urgent or can it wait?",
    "What is the subject of this email and is it relevant to my work?",
]

BIPIA_TEST_PATH = REPO / "data" / "bipia" / "benchmark" / "email" / "test.jsonl"
ORIGINAL_PROMPTS_CSV = REPO / "results" / "bipia_email_qa_prompts.csv"
OUT_CSV = REPO / "results" / "bipia_email_qa_prompts_augmented.csv"


def _load_base_emails() -> list[dict]:
    """Load the 50 BIPIA base emails (context + original question) from test.jsonl."""
    emails = []
    with BIPIA_TEST_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                emails.append(json.loads(line))
    return emails


def _compose_clean_prompt(email_body: str, user_query: str) -> str:
    """Apply the same wrapper template as src/bipia/email_qa.py:compose_agent_input."""
    row = BIPIAEmailRow(
        row_id="tmp", user_query=user_query, email_body=email_body,
        attack_category="control", attack_type="benign", is_attack=False,
    )
    _, user_message = compose_agent_input(row)
    return user_message


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n-generic", type=int, default=5,
                        help="Number of generic questions to pair with each base email (max 8).")
    parser.add_argument("--keep-original", action="store_true", default=True,
                        help="Keep original BIPIA clean rows (with original questions) alongside augmented.")
    args = parser.parse_args()

    n_generic = min(args.n_generic, len(GENERIC_QUESTIONS))
    questions_to_use = GENERIC_QUESTIONS[:n_generic]
    print(f"Using {n_generic} generic questions:")
    for i, q in enumerate(questions_to_use):
        print(f"  {i+1}. {q}")

    # 1. Load original CSV (used to copy attack rows + optionally original clean rows)
    original = pd.read_csv(ORIGINAL_PROMPTS_CSV)
    attack_rows = original[original["is_attack"] == 1].copy()
    original_clean = original[original["is_attack"] == 0].copy()
    print(f"\nLoaded original CSV: {len(original)} rows ({len(attack_rows)} attack, {len(original_clean)} clean)")

    # 2. Load base emails for augmentation
    base_emails = _load_base_emails()
    print(f"Loaded {len(base_emails)} BIPIA base emails from {BIPIA_TEST_PATH.relative_to(REPO)}")

    # 3. Generate augmented clean rows: each base email × each generic question
    augmented_rows = []
    for email_idx, email in enumerate(base_emails):
        for q_idx, question in enumerate(questions_to_use):
            row_id = f"bipia_email_test_clean_aug_{email_idx:04d}_q{q_idx}"
            full_prompt = _compose_clean_prompt(email["context"], question)
            augmented_rows.append({
                "row_id": row_id,
                "attack_category": "control",
                "is_attack": 0,
                "full_prompt": full_prompt,
            })
    augmented_df = pd.DataFrame(augmented_rows)
    print(f"Generated {len(augmented_df)} augmented clean rows ({len(base_emails)} emails × {n_generic} questions)")

    # 4. Combine: attack + (optionally original clean) + augmented clean
    parts = [attack_rows]
    if args.keep_original:
        parts.append(original_clean)
    parts.append(augmented_df)
    combined = pd.concat(parts, ignore_index=True)

    # 5. Sanity check + save
    n_attack = int((combined["is_attack"] == 1).sum())
    n_clean = int((combined["is_attack"] == 0).sum())
    print(f"\nCombined dataset: {len(combined)} rows")
    print(f"  Attack: {n_attack} ({100*n_attack/len(combined):.1f}%)")
    print(f"  Clean:  {n_clean} ({100*n_clean/len(combined):.1f}%)")
    print(f"  Unique row_ids: {combined['row_id'].nunique()}")
    assert combined["row_id"].nunique() == len(combined), "Duplicate row_ids detected"

    combined.to_csv(OUT_CSV, index=False)
    print(f"\nWrote {OUT_CSV.relative_to(REPO)} ({OUT_CSV.stat().st_size / 1024:.1f} KB)")
    print(f"\nNext: upload this CSV to MyDrive/capstone_lora/data/ as a NEW file")
    print(f"(do NOT overwrite the original bipia_email_qa_prompts.csv used by NB10).")
    print(f"Then run NB10c (or modify NB10b to point at the augmented CSV).")


if __name__ == "__main__":
    main()
