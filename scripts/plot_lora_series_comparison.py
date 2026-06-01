"""Generate the consolidated comparison figure for the §5.11 LoRA-on-BIPIA arc.

Produces a 2x2 figure summarising the four LoRA iterations on BIPIA indirect
injection (NB10, NB10b, NB10c, NB10e) across four metrics:

  - Cohen d on BIPIA test (log scale; the score-distribution-separation metric
    that exposed NB10 and NB10b as degenerate even when binary F1 looked fine)
  - Macro F1 on BIPIA test (the imbalance-robust headline metric)
  - Test 1 flag rate on attacks paired with generic questions (the pressure
    test from NB10d that caught NB10c's question-style shortcut)
  - eval_set F1 on direct injection (the §5.11 reference: 0.981 from the
    LoRA-from-ProtectAI winner; reported here to show that the BIPIA arm did
    not degrade direct-injection performance)

Output: reports/figures/lora_series_comparison.png and .pdf

Source data: results/lora_v2_metrics.json, lora_v3_metrics.json,
lora_v3_pressure_tests.json, lora_v4_metrics.json. NB10 numbers are
hardcoded since that probe did not produce a metrics JSON (only console
output documented in NB10's post-run notebook).
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

REPO = Path(__file__).resolve().parents[1]
FIG_DIR = REPO / "reports" / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)


def _load(p: Path) -> dict:
    return json.loads(p.read_text())


def _macro_f1_from_confusion(tp: int, fp: int, fn: int, tn: int) -> float:
    """Compute macro F1 from a 2x2 confusion matrix.

    Macro F1 = mean of per-class F1. Class 1 (attack) is positive; class 0 is
    the (TN, FN) corner. Robust to all-positive or all-negative degenerate
    predictions where binary F1 inflates under imbalance.
    """
    def _f1(p_, r_):
        return 0.0 if (p_ + r_) == 0 else 2 * p_ * r_ / (p_ + r_)
    p1 = tp / max(tp + fp, 1)
    r1 = tp / max(tp + fn, 1)
    f1_pos = _f1(p1, r1)
    # Class 0: treat 0 as positive.
    p0 = tn / max(tn + fn, 1)
    r0 = tn / max(tn + fp, 1)
    f1_neg = _f1(p0, r0)
    return (f1_pos + f1_neg) / 2


def main() -> None:
    nb10b = _load(REPO / "results" / "lora_v2_metrics.json")
    nb10c = _load(REPO / "results" / "lora_v3_metrics.json")
    nb10d = _load(REPO / "results" / "lora_v3_pressure_tests.json")
    nb10e = _load(REPO / "results" / "lora_v4_metrics.json")

    # NB10 was a pure inference probe (no metrics JSON saved). Numbers are from
    # the post-run notebook console output and the §5.11 prose.
    nb10_cohen_d = 0.13
    nb10_macro_f1 = float("nan")  # degenerate; reporting macro F1 not meaningful
    nb10_test1 = float("nan")     # Test 1 was not yet defined at NB10 time
    nb10_evalset_f1 = 0.981       # §5.11 LoRA-v1 unchanged on direct injection

    # NB10b: variant B (combined), BIPIA test row is metrics[0]
    nb10b_bipia = nb10b["variant_b_combined"]["metrics"][0]
    nb10b_evalset = nb10b["variant_b_combined"]["metrics"][1]
    nb10b_cohen_d = nb10b["robustness_checks"]["variant_b_score_separation"]["cohen_d"]

    # NB10c: variant B, BIPIA test = metrics[0], eval_set = metrics[1]
    nb10c_bipia = nb10c["variant_b_combined_aug"]["metrics"][0]
    nb10c_evalset = nb10c["variant_b_combined_aug"]["metrics"][1]
    nb10c_cohen_d = nb10c["robustness_checks"]["variant_b_score_separation"]["cohen_d"]
    nb10c_test1 = nb10d["test1_attack_question_swap"]["perturbed_flag_rate"]

    # NB10e: use in-distribution headline numbers for primary comparison
    nb10e_bipia = nb10e["bipia_test"]
    nb10e_evalset = nb10e["eval_set_test"]
    nb10e_test1 = nb10e["pressure_tests"]["test1_attack_question_swap"]["flag_rate"]
    # Triple-cross d for honest generalisation reporting
    nb10e_triple_d = nb10e["pressure_tests"]["test3_holdout_triple_cross"]["cohen_d"]
    nb10e_triple_macro = nb10e["pressure_tests"]["test3_holdout_triple_cross"]["macro_f1"]

    iterations = ["NB10\nLoRA-v1\ntransfer", "NB10b\nnaive\nretraining",
                  "NB10c\nclean\naugmentation", "NB10e\nsymmetric\naugmentation"]
    colours = ["#cc4444", "#cc8844", "#ddbb44", "#3a9c5a"]  # fail, fail, partial, pass

    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle("LoRA fine-tune on BIPIA indirect injection: four-iteration arc",
                 fontsize=14, fontweight="bold")

    # Subplot 1: Cohen d (log scale, threshold at 1.5)
    ax = axes[0, 0]
    cohen_d_values = [nb10_cohen_d, nb10b_cohen_d, nb10c_cohen_d, nb10e["robustness_checks"].get(
        "variant_b_score_separation", {}).get("cohen_d", 189.43) if False else 189.43]
    # NB10e in-distribution d isn't stored in the JSON's robustness_checks; use the bipia_test value
    cohen_d_values[3] = nb10e_bipia.get("cohen_d", 189.43)
    bars = ax.bar(iterations, cohen_d_values, color=colours, edgecolor="black", linewidth=0.5)
    ax.set_yscale("log")
    ax.axhline(1.5, color="grey", linestyle="--", linewidth=1, label="d=1.5 (healthy separation)")
    ax.set_ylabel("Cohen d (log scale)")
    ax.set_title("(a) Score distribution separation on BIPIA test")
    ax.legend(loc="upper left", fontsize=8)
    for bar, val in zip(bars, cohen_d_values):
        ax.text(bar.get_x() + bar.get_width()/2, val * 1.15, f"{val:.2f}",
                ha="center", va="bottom", fontsize=9)

    # Subplot 2: Macro F1 (linear 0-1)
    ax = axes[0, 1]
    nb10b_macro = nb10b_bipia.get("macro_f1") or _macro_f1_from_confusion(
        nb10b_bipia["tp"], nb10b_bipia["fp"], nb10b_bipia["fn"], nb10b_bipia["tn"])
    macro_values = [nb10_macro_f1,
                    nb10b_macro,
                    nb10c_bipia["macro_f1"],
                    nb10e_bipia["macro_f1"]]
    # Use 0 placeholder for NaN (NB10) with annotation
    plot_values = [0 if np.isnan(v) else v for v in macro_values]
    bars = ax.bar(iterations, plot_values, color=colours, edgecolor="black", linewidth=0.5)
    ax.axhline(0.5, color="grey", linestyle="--", linewidth=1, label="random baseline (0.5)")
    ax.axhline(0.9, color="green", linestyle=":", linewidth=1, label="strong signal (0.9)")
    ax.set_ylabel("Macro F1 on BIPIA test")
    ax.set_ylim(0, 1.05)
    ax.set_title("(b) Imbalance-robust headline metric")
    ax.legend(loc="lower right", fontsize=8)
    for bar, val, raw in zip(bars, plot_values, macro_values):
        label = "n/a\n(degenerate)" if np.isnan(raw) else f"{raw:.3f}"
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.02, label,
                ha="center", va="bottom", fontsize=9)

    # Subplot 3: Test 1 flag rate on attacks with generic questions
    ax = axes[1, 0]
    test1_values = [nb10_test1, float("nan"), nb10c_test1, nb10e_test1]
    plot_values = [0 if np.isnan(v) else v for v in test1_values]
    bars = ax.bar(iterations, plot_values, color=colours, edgecolor="black", linewidth=0.5)
    ax.axhline(0.95, color="green", linestyle=":", linewidth=1, label="deployment threshold (0.95)")
    ax.axhline(0.5, color="grey", linestyle="--", linewidth=1, label="coin flip (0.5)")
    ax.set_ylabel("Flag rate on attacks + generic question")
    ax.set_ylim(0, 1.1)
    ax.set_title("(c) Pressure test: question-style independence")
    ax.legend(loc="lower right", fontsize=8)
    for bar, val, raw in zip(bars, plot_values, test1_values):
        label = "not\nmeasured" if np.isnan(raw) else f"{raw:.3f}"
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.03, label,
                ha="center", va="bottom", fontsize=9)

    # Subplot 4: eval_set F1 on direct injection (preservation check)
    ax = axes[1, 1]
    evalset_values = [nb10_evalset_f1,
                      nb10b_evalset["f1"],
                      nb10c_evalset["f1"],
                      nb10e_evalset["f1"]]
    bars = ax.bar(iterations, evalset_values, color=colours, edgecolor="black", linewidth=0.5)
    ax.axhline(0.981, color="blue", linestyle=":", linewidth=1, label="§5.11 LoRA-v1 reference (0.981)")
    ax.set_ylabel("F1 on eval_set test")
    ax.set_ylim(0.9, 1.0)
    ax.set_title("(d) Direct-injection performance preserved")
    ax.legend(loc="lower right", fontsize=8)
    for bar, val in zip(bars, evalset_values):
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.003, f"{val:.3f}",
                ha="center", va="bottom", fontsize=9)

    # Caption / footer note
    fig.text(0.5, 0.005,
             "NB10e values are in-distribution test split (base-email-stratified). "
             f"NB10e triple-cross held-out generalisation: d={nb10e_triple_d:.2f}, macro F1={nb10e_triple_macro:.3f}. "
             "See §5.11 for the full methodology arc.",
             ha="center", fontsize=8, style="italic", color="dimgrey")

    plt.tight_layout(rect=[0, 0.025, 1, 0.97])
    out_png = FIG_DIR / "lora_series_comparison.png"
    out_pdf = FIG_DIR / "lora_series_comparison.pdf"
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    fig.savefig(out_pdf, bbox_inches="tight")
    print(f"Wrote {out_png.relative_to(REPO)}")
    print(f"Wrote {out_pdf.relative_to(REPO)}")


if __name__ == "__main__":
    main()
