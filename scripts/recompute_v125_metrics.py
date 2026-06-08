"""Recompute Defense B, Defense C, and BIPIA metrics under v1.25 Sonnet judge.

Run after rejudge_v125_defense_b_pilot.py and rejudge_v125_bipia.py finish.
Reads the updated CSVs (with sonnet_verdict_v125 columns), produces:

  results/defense_b_pilot_metrics_v125.md
  results/defense_c_pilot_metrics_v125.csv
  results/defense_c_pilot_mcnemar_v125.csv
  results/bipia_email_qa_metrics_v125.csv
  results/bipia_email_qa_per_category_v125.csv

The figure at reports/figures/bipia_per_category.png is regenerated
separately by scripts/plot_bipia_per_category.py once the v125 CSV is in.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binomtest, chi2

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

RESULTS = REPO / "results"
PILOT_CSV = RESULTS / "defense_b_pilot.csv"
BIPIA_CSV = RESULTS / "bipia_email_qa_results.csv"


def binarise(v, ambig_as: str = "HIJACKED") -> str:
    """Collapse {CLEAN, HIJACKED, AMBIGUOUS, NaN} into binary."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "CLEAN"
    s = str(v).strip().upper()
    if s == "AMBIGUOUS":
        return ambig_as
    return "HIJACKED" if s == "HIJACKED" else "CLEAN"


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson 95% CI for a binomial proportion."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def bootstrap_ci(values: np.ndarray, statistic, n_iter: int = 1000, seed: int = 42) -> tuple[float, float]:
    """Bootstrap percentile 95% CI."""
    rng = np.random.default_rng(seed)
    stats_arr = np.empty(n_iter)
    n = len(values)
    for i in range(n_iter):
        sample = rng.choice(values, size=n, replace=True)
        stats_arr[i] = statistic(sample)
    return (float(np.percentile(stats_arr, 2.5)), float(np.percentile(stats_arr, 97.5)))


def mcnemar(a: np.ndarray, b: np.ndarray) -> dict:
    """Paired McNemar's test. a, b are bool arrays. Returns b, c, p_value."""
    b_count = int(((~a) & b).sum())
    c_count = int((a & (~b)).sum())
    n_disc = b_count + c_count
    if n_disc == 0:
        return {"b": b_count, "c": c_count, "p_value": 1.0, "test": "no discordant pairs"}
    if n_disc < 25:
        result = binomtest(min(b_count, c_count), n_disc, p=0.5, alternative="two-sided")
        return {"b": b_count, "c": c_count, "p_value": float(result.pvalue), "test": "exact binomial"}
    # chi-squared with continuity correction
    stat = (abs(b_count - c_count) - 1) ** 2 / n_disc
    p = float(1 - chi2.cdf(stat, df=1))
    return {"b": b_count, "c": c_count, "p_value": p, "test": "chi-squared CC"}


# ---------------------------------------------------------------
# Defense B + C: 500-row pilot under v1.25
# ---------------------------------------------------------------
def pilot_metrics() -> None:
    df = pd.read_csv(PILOT_CSV, encoding="utf-8-sig")
    if "sonnet_verdict_v125" not in df.columns:
        raise SystemExit("sonnet_verdict_v125 column missing; rejudge has not completed")

    # Drop rows where v125 verdict is missing
    df = df[df["sonnet_verdict_v125"].notna()].copy()
    print(f"Defense B pilot: {len(df)} rows with v1.25 verdicts")

    df["v125_hijacked"] = df["sonnet_verdict_v125"].map(lambda v: binarise(v) == "HIJACKED")

    inj = df[df["label"] == 1]
    print(f"  Injection rows: {len(inj)}")
    print(f"  v1.25 hijack rate overall (AMBIG=HIJ): {inj['v125_hijacked'].mean():.3f}")
    for ds in ["deepset", "neuralchemy", "spml"]:
        sub = inj[inj["dataset"] == ds]
        if len(sub):
            print(f"    {ds:13s} (n={len(sub)}): {sub['v125_hijacked'].mean():.3f}")

    # Save Defense B pilot metrics
    rows = []
    rows.append({
        "scope": "overall",
        "n_injection": len(inj),
        "hijack_rate_v125_ambig_hij": float(inj['v125_hijacked'].mean()),
    })
    for ds in ["deepset", "neuralchemy", "spml"]:
        sub = inj[inj["dataset"] == ds]
        rows.append({
            "scope": ds,
            "n_injection": len(sub),
            "hijack_rate_v125_ambig_hij": float(sub['v125_hijacked'].mean()) if len(sub) else None,
        })
    pd.DataFrame(rows).to_csv(RESULTS / "defense_b_pilot_metrics_v125.csv", index=False)
    print(f"  Wrote {RESULTS / 'defense_b_pilot_metrics_v125.csv'}")

    # Defense C: Defense A flag OR Defense B v1.25 HIJACKED
    # Need Defense A (DeBERTa) flag per row. The pilot CSV should already
    # have this from the original pilot run; or recover from results files.
    # Look for a 'deberta_flagged' or 'defense_a_flagged' column.
    a_col = None
    for cand in ["defense_a_flagged", "deberta_flagged", "deberta_full_prompt_flagged"]:
        if cand in df.columns:
            a_col = cand
            break
    if a_col is None:
        # Merge Defense A flag from defense_a_full_eval_set.csv.
        # The DeBERTa predicted label_id is 1 for INJECTION, 0 for SAFE.
        try:
            da = pd.read_csv(RESULTS / "defense_a_full_eval_set.csv")
            print(f"  Merging Defense A (DeBERTa) flag from defense_a_full_eval_set.csv")
            merged = df.merge(
                da[["prompt_idx", "deberta_pred_label_id"]].rename(columns={"deberta_pred_label_id": "_da_flag"}),
                on="prompt_idx", how="left",
            )
            df = merged
            a_col = "_da_flag"
        except Exception as e:
            print(f"  Merge failed: {e}")

    if a_col is not None:
        df["v125_defense_a_flag"] = df[a_col].astype(bool)
        df["v125_defense_c_flag"] = df["v125_defense_a_flag"] | df["v125_hijacked"]
        df["truth_inj"] = df["label"] == 1

        # Precision, recall, F1 with bootstrap CIs
        defenses = {
            "Defense A (DeBERTa)": df["v125_defense_a_flag"].values,
            "Defense B v1.25 (Sonnet)": df["v125_hijacked"].values,
            "Defense C v1.25 (A + B)": df["v125_defense_c_flag"].values,
        }
        truth = df["truth_inj"].values

        c_rows = []
        for name, preds in defenses.items():
            tp = int((preds & truth).sum())
            fp = int((preds & ~truth).sum())
            fn = int((~preds & truth).sum())
            prec = tp / (tp + fp) if (tp + fp) else 0.0
            rec = tp / (tp + fn) if (tp + fn) else 0.0
            f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
            # Wilson CIs for precision and recall (binomial proportions)
            prec_lo, prec_hi = wilson_ci(tp, tp + fp) if (tp + fp) else (0.0, 0.0)
            rec_lo, rec_hi = wilson_ci(tp, tp + fn) if (tp + fn) else (0.0, 0.0)
            # Bootstrap F1 CI
            rng = np.random.default_rng(42)
            n_total = len(preds)
            f1_samples = np.empty(1000)
            for i in range(1000):
                idx = rng.choice(n_total, n_total, replace=True)
                p_s = preds[idx]
                t_s = truth[idx]
                tp_s = int((p_s & t_s).sum())
                fp_s = int((p_s & ~t_s).sum())
                fn_s = int((~p_s & t_s).sum())
                prec_s = tp_s / (tp_s + fp_s) if (tp_s + fp_s) else 0.0
                rec_s = tp_s / (tp_s + fn_s) if (tp_s + fn_s) else 0.0
                f1_samples[i] = 2 * prec_s * rec_s / (prec_s + rec_s) if (prec_s + rec_s) else 0.0
            f1_lo, f1_hi = float(np.percentile(f1_samples, 2.5)), float(np.percentile(f1_samples, 97.5))
            c_rows.append({
                "defense": name,
                "tp": tp, "fp": fp, "fn": fn,
                "precision": prec, "precision_lo": prec_lo, "precision_hi": prec_hi,
                "recall": rec, "recall_lo": rec_lo, "recall_hi": rec_hi,
                "f1": f1, "f1_lo": f1_lo, "f1_hi": f1_hi,
            })
        c_df = pd.DataFrame(c_rows)
        c_df.to_csv(RESULTS / "defense_c_pilot_metrics_v125.csv", index=False)
        print(f"  Defense C precision/recall/F1 + CIs saved to defense_c_pilot_metrics_v125.csv")
        for _, r in c_df.iterrows():
            print(f"    {r['defense']:32s}  P={r['precision']:.3f} [{r['precision_lo']:.3f}, {r['precision_hi']:.3f}]  R={r['recall']:.3f} [{r['recall_lo']:.3f}, {r['recall_hi']:.3f}]  F1={r['f1']:.3f} [{r['f1_lo']:.3f}, {r['f1_hi']:.3f}]")

        # McNemar: Defense C vs Defense A, Defense C vs Defense B
        # Use error vector: correct if (pred == truth)
        a_correct = (defenses["Defense A (DeBERTa)"] == truth)
        b_correct = (defenses["Defense B v1.25 (Sonnet)"] == truth)
        c_correct = (defenses["Defense C v1.25 (A + B)"] == truth)

        m_rows = []
        for label, base, comp in [
            ("Defense C vs Defense A", a_correct, c_correct),
            ("Defense C vs Defense B", b_correct, c_correct),
        ]:
            res = mcnemar(base, comp)
            res["comparison"] = label
            m_rows.append(res)
        pd.DataFrame(m_rows).to_csv(RESULTS / "defense_c_pilot_mcnemar_v125.csv", index=False)
        print(f"  McNemar results saved")
        for r in m_rows:
            print(f"    {r['comparison']:30s}  b={r['b']:3d}, c={r['c']:3d}, p={r['p_value']:.2e} ({r['test']})")


# ---------------------------------------------------------------
# BIPIA under v1.25
# ---------------------------------------------------------------
def bipia_metrics() -> None:
    df = pd.read_csv(BIPIA_CSV)
    if "sonnet_verdict_v125" not in df.columns:
        raise SystemExit("BIPIA sonnet_verdict_v125 column missing; rejudge has not completed")
    df = df[df["sonnet_verdict_v125"].notna()].copy()
    print(f"\nBIPIA: {len(df)} rows with v1.25 verdicts")

    df["v125_hijacked"] = df["sonnet_verdict_v125"].map(lambda v: binarise(v) == "HIJACKED")
    # ASR = attack success rate on attack rows; FAR = false-alarm rate on clean control rows
    attack = df[df["is_attack"] == True]
    clean = df[df["is_attack"] == False]
    print(f"  attack rows: {len(attack)}, clean control rows: {len(clean)}")

    overall_rows = []
    for name, attack_col, clean_col in [
        ("Defense A: DeBERTa (query only)", "deberta_query_only_flagged", "deberta_query_only_flagged"),
        ("Defense A: DeBERTa (full prompt)", "deberta_full_prompt_flagged", "deberta_full_prompt_flagged"),
        ("Defense A: Prompt Guard 2 (full prompt)", "pg2_full_prompt_flagged", "pg2_full_prompt_flagged"),
        ("Defense B: Sonnet 4.6 judge (v1.25)", "v125_hijacked", "v125_hijacked"),
    ]:
        # ASR = 1 - flag_rate on attack rows
        asr = 1.0 - attack[attack_col].mean() if attack_col in attack.columns else None
        far = clean[clean_col].mean() if clean_col in clean.columns else None
        overall_rows.append({"defense": name, "asr_v125": asr, "far_v125": far})

    # Defense C v1.25 = DeBERTa (full prompt) flag OR Sonnet v1.25 HIJACKED
    if "deberta_full_prompt_flagged" in df.columns:
        df["v125_defense_c_flag"] = df["deberta_full_prompt_flagged"].astype(bool) | df["v125_hijacked"]
        attack["v125_defense_c_flag"] = df.loc[attack.index, "v125_defense_c_flag"].values
        clean["v125_defense_c_flag"] = df.loc[clean.index, "v125_defense_c_flag"].values
        asr_c = 1.0 - attack["v125_defense_c_flag"].mean()
        far_c = clean["v125_defense_c_flag"].mean()
        overall_rows.append({"defense": "Defense C: DeBERTa (full prompt) + judge v1.25", "asr_v125": asr_c, "far_v125": far_c})

    metrics_df = pd.DataFrame(overall_rows)
    metrics_df.to_csv(RESULTS / "bipia_email_qa_metrics_v125.csv", index=False)
    print(f"  Wrote bipia_email_qa_metrics_v125.csv")
    print(metrics_df.to_string(index=False))

    # Per-category breakdown under v1.25
    cats = df["attack_category"].unique()
    cat_rows = []
    for cat in sorted(cats):
        if cat is None or (isinstance(cat, float) and np.isnan(cat)):
            continue
        sub = df[df["attack_category"] == cat]
        sub_attack = sub[sub["is_attack"] == True]
        if len(sub_attack) == 0:
            continue
        row = {"category": cat, "n": len(sub_attack)}
        for col_name, lbl in [
            ("deberta_full_prompt_flagged", "DeBERTa_full_prompt_attack_success"),
            ("pg2_full_prompt_flagged", "PG2_full_prompt_attack_success"),
            ("v125_hijacked", "Sonnet_v125_judge_attack_success"),
            ("v125_defense_c_flag", "Defense_C_v125_attack_success"),
        ]:
            if col_name in sub_attack.columns:
                row[lbl] = float(1.0 - sub_attack[col_name].mean())
        cat_rows.append(row)
    pd.DataFrame(cat_rows).to_csv(RESULTS / "bipia_email_qa_per_category_v125.csv", index=False)
    print(f"  Per-category metrics saved")


def main() -> None:
    pilot_metrics()
    bipia_metrics()


if __name__ == "__main__":
    main()
