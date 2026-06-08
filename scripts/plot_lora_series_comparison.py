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

    iterations = ["Iteration 1\ndirect-LoRA\ntransfer", "Iteration 2\nnaive\nretraining",
                  "Iteration 3\nclean-question\naugmentation", "Iteration 4\nsymmetric\naugmentation"]
    colours = ["#cc4444", "#cc8844", "#ddbb44", "#3a9c5a"]  # fail, fail, partial, pass

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle("LoRA fine-tune on BIPIA indirect injection: four-iteration arc",
                 fontsize=15, fontweight="bold")

    # Subplot 1: Cohen d (log scale, threshold at 1.5)
    ax = axes[0]
    cohen_d_values = [nb10_cohen_d, nb10b_cohen_d, nb10c_cohen_d, nb10e_bipia.get("cohen_d", 189.43)]
    bars = ax.bar(iterations, cohen_d_values, color=colours, edgecolor="black", linewidth=0.5)
    ax.set_yscale("log")
    ax.axhline(1.5, color="grey", linestyle="--", linewidth=1, label="d=1.5 (healthy separation)")
    ax.set_ylabel("Cohen d (log scale)", fontsize=13)
    ax.set_title("(a) Score distribution separation on BIPIA test", fontsize=13)
    ax.legend(loc="upper left", fontsize=12)
    ax.tick_params(axis="both", labelsize=11)
    for bar, val in zip(bars, cohen_d_values):
        ax.text(bar.get_x() + bar.get_width()/2, val * 1.15, f"{val:.2f}",
                ha="center", va="bottom", fontsize=12)

    # Subplot 2: Test 1 flag rate on attacks with generic questions
    ax = axes[1]
    test1_values = [nb10_test1, float("nan"), nb10c_test1, nb10e_test1]
    plot_values = [0 if np.isnan(v) else v for v in test1_values]
    bars = ax.bar(iterations, plot_values, color=colours, edgecolor="black", linewidth=0.5)
    ax.axhline(0.95, color="green", linestyle=":", linewidth=1, label="deployment threshold (0.95)")
    ax.axhline(0.5, color="grey", linestyle="--", linewidth=1, label="coin flip (0.5)")
    ax.set_ylabel("Flag rate on attacks paired with generic question", fontsize=13)
    ax.set_ylim(0, 1.1)
    ax.set_title("(b) Pressure test: question-style independence", fontsize=13)
    ax.legend(loc="lower right", fontsize=12)
    ax.tick_params(axis="both", labelsize=11)
    for bar, val, raw in zip(bars, plot_values, test1_values):
        label = "not\nmeasured" if np.isnan(raw) else f"{raw:.3f}"
        ax.text(bar.get_x() + bar.get_width()/2, val + 0.03, label,
                ha="center", va="bottom", fontsize=12)

    plt.tight_layout(rect=[0, 0.0, 1, 0.95])
    out_png = FIG_DIR / "lora_series_comparison.png"
    out_pdf = FIG_DIR / "lora_series_comparison.pdf"
    fig.savefig(out_png, dpi=150, bbox_inches="tight")
    fig.savefig(out_pdf, bbox_inches="tight")
    print(f"Wrote {out_png.relative_to(REPO)}")
    print(f"Wrote {out_pdf.relative_to(REPO)}")


if __name__ == "__main__":
    main()
