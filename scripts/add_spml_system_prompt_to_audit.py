"""Add the SPML `system_prompt` column to the label-audit sample.

Why: §3.2 Step 0 (and the design of SPML itself) says an SPML row's
injection status is defined relative to the operator's deployed system
prompt. The current `label_audit_sample_disagreement_sorted.csv` exposes
only the user prompt, which means an auditor labeling SPML rows is
working without the context that gives those rows their injection
status. This script adds a `system_prompt` column populated for SPML
rows (empty for deepset / neuralchemy, which have no system_prompt).

Preserves any existing audit_label / ambiguous / notes entries in the
file. Writes back to the same path with UTF-8-with-BOM encoding so
Excel handles it cleanly going forward (avoids the cp1252 round-trip
that's been corrupting non-ASCII characters).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from datasets import load_from_disk

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

AUDIT_CSV = REPO / "results" / "label_audit_sample_disagreement_sorted.csv"
SPML_DIR = REPO / "data" / "spml"


def main() -> None:
    # Read existing audit file. Encoding may be cp1252 or latin-1 if Excel
    # has saved it; try utf-8 first, then fall back.
    audit = None
    for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            audit = pd.read_csv(AUDIT_CSV, encoding=enc)
            print(f"Read existing audit file with encoding={enc} (shape {audit.shape})")
            break
        except UnicodeDecodeError:
            continue
    if audit is None:
        raise RuntimeError(f"Could not read {AUDIT_CSV} with any tried encoding")

    if "system_prompt" in audit.columns:
        print("Column 'system_prompt' already present; will refresh SPML rows in place.")
        audit = audit.drop(columns=["system_prompt"])

    # Load SPML dataset; index column matches the trailing zero-padded number
    # in `spml_train_XXXXX` prompt_idx values.
    sp = load_from_disk(SPML_DIR)["train"].to_pandas().reset_index(drop=True)
    sp["prompt_idx"] = "spml_train_" + sp.index.astype(str).str.zfill(5)
    spml_lookup = sp.set_index("prompt_idx")["System Prompt"].to_dict()

    # Populate system_prompt for SPML rows only.
    system_prompts = []
    n_spml = 0
    n_missing = 0
    for _, row in audit.iterrows():
        if row["dataset"] == "spml":
            sp_text = spml_lookup.get(row["prompt_idx"])
            if sp_text is None:
                n_missing += 1
                system_prompts.append("")
            else:
                system_prompts.append(sp_text)
                n_spml += 1
        else:
            system_prompts.append("")
    audit["system_prompt"] = system_prompts

    # Move system_prompt to right after `prompt` for readability in Excel.
    cols = list(audit.columns)
    cols.remove("system_prompt")
    insert_after = cols.index("prompt") + 1
    cols.insert(insert_after, "system_prompt")
    audit = audit[cols]

    # Write back with utf-8-sig so Excel reads non-ASCII characters
    # (German umlauts, escaped Unicode, etc.) correctly.
    audit.to_csv(AUDIT_CSV, index=False, encoding="utf-8-sig")
    print(f"Wrote {AUDIT_CSV.relative_to(REPO)} ({len(audit)} rows, utf-8-sig)")
    print(f"  SPML rows with system_prompt populated: {n_spml}")
    if n_missing:
        print(f"  WARNING: SPML rows with no match in dataset: {n_missing}")

    # Sanity: confirm user labels were preserved
    n_labeled = audit["audit_label"].notna().sum()
    print(f"  audit_label entries preserved: {n_labeled}")


if __name__ == "__main__":
    main()
