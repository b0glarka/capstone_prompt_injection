"""Recompute aggregate Defense B / C / BIPIA metrics under the v1.21 rubric.

Reads the re-judged CSVs (with v1.21 verdict columns added by
src/defense_b/rejudge_v121.py) and produces a markdown summary with
side-by-side v1.8 baseline and v1.21 numbers. Also handles the
new AMBIGUOUS verdict category that did not exist in v1.8.

AMBIGUOUS handling convention: for hijack-rate computation, treat
AMBIGUOUS as HIJACKED (conservative deployment-oriented choice;
anything not clearly clean is flagged). The AMBIGUOUS rate is also
reported separately so the report can show both views.

Outputs:
- results/aggregate_metrics_v121.md (human-readable summary)
- Console: side-by-side comparison tables
"""
from __future__ import annotations

import sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import binomtest
from sklearn.metrics import cohen_kappa_score, precision_recall_fscore_support, accuracy_score

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from src.metrics import bootstrap_ci, mcnemar  # noqa: E402

RESULTS = REPO / "results"


def to_binary_v121(verdict_series: pd.Series, ambiguous_as: str = "hijacked") -> pd.Series:
    """Map v1.21 verdict (CLEAN/HIJACKED/AMBIGUOUS) to 0/1.

    ambiguous_as: "hijacked" (default, conservative) or "clean" (lenient).
    """
    v = verdict_series.astype(str).str.upper()
    if ambiguous_as == "hijacked":
        return (v != "CLEAN").astype(int)
    elif ambiguous_as == "clean":
        return (v == "HIJACKED").astype(int)
    else:
        raise ValueError(f"ambiguous_as must be 'hijacked' or 'clean', got {ambiguous_as}")


def per_dataset_hijack_rate(df: pd.DataFrame, verdict_col: str, label_col: str = "label") -> pd.DataFrame:
    """Hijack rate on injection rows only, per dataset."""
    rows = []
    for ds, sub in df.groupby("dataset"):
        inj = sub[sub[label_col] == 1]
        if isinstance(verdict_col, tuple):
            # v1.21: convert verdict to binary first
            verdict_text = inj[verdict_col[0]]
            hij = to_binary_v121(verdict_text).sum()
            amb = (verdict_text.astype(str).str.upper() == "AMBIGUOUS").sum()
        else:
            hij = inj[verdict_col].sum()
            amb = 0
        n = len(inj)
        rows.append({
            "dataset": ds,
            "n_injection": n,
            "hijacked": int(hij),
            "hijack_rate": float(hij / n) if n else float("nan"),
            "ambiguous": int(amb),
        })
    return pd.DataFrame(rows)


def cross_judge_kappa(a: pd.Series, b: pd.Series, label_a: str, label_b: str) -> dict:
    """Pairwise kappa + agreement between two binary judge series."""
    mask = a.notna() & b.notna()
    aa = a[mask].astype(int)
    bb = b[mask].astype(int)
    if len(aa) == 0:
        return {"pair": f"{label_a} vs {label_b}", "n": 0, "agreement": float("nan"), "kappa": float("nan")}
    agree = float((aa == bb).mean())
    kappa = float(cohen_kappa_score(aa, bb))
    return {"pair": f"{label_a} vs {label_b}", "n": int(len(aa)), "agreement": agree, "kappa": kappa}


def main() -> None:
    out = []
    out.append("# Aggregate metrics under v1.21 §3.2 rubric")
    out.append("")
    out.append(f"- Date: 2026-05-27")
    out.append(f"- Source CSVs: re-judged 2026-05-26 via `src/defense_b/rejudge_v121.py`")
    out.append(f"- v1.8 baseline: `_local/baseline_v1.8_judge/` (preserved for comparison)")
    out.append(f"- AMBIGUOUS handling: counted as HIJACKED for hijack-rate computation (conservative); ambiguous rate reported separately")
    out.append("")

    # ====================================================================
    # Defense B pilot: 500-row Sonnet
    # ====================================================================
    out.append("## Defense B pilot, Sonnet 4.6 (n=500)")
    out.append("")
    pilot = pd.read_csv(RESULTS / "defense_b_pilot.csv")

    # v1.8 baseline (from `judge_hijacked` column). NaN = judge blocked; treat as 0 for hijack-rate accounting.
    pilot["v18_hijacked"] = pilot["judge_hijacked"].fillna(False).astype(int)
    pilot["v121_hijacked"] = to_binary_v121(pilot["sonnet_verdict_v121"], "hijacked")
    pilot["v121_ambiguous"] = (pilot["sonnet_verdict_v121"].astype(str).str.upper() == "AMBIGUOUS").astype(int)

    inj_pilot = pilot[pilot["label"] == 1]
    out.append(f"On {len(inj_pilot)} injection-class rows in the pilot:")
    out.append("")
    out.append("| Scope | n | v1.8 hijack rate | v1.21 hijack rate (AMB=HIJACKED) | v1.21 AMBIGUOUS rate |")
    out.append("|---|---|---|---|---|")
    for ds in ["deepset", "neuralchemy", "spml"]:
        sub = inj_pilot[inj_pilot["dataset"] == ds]
        n = len(sub)
        h18 = sub["v18_hijacked"].mean()
        h21 = sub["v121_hijacked"].mean()
        amb = sub["v121_ambiguous"].mean()
        out.append(f"| {ds} (injection rows) | {n} | {h18:.4f} | {h21:.4f} | {amb:.4f} |")
    n_all = len(inj_pilot)
    h18_all = inj_pilot["v18_hijacked"].mean()
    h21_all = inj_pilot["v121_hijacked"].mean()
    amb_all = inj_pilot["v121_ambiguous"].mean()
    out.append(f"| **All injection rows** | **{n_all}** | **{h18_all:.4f}** | **{h21_all:.4f}** | **{amb_all:.4f}** |")
    out.append("")

    # Paired McNemar v1.8 vs v1.21 on the same rows
    # Using label=1 as the truth: a "correct" verdict is HIJACKED, "incorrect" is CLEAN
    pred_a = inj_pilot["v18_hijacked"].values
    pred_b = inj_pilot["v121_hijacked"].values
    y_true = np.ones(len(inj_pilot), dtype=int)
    mc = mcnemar(y_true, pred_a, pred_b)
    out.append(f"Paired McNemar v1.8 vs v1.21 (on injection rows, HIJACKED = correct): b={mc['b']}, c={mc['c']}, p={mc['p_value']:.4g}")
    out.append("")

    # ====================================================================
    # Cheap-judge sweep cross-kappa under v1.21
    # ====================================================================
    out.append("## Cheap-judge sweep: cross-judge kappa under v1.21 (n=500)")
    out.append("")
    sweep = pd.read_csv(RESULTS / "defense_b_judge_cost_comparison.csv")
    # Sonnet v1.21 verdicts come from defense_b_pilot.csv via prompt_idx
    sonnet_map = pilot.set_index("prompt_idx")["sonnet_verdict_v121"].to_dict()
    sweep["sonnet_verdict_v121"] = sweep["prompt_idx"].map(sonnet_map)

    sweep["v121_sonnet"] = to_binary_v121(sweep["sonnet_verdict_v121"], "hijacked")
    sweep["v121_haiku"]  = to_binary_v121(sweep["haiku45_verdict_v121"], "hijacked")
    sweep["v121_gpt4m"]  = to_binary_v121(sweep["gpt4mini_verdict_v121"], "hijacked")

    # v1.8 baselines. NaN = judge blocked; treat as 0 for hijack-rate accounting.
    sweep["v18_sonnet"] = sweep["sonnet_hijacked"].fillna(False).astype(int)
    sweep["v18_haiku"]  = sweep["haiku45_hijacked"].fillna(False).astype(int)
    sweep["v18_gpt4m"]  = sweep["gpt4mini_hijacked"].fillna(False).astype(int)

    pairs = [
        ("Sonnet 4.6 vs Haiku 4.5",   "v121_sonnet", "v121_haiku", "v18_sonnet", "v18_haiku"),
        ("Sonnet 4.6 vs GPT-4o-mini", "v121_sonnet", "v121_gpt4m", "v18_sonnet", "v18_gpt4m"),
        ("Haiku 4.5 vs GPT-4o-mini",  "v121_haiku",  "v121_gpt4m", "v18_haiku",  "v18_gpt4m"),
    ]
    out.append("| Pair | n | v1.8 agreement | v1.8 kappa | v1.21 agreement | v1.21 kappa |")
    out.append("|---|---|---|---|---|---|")
    for name, ac, bc, ac8, bc8 in pairs:
        r8 = cross_judge_kappa(sweep[ac8], sweep[bc8], "a", "b")
        r21 = cross_judge_kappa(sweep[ac],  sweep[bc],  "a", "b")
        out.append(f"| {name} | {r21['n']} | {r8['agreement']:.3f} | {r8['kappa']:.3f} | {r21['agreement']:.3f} | {r21['kappa']:.3f} |")
    out.append("")

    # Three-way agreement
    triple18 = ((sweep["v18_sonnet"] == sweep["v18_haiku"]) & (sweep["v18_haiku"] == sweep["v18_gpt4m"])).mean()
    triple21 = ((sweep["v121_sonnet"] == sweep["v121_haiku"]) & (sweep["v121_haiku"] == sweep["v121_gpt4m"])).mean()
    out.append(f"Three-judge agreement: v1.8 = {triple18:.3f}, v1.21 = {triple21:.3f}")
    out.append("")

    # ====================================================================
    # Defense C combined pilot
    # ====================================================================
    out.append("## Defense C combined (n=500, pilot)")
    out.append("")
    # Load Defense A predictions on the same prompts
    da = pd.read_csv(RESULTS / "defense_a_full_eval_set.csv")
    # Keep only the rows that exist in the pilot
    da_pilot = da[da["prompt_idx"].isin(pilot["prompt_idx"])][
        ["prompt_idx", "deberta_pred_label_id", "pg2_pred_label_id"]
    ]
    cmb = pilot.merge(da_pilot, on="prompt_idx", how="left")
    # OR-gate of DeBERTa + Sonnet judge
    cmb["c_v18"] = ((cmb["deberta_pred_label_id"] == 1) | (cmb["v18_hijacked"] == 1)).astype(int)
    cmb["c_v121"] = ((cmb["deberta_pred_label_id"] == 1) | (cmb["v121_hijacked"] == 1)).astype(int)

    y = cmb["label"].astype(int).values
    out.append("| Defense | F1 (v1.8) | F1 (v1.21) | Precision (v1.21) | Recall (v1.21) | Acc (v1.21) |")
    out.append("|---|---|---|---|---|---|")
    # Defense A alone (DeBERTa)
    da_pred = cmb["deberta_pred_label_id"].fillna(0).astype(int).values
    p, r, f, _ = precision_recall_fscore_support(y, da_pred, average="binary", pos_label=1, zero_division=0)
    out.append(f"| Defense A (DeBERTa) | {f:.3f} | {f:.3f} (unchanged; A is independent of judge) | {p:.3f} | {r:.3f} | {accuracy_score(y, da_pred):.3f} |")
    # Defense B v1.8 vs v1.21
    p18, r18, f18, _ = precision_recall_fscore_support(y, cmb["v18_hijacked"], average="binary", pos_label=1, zero_division=0)
    p21, r21, f21, _ = precision_recall_fscore_support(y, cmb["v121_hijacked"], average="binary", pos_label=1, zero_division=0)
    out.append(f"| Defense B (Sonnet judge) | {f18:.3f} | {f21:.3f} | {p21:.3f} | {r21:.3f} | {accuracy_score(y, cmb['v121_hijacked']):.3f} |")
    # Defense C
    p18c, r18c, f18c, _ = precision_recall_fscore_support(y, cmb["c_v18"], average="binary", pos_label=1, zero_division=0)
    p21c, r21c, f21c, _ = precision_recall_fscore_support(y, cmb["c_v121"], average="binary", pos_label=1, zero_division=0)
    out.append(f"| Defense C (A OR B) | {f18c:.3f} | {f21c:.3f} | {p21c:.3f} | {r21c:.3f} | {accuracy_score(y, cmb['c_v121']):.3f} |")
    out.append("")

    # Defense C bootstrap CI under v1.21
    ci = bootstrap_ci(
        cmb["label"].astype(int).values,
        cmb["c_v121"].astype(int).values,
        n_iter=1000, seed=42,
    )
    out.append(f"Defense C v1.21 bootstrap 95% CIs: F1 = {f21c:.3f} [{ci['f1'][0]:.3f}, {ci['f1'][1]:.3f}], precision = {p21c:.3f} [{ci['precision'][0]:.3f}, {ci['precision'][1]:.3f}], recall = {r21c:.3f} [{ci['recall'][0]:.3f}, {ci['recall'][1]:.3f}]")
    out.append("")

    # Paired McNemar Defense A vs Defense C v1.21
    mc_ac = mcnemar(y, da_pred, cmb["c_v121"].astype(int).values)
    out.append(f"Paired McNemar Defense A vs Defense C (v1.21): b={mc_ac['b']}, c={mc_ac['c']}, p={mc_ac['p_value']:.4g}")
    out.append("")

    # ====================================================================
    # BIPIA email-QA under v1.21
    # ====================================================================
    out.append("## BIPIA email-QA under v1.21 (n=800, 750 attacks + 50 controls)")
    out.append("")
    bipia = pd.read_csv(RESULTS / "bipia_email_qa_results.csv")
    bipia["v121_hijacked"] = to_binary_v121(bipia["sonnet_verdict_v121"], "hijacked")
    bipia["v121_ambiguous"] = (bipia["sonnet_verdict_v121"].astype(str).str.upper() == "AMBIGUOUS").astype(int)
    bipia["v18_hijacked"] = bipia["judge_hijacked"].fillna(False).astype(int)

    attacks = bipia[bipia["is_attack"] == 1]
    controls = bipia[bipia["is_attack"] == 0]

    # Defense A: query-only and full-prompt
    n_attacks = len(attacks)
    n_controls = len(controls)
    out.append(f"On {n_attacks} attack rows and {n_controls} clean controls:")
    out.append("")
    out.append("| Defense | v1.8 attack success | v1.21 attack success | v1.8 FAR | v1.21 FAR |")
    out.append("|---|---|---|---|---|")
    # Defense A query-only is unchanged
    da_qo_atk = 1 - attacks["deberta_query_only_flagged"].mean()
    da_qo_far = controls["deberta_query_only_flagged"].mean()
    da_fp_atk = 1 - attacks["deberta_full_prompt_flagged"].mean()
    da_fp_far = controls["deberta_full_prompt_flagged"].mean()
    pg2_fp_atk = 1 - attacks["pg2_full_prompt_flagged"].mean()
    pg2_fp_far = controls["pg2_full_prompt_flagged"].mean()
    out.append(f"| Defense A: DeBERTa (query only) | {da_qo_atk:.4f} | {da_qo_atk:.4f} (A unchanged) | {da_qo_far:.4f} | {da_qo_far:.4f} |")
    out.append(f"| Defense A: DeBERTa (full prompt) | {da_fp_atk:.4f} | {da_fp_atk:.4f} (A unchanged) | {da_fp_far:.4f} | {da_fp_far:.4f} |")
    out.append(f"| Defense A: PG2 (full prompt) | {pg2_fp_atk:.4f} | {pg2_fp_atk:.4f} (A unchanged) | {pg2_fp_far:.4f} | {pg2_fp_far:.4f} |")
    # Judge alone
    j18_atk = 1 - attacks["v18_hijacked"].mean()
    j21_atk = 1 - attacks["v121_hijacked"].mean()
    j18_far = controls["v18_hijacked"].mean()
    j21_far = controls["v121_hijacked"].mean()
    out.append(f"| Defense B: Sonnet judge | {j18_atk:.4f} | {j21_atk:.4f} | {j18_far:.4f} | {j21_far:.4f} |")
    # Defense C OR-gate (DeBERTa full + judge)
    attacks_c18 = ((attacks["deberta_full_prompt_flagged"] == 1) | (attacks["v18_hijacked"] == 1)).astype(int)
    attacks_c21 = ((attacks["deberta_full_prompt_flagged"] == 1) | (attacks["v121_hijacked"] == 1)).astype(int)
    controls_c18 = ((controls["deberta_full_prompt_flagged"] == 1) | (controls["v18_hijacked"] == 1)).astype(int)
    controls_c21 = ((controls["deberta_full_prompt_flagged"] == 1) | (controls["v121_hijacked"] == 1)).astype(int)
    c18_atk = 1 - attacks_c18.mean()
    c21_atk = 1 - attacks_c21.mean()
    c18_far = controls_c18.mean()
    c21_far = controls_c21.mean()
    out.append(f"| Defense C: DeBERTa (full) + judge | {c18_atk:.4f} | {c21_atk:.4f} | {c18_far:.4f} | {c21_far:.4f} |")
    out.append("")

    amb_atk = attacks["v121_ambiguous"].mean()
    amb_far = controls["v121_ambiguous"].mean()
    out.append(f"v1.21 AMBIGUOUS rate: {amb_atk:.4f} on attacks, {amb_far:.4f} on controls.")
    out.append("")

    # Per-attack-category breakdown for Defense C under v1.21
    out.append("### BIPIA per-category attack success (Defense C under v1.21)")
    out.append("")
    out.append("| Category | n | v1.8 Defense C | v1.21 Defense C |")
    out.append("|---|---|---|---|")
    for cat, sub in attacks.groupby("attack_category"):
        n = len(sub)
        sub_c18 = ((sub["deberta_full_prompt_flagged"] == 1) | (sub["v18_hijacked"] == 1)).astype(int)
        sub_c21 = ((sub["deberta_full_prompt_flagged"] == 1) | (sub["v121_hijacked"] == 1)).astype(int)
        c18 = 1 - sub_c18.mean()
        c21 = 1 - sub_c21.mean()
        out.append(f"| {cat} | {n} | {c18:.2f} | {c21:.2f} |")
    out.append("")

    # ====================================================================
    # GPT-4o sensitivity check
    # ====================================================================
    out.append("## GPT-4o judge sensitivity, deepset role-play (n=8)")
    out.append("")
    sens = pd.read_csv(RESULTS / "defense_b_judge_sensitivity_deepset.csv")
    sens["v121_gpt4o_hijacked"] = to_binary_v121(sens["gpt4o_verdict_v121"], "hijacked")
    n_sens = len(sens)
    out.append(f"Of {n_sens} cases:")
    out.append("")
    out.append(f"- v1.8: Claude flagged {sens['claude_hijacked'].sum()}/{n_sens}; GPT-4o flagged {sens['gpt4o_hijacked'].sum()}/{n_sens}; agreement {sens['agree'].sum()}/{n_sens}.")
    # v1.21: Claude verdict is the Sonnet v1.21 from the pilot; GPT-4o v1.21 from sensitivity CSV
    claude_v121_lookup = pilot.set_index("prompt_idx")["v121_hijacked"].to_dict()
    sens["v121_claude_hijacked"] = sens["prompt_idx"].map(claude_v121_lookup).fillna(0).astype(int)
    v121_agree = (sens["v121_claude_hijacked"] == sens["v121_gpt4o_hijacked"]).sum()
    out.append(f"- v1.21: Claude flagged {sens['v121_claude_hijacked'].sum()}/{n_sens}; GPT-4o flagged {sens['v121_gpt4o_hijacked'].sum()}/{n_sens}; agreement {v121_agree}/{n_sens}.")
    out.append("")

    # ====================================================================
    # Write output
    # ====================================================================
    out_path = RESULTS / "aggregate_metrics_v121.md"
    out_path.write_text("\n".join(out), encoding="utf-8")
    print(f"Wrote {out_path.relative_to(REPO)}")
    print()
    print("\n".join(out))


if __name__ == "__main__":
    main()
