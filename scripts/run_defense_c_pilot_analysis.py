"""Defense C combined pipeline analysis on the 500-row pilot.

Defense C is defined as the OR-combination of Defense A (input classifier) and
Defense B (output-side LLM-as-judge): a prompt is flagged if Defense A says
INJECTION or if Defense B's judge says the agent's response is HIJACKED.

Per plan v2 Section 5, this is the "input gate then output judge" pipeline,
which is mathematically equivalent to OR-combination when B runs on everything
(since A_flag OR B_flag = A_flag OR (A_passes AND B_flag) when A_flag and
A_passes are complements).

This script uses ONLY existing pilot data; no new API calls. It computes
Defense C metrics on the 500-row pilot subset and runs paired McNemar
comparisons against Defense A alone and Defense B alone.

Defense A variants tested as the input-stage of Defense C:
  - DeBERTa alone
  - PG2 alone
  - DeBERTa + PG2 ensemble (OR-gate)

Outputs:
  results/defense_c_pilot_metrics.csv
  results/defense_c_pilot_mcnemar.csv
  results/defense_c_pilot.md
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from src.metrics import bootstrap_ci, headline_metrics, mcnemar

RES = REPO / "results"


def main() -> None:
    # Load pilot data (has judge_hijacked) and full-eval-set Defense A predictions
    pilot = pd.read_csv(RES / "defense_b_pilot.csv")
    defense_a = pd.read_csv(RES / "defense_a_full_eval_set.csv")[
        ["prompt_idx", "deberta_pred_label_id", "pg2_pred_label_id"]
    ]
    df = pilot.merge(defense_a, on="prompt_idx", how="left")
    assert df["deberta_pred_label_id"].notna().all(), "missing DeBERTa predictions for some pilot rows"
    print(f"pilot rows merged with Defense A: {len(df)}")

    # Build per-defense flag columns. All booleans; 1 = flagged as injection / hijacked.
    df["A_deberta"]   = (df["deberta_pred_label_id"] == 1).astype(int)
    df["A_pg2"]       = (df["pg2_pred_label_id"] == 1).astype(int)
    df["A_ensemble"]  = ((df["A_deberta"] == 1) | (df["A_pg2"] == 1)).astype(int)
    df["B_judge"]     = (df["judge_hijacked"] == True).astype(int)
    # Defense B can also be no-decision (judge_blocked) but in the pilot it didn't happen

    # Three Defense C variants, paired with each Defense A choice
    df["C_deberta_plus_B"]  = ((df["A_deberta"]  == 1) | (df["B_judge"] == 1)).astype(int)
    df["C_pg2_plus_B"]      = ((df["A_pg2"]      == 1) | (df["B_judge"] == 1)).astype(int)
    df["C_ensemble_plus_B"] = ((df["A_ensemble"] == 1) | (df["B_judge"] == 1)).astype(int)

    defenses = {
        "A: DeBERTa alone":         "A_deberta",
        "A: PG2 alone":             "A_pg2",
        "A: DeBERTa+PG2 ensemble":  "A_ensemble",
        "B: Sonnet judge alone":    "B_judge",
        "C: DeBERTa + B":           "C_deberta_plus_B",
        "C: PG2 + B":               "C_pg2_plus_B",
        "C: Ensemble + B":          "C_ensemble_plus_B",
    }

    # Headline metrics with bootstrap CIs, per defense, per scope
    scopes = [("overall", df)] + [(ds, df[df["dataset"] == ds]) for ds in ["deepset", "neuralchemy", "spml"]]
    rows = []
    for name, pred_col in defenses.items():
        for scope_name, scope in scopes:
            y = scope["label"].values
            yp = scope[pred_col].values
            m = headline_metrics(y, yp)
            ci = bootstrap_ci(y, yp, n_iter=1000, seed=42)
            row = {"defense": name, "scope": scope_name, "n": len(scope), **m}
            for k, (lo, hi) in ci.items():
                row[f"{k}_lo"] = round(lo, 4)
                row[f"{k}_hi"] = round(hi, 4)
            rows.append(row)
    metrics_df = pd.DataFrame(rows)
    for c in ["accuracy", "precision", "recall", "f1"]:
        if c in metrics_df.columns:
            metrics_df[c] = metrics_df[c].round(4)
    metrics_df.to_csv(RES / "defense_c_pilot_metrics.csv", index=False)

    # Paired McNemar: each C variant vs its A counterpart and vs B alone
    pairs = [
        ("C: DeBERTa + B",   "A_deberta",  "C_deberta_plus_B"),
        ("C: DeBERTa + B",   "B_judge",    "C_deberta_plus_B"),
        ("C: PG2 + B",       "A_pg2",      "C_pg2_plus_B"),
        ("C: PG2 + B",       "B_judge",    "C_pg2_plus_B"),
        ("C: Ensemble + B",  "A_ensemble", "C_ensemble_plus_B"),
        ("C: Ensemble + B",  "B_judge",    "C_ensemble_plus_B"),
    ]
    mcnemar_rows = []
    for label, baseline_col, c_col in pairs:
        for scope_name, scope in scopes:
            y = scope["label"].values
            base = scope[baseline_col].values
            ch = scope[c_col].values
            res = mcnemar(y, base, ch, exact=False)
            mcnemar_rows.append({
                "comparison": f"{label} vs {baseline_col}",
                "scope": scope_name,
                "n": len(scope),
                **res,
            })
    mcnemar_df = pd.DataFrame(mcnemar_rows)
    mcnemar_df.to_csv(RES / "defense_c_pilot_mcnemar.csv", index=False)

    # Print headline summary
    print("\n=== Headline metrics (overall, n=500) ===")
    print(metrics_df[metrics_df["scope"] == "overall"][
        ["defense", "n", "precision", "recall", "f1", "accuracy"]
    ].to_string(index=False))

    print("\n=== Paired McNemar (overall) ===")
    print(mcnemar_df[mcnemar_df["scope"] == "overall"][
        ["comparison", "n", "b", "c", "p_value"]
    ].to_string(index=False))

    # Pull out specific cells for the writeup
    overall = metrics_df[metrics_df["scope"] == "overall"].set_index("defense")
    md = _build_markdown(overall, metrics_df, mcnemar_df)
    (RES / "defense_c_pilot.md").write_text(md, encoding="utf-8")
    print(f"\nsaved {RES / 'defense_c_pilot.md'}")
    print(f"saved {RES / 'defense_c_pilot_metrics.csv'}")
    print(f"saved {RES / 'defense_c_pilot_mcnemar.csv'}")


def _build_markdown(overall: pd.DataFrame, metrics_df: pd.DataFrame, mcnemar_df: pd.DataFrame) -> str:
    def fmt(d, col):
        v, lo, hi = d[col], d[f"{col}_lo"], d[f"{col}_hi"]
        return f"{v:.3f} [{lo:.3f}, {hi:.3f}]"

    lines = []
    lines.append("# Defense C combined pipeline: pilot-scale analysis (n=500)\n")
    lines.append("- Run date: 2026-05-11")
    lines.append("- Data: 500-row Defense B pilot (`results/defense_b_pilot.csv`) merged with full-eval-set Defense A predictions (`results/defense_a_full_eval_set.csv`)")
    lines.append("- No new API calls. Defense C is computed as the OR-combination of Defense A and Defense B verdicts on the same prompts.")
    lines.append("")
    lines.append("## Decision rule")
    lines.append("")
    lines.append("```")
    lines.append("A prompt is flagged by Defense C if:")
    lines.append("    Defense A classifier flags it as INJECTION")
    lines.append("  OR")
    lines.append("    Defense B agent + judge says the agent's response is HIJACKED")
    lines.append("```")
    lines.append("")
    lines.append("Three Defense C variants are tested, paired with each Defense A choice (DeBERTa alone, PG2 alone, DeBERTa+PG2 ensemble).")
    lines.append("")
    lines.append("## Headline metrics (overall, n=500, with bootstrap 95% CIs)")
    lines.append("")
    lines.append("| Defense | Precision | Recall | F1 | Accuracy |")
    lines.append("|---|---|---|---|---|")
    for name in [
        "A: DeBERTa alone", "A: PG2 alone", "A: DeBERTa+PG2 ensemble",
        "B: Sonnet judge alone",
        "C: DeBERTa + B", "C: PG2 + B", "C: Ensemble + B",
    ]:
        row = overall.loc[name]
        lines.append(
            f"| {name} | {fmt(row, 'precision')} | {fmt(row, 'recall')} | {fmt(row, 'f1')} | {fmt(row, 'accuracy')} |"
        )
    lines.append("")

    lines.append("## Per-dataset comparison (F1)")
    lines.append("")
    lines.append("| Defense | deepset | neuralchemy | spml |")
    lines.append("|---|---|---|---|")
    for name in [
        "A: DeBERTa alone", "A: DeBERTa+PG2 ensemble", "B: Sonnet judge alone",
        "C: DeBERTa + B", "C: Ensemble + B",
    ]:
        ds = metrics_df[metrics_df["defense"] == name].set_index("scope")
        cells = [name]
        for s in ["deepset", "neuralchemy", "spml"]:
            cells.append(f"{ds.loc[s, 'f1']:.3f}")
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")

    lines.append("## Paired McNemar (overall)")
    lines.append("")
    lines.append("Tests whether Defense C's error pattern differs from each single-defense baseline.")
    lines.append("")
    lines.append("| Comparison | b (baseline wins) | c (C wins) | p-value |")
    lines.append("|---|---|---|---|")
    overall_mc = mcnemar_df[mcnemar_df["scope"] == "overall"]
    for _, r in overall_mc.iterrows():
        lines.append(f"| {r['comparison']} | {r['b']} | {r['c']} | {r['p_value']:.4g} |")
    lines.append("")

    lines.append("## Reading")
    lines.append("")
    lines.append("Defense C is the OR-combination, so by construction recall >= max(recall_A, recall_B). The interesting question is whether the recall lift over the best single defense is significant, and whether the FPR cost of OR-combination is acceptable. McNemar's b and c columns indicate the asymmetric error pattern: c is the count of prompts Defense C gets right that the baseline gets wrong, b is the count where the baseline is right and C is wrong. For OR-combinations against either component, b should equal 0 (C cannot do worse on a prompt than the baseline component), so the entire test reduces to whether c is large enough to declare meaningful improvement.")
    lines.append("")
    lines.append("## Caveats")
    lines.append("")
    lines.append("Pilot-scale (n=500); full-scale Defense C requires running the agent + judge pipeline on the ~2,326 remaining frozen-eval-set rows that Defense A passes (cost ~$5 with Sonnet judge, ~$2 with Haiku 4.5 after gold-subset validation). Per-subcategory breakdowns on neuralchemy at this n are exploratory only. Judge rubric is the minimum-rubric form, not the production rubric.")

    return "\n".join(lines)


if __name__ == "__main__":
    main()
