"""Build the cost-weighted business decision framework for prompt-injection defenses.

Per implementation plan v2 Section 6a, this script translates statistical
results into deployment recommendations. The framework lives in three layers:

  Layer 1 (harm taxonomy)        : qualitative classes of consequence
  Layer 2 (cost-weighted scoring): expected cost per prompt under varying cost ratios
  Layer 3 (decision matrix)      : per-defense security/usability/latency/cost summary
  Layer 4 (scenario recommendations): which defense fits which enterprise scenario

This script computes Layer 2 and Layer 3 from existing Defense A data on the
frozen evaluation set. Layer 1 and Layer 4 are static narrative and are
written into the markdown output. Defense B columns are filled in once the
500-row pilot completes; in the meantime, sneak-preview estimates are flagged
as preliminary.

Outputs:
  results/business_decision_matrix.csv
  reports/business_decision_framework.md
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

RES = REPO / "results"
REPORTS = REPO / "reports"

# Cost ratios to test: how many false alarms equal one missed attack?
# Smaller ratio = false alarms are nearly as costly as missed attacks (e.g., consumer chatbot).
# Larger ratio = a missed attack is catastrophically worse (e.g., critical infrastructure).
COST_RATIOS = [10, 100, 1000]


def fnr_fpr_from_predictions(y_true: np.ndarray, y_pred: np.ndarray) -> tuple[float, float]:
    """Compute false-negative rate and false-positive rate at the given operating point."""
    tn = int(((y_true == 0) & (y_pred == 0)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum())
    fn = int(((y_true == 1) & (y_pred == 0)).sum())
    tp = int(((y_true == 1) & (y_pred == 1)).sum())
    fnr = fn / (fn + tp) if (fn + tp) else 0.0
    fpr = fp / (fp + tn) if (fp + tn) else 0.0
    return fnr, fpr


def expected_cost_per_prompt(fnr: float, fpr: float, cost_ratio: float, injection_prevalence: float) -> float:
    """E[cost] per prompt, in 'false-alarm units'.

    Cost of one missed attack = cost_ratio false-alarm units.
    Cost of one false alarm   = 1 false-alarm unit.
    E[cost] = P(injection) * FNR * cost_ratio + P(benign) * FPR * 1
    """
    return (
        injection_prevalence * fnr * cost_ratio
        + (1 - injection_prevalence) * fpr * 1.0
    )


def main() -> None:
    df = pd.read_csv(RES / "defense_a_full_eval_set.csv")
    n = len(df)
    inj_prev = float((df["label"] == 1).mean())
    print(f"eval set: {n} rows, injection prevalence {inj_prev:.3f}")

    # Add ensemble predictions for completeness
    df["or_pred"]  = ((df["deberta_pred_label_id"] == 1) | (df["pg2_pred_label_id"] == 1)).astype(int)
    df["and_pred"] = ((df["deberta_pred_label_id"] == 1) & (df["pg2_pred_label_id"] == 1)).astype(int)

    defenses = {
        "DeBERTa (ProtectAI v2)":     "deberta_pred_label_id",
        "Prompt Guard 2 (Meta)":      "pg2_pred_label_id",
        "Ensemble OR-gate":           "or_pred",
        "Ensemble AND-gate":          "and_pred",
    }

    matrix_rows = []
    y_true = df["label"].values
    for name, pred_col in defenses.items():
        yp = df[pred_col].values
        fnr, fpr = fnr_fpr_from_predictions(y_true, yp)
        tpr = 1 - fnr
        legit_pass = 1 - fpr
        row = {
            "defense": name,
            "security_TPR_recall": round(tpr, 4),
            "security_FNR_missed_rate": round(fnr, 4),
            "usability_legit_pass_rate": round(legit_pass, 4),
            "usability_FPR_false_alarm_rate": round(fpr, 4),
        }
        for cr in COST_RATIOS:
            cost = expected_cost_per_prompt(fnr, fpr, cr, inj_prev)
            row[f"E_cost_per_prompt_at_{cr}x"] = round(cost, 4)
        matrix_rows.append(row)

    # Defense B placeholder rows: estimated from the 24-case sneak preview, flagged as preliminary
    sneak = pd.read_csv(RES / "defense_b_sneak_preview.csv")
    # 4/8 hijacked on deepset role-play subset. Cannot translate cleanly to TPR/FPR on the full eval set;
    # report as placeholder line in the matrix.
    matrix_rows.append({
        "defense": "Defense B (Llama+Claude judge) [PRELIMINARY, n=24 sneak preview]",
        "security_TPR_recall": "see report; 4/8 caught on deepset role-play class, 0/8 on jailbreak, 1/8 on encoding",
        "security_FNR_missed_rate": "preliminary",
        "usability_legit_pass_rate": "preliminary",
        "usability_FPR_false_alarm_rate": "preliminary",
        **{f"E_cost_per_prompt_at_{cr}x": "preliminary" for cr in COST_RATIOS},
    })

    matrix_df = pd.DataFrame(matrix_rows)
    matrix_df.to_csv(RES / "business_decision_matrix.csv", index=False)
    print(f"\nsaved {RES / 'business_decision_matrix.csv'}")

    # Sweep cost ratios for the headline narrative
    print("\nExpected cost per prompt (in false-alarm units) by cost ratio:")
    headline_cols = ["defense"] + [f"E_cost_per_prompt_at_{cr}x" for cr in COST_RATIOS]
    print(matrix_df[matrix_df["defense"].str.contains("PRELIMINARY") == False][headline_cols].to_string(index=False))

    # Write the markdown framework
    md = _build_markdown(matrix_df, inj_prev, n)
    out_md = REPORTS / "business_decision_framework.md"
    out_md.write_text(md, encoding="utf-8")
    print(f"saved {out_md}")


def _build_markdown(matrix_df: pd.DataFrame, inj_prev: float, n: int) -> str:
    quant = matrix_df[matrix_df["defense"].str.contains("PRELIMINARY") == False].copy()
    qbest = {
        cr: quant.loc[quant[f"E_cost_per_prompt_at_{cr}x"].astype(float).idxmin(), "defense"]
        for cr in COST_RATIOS
    }

    lines: list[str] = []
    lines.append("# Business Decision Framework: Prompt Injection Defense Deployment\n")
    lines.append(
        "This document translates the statistical evaluation of input-side (Defense A) and "
        "output-side (Defense B) prompt-injection defenses into deployment recommendations. "
        "It is the practitioner-facing artifact of the capstone, anchored on the empirical "
        f"results in `results/defense_a_full_metrics.csv` (n = {n}, injection prevalence "
        f"{inj_prev:.3f}) and the Defense B sneak-preview data in `results/defense_b_*_preview.md`."
    )
    lines.append(
        "\n\nThe framework has four layers. Layer 1 names the categories of harm a deployment "
        "must reason about. Layer 2 reduces those categories to a single cost-weighted score "
        "that varies with the deployment context. Layer 3 is a per-defense decision matrix. "
        "Layer 4 maps representative enterprise scenarios to the defense configuration that "
        "minimizes expected cost in that scenario.\n"
    )

    lines.append("\n## Layer 1: Business harm taxonomy\n")
    lines.append(
        "Prompt-injection failures cause two error types with very different consequences:\n"
        "\n"
        "**Missed attack (false negative)**: an injection succeeds, the defense does not flag it, "
        "and the agent's output reflects the attacker's goal. Possible business consequences:\n"
        "\n"
        "- Financial. Unauthorized transactions, data exfiltration to attacker-controlled destinations, "
        "leak of pricing or contract terms.\n"
        "- Reputational. Brand damage from offensive or off-policy agent outputs, especially if surfaced "
        "publicly (screenshot leaks, journalist test cases).\n"
        "- Operational. The attacker uses the agent to bypass workflow controls (e.g., approval routing) "
        "or to plant information that downstream automation acts on without re-checking.\n"
        "- Compliance. Regulatory exposure under GDPR, sector-specific obligations (HIPAA, PCI-DSS), or "
        "AI-system safety regulations now appearing in EU and other jurisdictions.\n"
        "\n"
        "**False alarm (false positive)**: a benign user request is wrongly flagged as an injection, "
        "and either blocked, deferred to a human reviewer, or downgraded to a more restricted response.\n"
        "\n"
        "- Operational. Each false alarm consumes review time and adds latency. At scale (millions of "
        "interactions), even a 1% false-positive rate translates into thousands of unnecessary escalations.\n"
        "- User-experience. Repeated false alarms erode trust in the agent and push legitimate users to "
        "workarounds outside the controlled environment.\n"
        "- Revenue. For customer-facing deployments, blocked legitimate requests are abandoned interactions, "
        "which is a direct conversion cost.\n"
    )

    lines.append("\n## Layer 2: Cost-weighted decision scoring\n")
    lines.append(
        "Single-number metrics (accuracy, F1, AUC) do not select a deployment threshold because they do "
        "not encode the relative cost of false negatives vs false positives. The framework reduces this "
        "to a single expected-cost-per-prompt expression and varies it across plausible cost ratios:\n"
        "\n"
        "```\n"
        "E[cost per prompt] = P(injection) * FNR * cost_per_missed_attack\n"
        "                   + P(benign)    * FPR * cost_per_false_alarm\n"
        "```\n"
        "\n"
        "Normalizing on `cost_per_false_alarm = 1` and varying `cost_per_missed_attack` across {10, 100, 1000}:\n"
        "\n"
        "- `10x`   : false alarms are nearly as costly as missed attacks. Representative of consumer chat "
        "applications where user friction is high-impact and the underlying harm of a missed attack is "
        "bounded (e.g., a missed jailbreak that makes the chatbot say something embarrassing).\n"
        "- `100x`  : missed attacks are substantially worse. Representative of business-internal tools "
        "with moderate stakes (e.g., a customer-support agent with access to billing data).\n"
        "- `1000x` : a missed attack is catastrophically worse than a false alarm. Representative of "
        "agents with access to high-stakes tools (financial transactions, code execution, sensitive "
        "data systems). This is closest to the Hiflylabs deployment context described in the PID.\n"
        "\n"
        "**Per-defense expected cost at each ratio** (lower is better; injection prevalence "
        f"{inj_prev:.3f}, n = {n}):\n"
        "\n"
        "| Defense | TPR (recall) | FPR | E[cost] @ 10x | E[cost] @ 100x | E[cost] @ 1000x |\n"
        "|---|---|---|---|---|---|"
    )
    for _, r in quant.iterrows():
        lines.append(
            f"\n| {r['defense']} | {r['security_TPR_recall']} | {r['usability_FPR_false_alarm_rate']} | "
            f"{r['E_cost_per_prompt_at_10x']:.4f} | {r['E_cost_per_prompt_at_100x']:.4f} | "
            f"{r['E_cost_per_prompt_at_1000x']:.4f} |"
        )
    lines.append("\n")
    lines.append(
        "Reading: the cost-minimizing defense changes with the assumed cost ratio. "
        f"At 10x, **{qbest[10]}** minimizes expected cost. "
        f"At 100x, **{qbest[100]}** minimizes expected cost. "
        f"At 1000x, **{qbest[1000]}** minimizes expected cost.\n"
        "\n"
        "The qualitative pattern: the more catastrophic a missed attack is judged to be, the more aggressive "
        "the deployment should be in flagging (higher TPR, accepting more false alarms). Conservative "
        "classifiers (high precision, low recall) optimize for the low cost-ratio regime; sensitive "
        "configurations (broader flagging, lower threshold or OR-gated ensembles) optimize for the "
        "high cost-ratio regime.\n"
    )

    lines.append("\n## Layer 3: Decision matrix (per defense)\n")
    lines.append(
        "Practitioner-facing summary across the dimensions that determine deployment fit. "
        "Latency and cost-per-1K-prompts columns are estimates from observed pilot data where available; "
        "Defense B numbers are preliminary from the 24-case sneak preview.\n"
        "\n"
        "| Defense | Security (TPR) | Usability (legit pass) | Latency profile | Cost per 1K prompts | Best for |\n"
        "|---|---|---|---|---|---|\n"
        "| DeBERTa (ProtectAI v2)        | 0.875 | 0.973 | <100ms on CPU, batched | local inference, ~$0 marginal | broad first-line filter where false alarms are visible to users |\n"
        "| Prompt Guard 2 (Meta)         | 0.503 | 0.992 | <100ms on CPU, batched | local inference, ~$0 marginal | extremely conservative deployments where false alarms are unacceptable |\n"
        "| Ensemble OR-gate              | 0.887 | 0.969 | <200ms on CPU (two inferences) | local inference, ~$0 marginal | applications wanting the slight recall lift of two classifiers combined |\n"
        "| Ensemble AND-gate             | 0.491 | 0.998 | <200ms on CPU (two inferences) | local inference, ~$0 marginal | low-stakes deployments where conservative blocking is preferred |\n"
        "| Defense B (Llama+Claude judge) [PRELIMINARY] | preliminary; sneak preview shows mechanism varies by attack class | preliminary | seconds-per-call (LLM agent + LLM judge) | API: ~$0.005-0.010 per prompt (Sonnet judge), ~$0.001 per prompt with Haiku 4.5 judge (cost-comparison sweep pending) | applications already running agents where the second-stage judge is the only practical defense, especially against subtle injections that input classifiers miss |\n"
        "| Defense C (A then B, combined) [STRETCH]    | not yet measured | not yet measured | A first then B on A's non-blocks | additive of A and B costs, on prompts that pass A | high-stakes deployments where the input classifier removes obvious attacks and the judge handles the residual |\n"
    )

    lines.append("\n## Layer 4: Scenario-based recommendations\n")
    lines.append(
        "Three representative enterprise scenarios with the defense configuration that minimizes expected "
        "cost in each context. The Hiflylabs deployment scenario described in the PID maps closest to "
        "the high-stakes case.\n"
        "\n"
        "**Scenario A: Consumer-facing chatbot with no tool access**\n"
        "\n"
        "- Threat profile: misuse and brand-damaging outputs; no path to financial or data harm beyond text content.\n"
        "- Cost ratio: roughly 10x. False alarms hurt conversion; missed attacks are embarrassing but bounded.\n"
        "- Recommended: **DeBERTa solo at default threshold**. F1 0.91, low FPR (2.7%), local-CPU inference. "
        "No Defense B needed; the cost of false alarms outweighs the marginal value of a second-stage judge "
        "for this risk profile.\n"
        "\n"
        "**Scenario B: Business-internal agent with read-only access to systems**\n"
        "\n"
        "- Threat profile: data exfiltration and policy violations are possible; tool calls are bounded to safe operations.\n"
        "- Cost ratio: roughly 100x. Missed attacks have real consequences but containment is partial.\n"
        "- Recommended: **DeBERTa ensemble (OR-gate with PG2) plus Defense B on flagged or borderline cases**. "
        "OR-gate gives a small recall lift on the hardest dataset (deepset). Defense B as second-stage handler "
        "of subtle injections that the classifier under-flags. Use Haiku 4.5 as the judge to keep cost per prompt "
        "under $0.001 (pending the cost-comparison sweep that confirms Haiku tracks Sonnet at scale).\n"
        "\n"
        "**Scenario C: Autonomous agent with broad tool access (Hiflylabs PID context)**\n"
        "\n"
        "- Threat profile: agent can execute, send, transact, or persist on the user's behalf. Missed attacks "
        "are catastrophic.\n"
        "- Cost ratio: roughly 1000x. False alarms are inconvenient but tolerable; missed attacks must be minimized.\n"
        "- Recommended: **Defense A as input gate (use the more sensitive OR-gate ensemble) followed by Defense B "
        "on every output (not just on A's non-blocks)**. This is the Defense C configuration in the implementation "
        "plan, run in its fully-protective mode. Use Sonnet 4.6 as the primary judge (not Haiku) to maximize "
        "second-stage detection accuracy; the marginal cost is bounded by the volume of agent actions, which is "
        "typically much smaller than raw chatbot traffic.\n"
        "\n"
        "Across all three scenarios, two cross-cutting recommendations hold:\n"
        "\n"
        "- **Pre-deploy human gold-set validation of the judge** before relying on Defense B in production. "
        "The sneak-preview judge sensitivity check (Claude vs GPT-4o agreed on 6 of 8 cases) demonstrates "
        "that judge calls are sensitive to model family and rubric design.\n"
        "- **Monitor per-attack-subcategory recall in production** if the deployment has logging infrastructure. "
        "The neuralchemy subcategory analysis shows Defense A blind spots (jailbreak 0.55, encoding 0.67 on DeBERTa, "
        "both <0.10 on PG2) that an attacker can deliberately target. A defense's overall F1 is not informative if "
        "real-world traffic concentrates on the subcategories where the defense underperforms.\n"
    )

    lines.append("\n## Limitations and assumptions\n")
    lines.append(
        "- Cost ratios above are illustrative. A real deployment derives them from incident-cost data the "
        "deploying organization owns.\n"
        "- Expected-cost calculations assume independence between false-negative and false-positive events, "
        "which is realistic at the population level but not at the user-session level (a frustrated user is "
        "more likely to try injections after a false alarm).\n"
        "- Defense B numbers are sneak-preview only (24 cases). The 500-row formal pilot, when complete, "
        "will replace those placeholders. Cost-extrapolation in this document uses pilot-scale token counts.\n"
        "- The eval-set distribution (deepset + neuralchemy + SPML) may not match any specific enterprise's "
        "traffic distribution. Per-dataset metrics are reported so a deploying organization can pick the "
        "dataset whose distribution is closest to their use case.\n"
    )
    return "\n".join(lines)


if __name__ == "__main__":
    main()
