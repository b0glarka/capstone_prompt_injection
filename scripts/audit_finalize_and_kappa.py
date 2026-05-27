"""Finalise the audit and compute kappa / noise-rate / ambiguity metrics.

Steps:
1. Flip ranks 39 and 62 from audit_label=1 to audit_label=0 for v1.22 §3.1
   consistency with rank 59. All three are content-policy borderline cases
   (harmful-content requests without Step 4 patterns); under v1.22 §3.1 they
   are BENIGN.
2. Compute Cohen's kappa (audit vs dataset gold labels) with bootstrap CI:
   overall and per dataset.
3. Compute per-dataset disagreement rate (proxy for label noise floor).
4. Compute ambiguity rate per dataset and per language.
5. Cross-tab disagreement by language for the cross-language finding.
6. Print everything in markdown-friendly form for direct paste into the
   label_audit_report.

Saves the updated audit CSV back to the same path.
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score

REPO = Path(__file__).resolve().parents[1]
PATH = REPO / "results" / "label_audit_sample_disagreement_sorted_post_audit.csv"

# Final flips for v1.22 §3.1 consistency
RANK39_NEW_NOTE = (
    "Definition-boundary case (content policy, not §3.1 injection). The prompt requests "
    "harmful-content output (insider-trading analysis) but uses no §3.1 Step 4 pattern. "
    "Per op-defs §2.3 and the §3.1 scope note (v1.22), content-policy violations not "
    "driven by an injection mechanism are not injection attempts. Audit label flipped "
    "1 -> 0 on 2026-05-27 to align with rank 59 (analogous coercion-message case also "
    "labeled BENIGN). The ambiguity flag stays TRUE because the row sits on the "
    "harm-vs-injection boundary."
)
RANK62_NEW_NOTE = (
    "Definition-boundary case (content policy, not §3.1 injection). The prompt requests "
    "step-by-step instructions for logging into a corporate network. No §3.1 Step 4 "
    "pattern (no override, persona, authority, extraction, encoding, or carrier). "
    "Per op-defs §2.3 and the §3.1 scope note (v1.22), content-policy violations not "
    "driven by an injection mechanism are not injection attempts. Audit label flipped "
    "1 -> 0 on 2026-05-27 to align with rank 59 and rank 39 (both content-policy "
    "boundary cases). The ambiguity flag stays TRUE because the row sits on the "
    "harm-vs-injection boundary."
)


def bootstrap_kappa_ci(y1, y2, n_iter=1000, seed=42):
    rng = np.random.default_rng(seed)
    n = len(y1)
    samples = []
    for _ in range(n_iter):
        idx = rng.integers(0, n, n)
        try:
            k = cohen_kappa_score(y1[idx], y2[idx])
            samples.append(k)
        except Exception:
            continue
    if not samples:
        return float("nan"), float("nan")
    samples = np.array(samples)
    return float(np.percentile(samples, 2.5)), float(np.percentile(samples, 97.5))


def main() -> None:
    df = pd.read_csv(PATH, encoding="utf-8-sig")
    print(f"Loaded {len(df)} rows.")

    # ===== Step 1: Flip ranks 39 and 62 =====
    for rank, new_note in [(39, RANK39_NEW_NOTE), (62, RANK62_NEW_NOTE)]:
        mask = df["disagreement_rank"] == rank
        old_label = df.loc[mask, "audit_label"].iloc[0]
        df.loc[mask, "audit_label"] = 0
        df.loc[mask, "notes"] = new_note
        print(f"  rank {rank}: audit_label {old_label} -> 0; note updated")

    df.to_csv(PATH, index=False, encoding="utf-8-sig")
    print(f"Wrote {PATH.relative_to(REPO)}")
    print()

    # ===== Step 2-5: Compute metrics =====
    labeled = df[df["audit_label"].notna()].copy()
    labeled["al"] = labeled["audit_label"].astype(float).astype(int)
    labeled["dl"] = labeled["dataset_label"].astype(int)
    labeled["amb"] = labeled["ambiguous"].astype(str).str.lower().isin(["true", "t", "1", "yes"])

    print("=" * 70)
    print("RESULTS")
    print("=" * 70)

    print()
    print("## Overall agreement and Cohen's kappa")
    print()
    n = len(labeled)
    agree = (labeled["al"] == labeled["dl"]).sum()
    kappa = cohen_kappa_score(labeled["al"].values, labeled["dl"].values)
    lo, hi = bootstrap_kappa_ci(labeled["al"].values, labeled["dl"].values)
    print(f"| Scope | n | Agreement | Disagreements | Cohen's kappa [95% CI] |")
    print(f"|---|---|---|---|---|")
    print(f"| Overall | {n} | {agree}/{n} = {agree/n:.1%} | {n-agree} | {kappa:.3f} [{lo:.3f}, {hi:.3f}] |")

    for ds in ["deepset", "neuralchemy", "spml"]:
        sub = labeled[labeled["dataset"] == ds]
        n_ds = len(sub)
        agree_ds = (sub["al"] == sub["dl"]).sum()
        kappa_ds = cohen_kappa_score(sub["al"].values, sub["dl"].values)
        lo_ds, hi_ds = bootstrap_kappa_ci(sub["al"].values, sub["dl"].values)
        print(f"| {ds} | {n_ds} | {agree_ds}/{n_ds} = {agree_ds/n_ds:.1%} | {n_ds-agree_ds} | {kappa_ds:.3f} [{lo_ds:.3f}, {hi_ds:.3f}] |")

    print()
    print("## Ambiguity rate")
    print()
    print("| Scope | n labeled | Ambiguous=TRUE | Ambiguity rate |")
    print("|---|---|---|---|")
    amb_all = labeled["amb"].sum()
    print(f"| Overall | {n} | {amb_all} | {amb_all/n:.1%} |")
    for ds in ["deepset", "neuralchemy", "spml"]:
        sub = labeled[labeled["dataset"] == ds]
        amb_ds = sub["amb"].sum()
        print(f"| {ds} | {len(sub)} | {amb_ds} | {amb_ds/len(sub):.1%} |")

    print()
    print("## Disagreement rows (final list)")
    print()
    disagree = labeled[labeled["al"] != labeled["dl"]][
        ["disagreement_rank", "prompt_idx", "dataset", "language", "dataset_label", "al", "amb"]
    ].copy()
    print(f"Total disagreements: {len(disagree)} of {n} ({len(disagree)/n:.1%})")
    print()
    print("| Rank | prompt_idx | Dataset | Language | Dataset label | Audit label | Ambiguous |")
    print("|---|---|---|---|---|---|---|")
    for _, row in disagree.iterrows():
        print(f"| {int(row['disagreement_rank'])} | {row['prompt_idx']} | {row['dataset']} | {row['language']} | {int(row['dataset_label'])} | {int(row['al'])} | {row['amb']} |")

    print()
    print("## Cross-language agreement")
    print()
    labeled["is_en"] = labeled["language"] == "en"
    print("| Subgroup | n | Agreement | Ambiguity rate |")
    print("|---|---|---|---|")
    for is_en, sub in labeled.groupby("is_en"):
        n_sub = len(sub)
        agree_sub = (sub["al"] == sub["dl"]).sum()
        amb_sub = sub["amb"].sum()
        label = "English" if is_en else "Non-English"
        print(f"| {label} | {n_sub} | {agree_sub}/{n_sub} = {agree_sub/n_sub:.1%} | {amb_sub}/{n_sub} = {amb_sub/n_sub:.1%} |")

    # Defense A catch rate on auditor-confirmed injections by language
    print()
    print("## Defense A catch rate on auditor-confirmed injections by language")
    print()
    injections = labeled[labeled["al"] == 1]
    print("| Subgroup | n | DeBERTa caught | PG2 caught |")
    print("|---|---|---|---|")
    for is_en, sub in injections.groupby(injections["language"].eq("en")):
        n_sub = len(sub)
        db = (sub["deberta_pred_label_id"] == 1).sum()
        pg = (sub["pg2_pred_label_id"] == 1).sum()
        label = "English" if is_en else "Non-English"
        print(f"| {label} | {n_sub} | {db}/{n_sub} = {db/n_sub:.1%} | {pg}/{n_sub} = {pg/n_sub:.1%} |")


if __name__ == "__main__":
    main()
