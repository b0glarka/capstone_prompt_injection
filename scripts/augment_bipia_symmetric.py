"""Symmetric BIPIA augmentation: decorrelate question style from label.

Motivation: NB10c augmentation produced apparently strong results (d=9.37) but
NB10d Test 1 revealed a question-style shortcut. Training data had perfect
(question style x label) correlation: all clean rows used generic questions,
all attack rows used BIPIA's specific questions. The model learned that
correlation as a shortcut. When attacks were paired with generic questions at
test time (Test 1), flag rate collapsed to 0.487.

Fix: augment ATTACK rows the same way clean rows were augmented. Each base
email contributes equal counts of clean and attack rows across all 6 question
styles (1 BIPIA original + 5 generic). The marginal distribution of question
styles is identical across both classes, so question style is no longer a
discriminative signal.

Additional fix: base-email-stratified split. NB10d Test 4 found 100% clean
train/test email-body overlap. Here, each base email goes entirely into one
split. Train and test share zero base emails, so memorization is structurally
impossible.

Design (per base email, 21 rows):
- 6 clean rows: 1 with original BIPIA question + 5 with generic questions
- 15 attack rows: 1 per attack category, each with a randomly-assigned
  question style (5 generic + 1 BIPIA original)

50 base emails x 21 rows = 1,050 rows total.
35 train / 7 val / 8 test base emails => 735 / 147 / 168 rows.

Class balance: 6/21 = 28.6% clean, 71.4% attack (same as NB10c).
Question-style distribution: ~equal across both classes (the key invariant).
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.bipia.email_qa import compose_agent_input, BIPIAEmailRow, _splice_attack

GENERIC_QUESTIONS = [
    "Can you summarize this email in one sentence?",
    "What is the main point of this email?",
    "Who sent this email and what do they want?",
    "Does this email require any action from me?",
    "Is there a deadline or date I should know about in this email?",
]

BIPIA_TEST_EMAILS = REPO / "data" / "bipia" / "benchmark" / "email" / "test.jsonl"
BIPIA_TEST_ATTACKS = REPO / "data" / "bipia" / "benchmark" / "text_attack_test.json"
OUT_CSV = REPO / "results" / "bipia_email_qa_prompts_symmetric.csv"


def _compose(email_body: str, user_query: str) -> str:
    row = BIPIAEmailRow(
        row_id="tmp", user_query=user_query, email_body=email_body,
        attack_category="control", attack_type="benign", is_attack=False,
    )
    _, msg = compose_agent_input(row)
    return msg


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    rng = random.Random(args.seed)

    with BIPIA_TEST_EMAILS.open("r", encoding="utf-8") as f:
        emails = [json.loads(line) for line in f if line.strip()]
    with BIPIA_TEST_ATTACKS.open("r", encoding="utf-8") as f:
        attacks_by_cat = json.load(f)

    print(f"Loaded {len(emails)} base emails, {len(attacks_by_cat)} attack categories")
    print(f"Generic questions: {len(GENERIC_QUESTIONS)} + 1 BIPIA original per email = 6 question styles")

    all_question_styles_per_email = []  # list of 6 questions for each email
    for em in emails:
        styles = [em["question"]] + list(GENERIC_QUESTIONS)
        all_question_styles_per_email.append(styles)

    # Base-email-stratified split: 35 train / 7 val / 8 test (out of 50)
    email_indices = list(range(len(emails)))
    train_val_idx, test_idx = train_test_split(email_indices, test_size=0.15, random_state=args.seed)
    train_idx, val_idx = train_test_split(train_val_idx, test_size=0.15/0.85, random_state=args.seed)
    split_of_email = {}
    for i in train_idx: split_of_email[i] = "train"
    for i in val_idx: split_of_email[i] = "val"
    for i in test_idx: split_of_email[i] = "test"
    print(f"\nBase-email split: train={len(train_idx)}, val={len(val_idx)}, test={len(test_idx)}")

    rows = []
    for email_idx, em in enumerate(emails):
        split = split_of_email[email_idx]
        question_styles = all_question_styles_per_email[email_idx]
        # 6 clean rows: each question style once
        for q_idx, q in enumerate(question_styles):
            style_name = "bipia_original" if q_idx == 0 else f"generic_{q_idx-1}"
            rows.append({
                "row_id": f"sym_clean_{email_idx:03d}_q{q_idx}",
                "attack_category": "control",
                "is_attack": 0,
                "base_email_idx": email_idx,
                "question_style": style_name,
                "split": split,
                "full_prompt": _compose(em["context"], q),
            })
        # 15 attack rows: one per category, with a randomly assigned question style
        for cat_idx, (cat, templates) in enumerate(attacks_by_cat.items()):
            attack_text = rng.choice(templates)
            spliced_body = _splice_attack(em["context"], attack_text, "end")
            q_idx = rng.randint(0, len(question_styles) - 1)
            q = question_styles[q_idx]
            style_name = "bipia_original" if q_idx == 0 else f"generic_{q_idx-1}"
            rows.append({
                "row_id": f"sym_attack_{email_idx:03d}_c{cat_idx:02d}",
                "attack_category": cat,
                "is_attack": 1,
                "base_email_idx": email_idx,
                "question_style": style_name,
                "split": split,
                "full_prompt": _compose(spliced_body, q),
            })

    df = pd.DataFrame(rows)
    print(f"\nGenerated {len(df)} rows")
    print(f"Class balance: {df['is_attack'].value_counts().to_dict()}")
    print(f"\nSplit sizes:")
    print(df.groupby('split')['is_attack'].agg(['count', 'sum']))
    print(f"\nQuestion-style distribution PER CLASS (the key invariant):")
    print(pd.crosstab(df['question_style'], df['is_attack']))

    df.to_csv(OUT_CSV, index=False)
    print(f"\nWrote {OUT_CSV.relative_to(REPO)} ({OUT_CSV.stat().st_size / 1024:.1f} KB)")
    print(f"\nNext: upload to MyDrive/capstone_lora/data/ as bipia_email_qa_prompts_symmetric.csv")
    print(f"Then run NB10e (notebooks/10e_lora_v4_symmetric_augmented.ipynb)")


if __name__ == "__main__":
    main()
