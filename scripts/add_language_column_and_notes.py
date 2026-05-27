"""Add a `language` column to the audit file using langdetect, and write the
rank 39 definition-boundary note. Preserves all existing user-entered labels
and notes.

The `language` column is for analytical purposes only; it does not change
any audit labels. Useful for the report's discussion of cross-language
classifier behaviour and pretraining-corpus bias.

Re-saves the file as utf-8-sig so Excel keeps rendering it correctly.
"""
from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd
from langdetect import detect_langs, DetectorFactory

DetectorFactory.seed = 42  # deterministic

REPO = Path(__file__).resolve().parents[1]
PATH = REPO / "results" / "label_audit_sample_disagreement_sorted_post_audit.csv"

RANK39_NOTE = (
    "Definition-boundary disagreement with dataset. The prompt requests harmful-content "
    "output (insider-trading analysis) but uses no §3.1 Step 4 pattern (no override, "
    "persona, authority, extraction, encoding, or indirect carrier). Per op-defs §2.3 "
    "and the §3.1 scope note (v1.22), content-policy violations not driven by an "
    "injection mechanism are not hijacks; under §3.1 this row is BENIGN. Audit value "
    "1+ambiguous reflects practitioner concern about output harm, which is the §3.2 "
    "response-side concern, not the §3.1 input-side classification. Dataset's 0 is "
    "correct under §3.1's narrow definition."
)


def detect_lang(text) -> str:
    if pd.isna(text) or not str(text).strip():
        return "unknown"
    try:
        guesses = detect_langs(str(text))
        if not guesses:
            return "unknown"
        top = guesses[0]
        # If confidence is low, return mixed
        if top.prob < 0.6:
            others = "+".join(g.lang for g in guesses[:3])
            return f"mixed({others})"
        return top.lang
    except Exception:
        return "error"


def main() -> None:
    df = pd.read_csv(PATH, encoding="utf-8-sig")
    print(f"Loaded {len(df)} rows.")

    # Detect language
    print("Detecting languages ...")
    df["language"] = df["prompt"].apply(detect_lang)

    # Place language column right after `dataset` for readability
    cols = list(df.columns)
    cols.remove("language")
    insert_after = cols.index("dataset") + 1
    cols.insert(insert_after, "language")
    df = df[cols]

    # Apply rank 39 note
    mask = df["prompt_idx"] == "neuralchemy_train_00156"
    if mask.sum() == 0:
        print("WARNING: rank 39 (neuralchemy_train_00156) not found")
    else:
        df.loc[mask, "notes"] = RANK39_NOTE
        print("Applied rank 39 note.")

    df.to_csv(PATH, index=False, encoding="utf-8-sig")
    print(f"Wrote {PATH.relative_to(REPO)}")

    # Quick distribution summary
    print()
    print("=== Language distribution ===")
    print(df["language"].value_counts())
    print()
    print("=== Language by dataset ===")
    print(df.groupby(["dataset", "language"]).size().unstack(fill_value=0))


if __name__ == "__main__":
    main()
