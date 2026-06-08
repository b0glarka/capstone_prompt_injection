"""Judge cost vs reliability scatter (Defense B's clearest story).

Shows the Haiku-approximately-equals-Opus-at-one-fifth-the-cost finding
visually: x-axis = cost per 1,000 prompts in USD (from the production
defense-stack cost table in §7), y-axis = Cohen's kappa vs the 150-row
human gold subset under the v1.25 rubric (AMBIG=HIJACKED convention,
matches §5.6 reporting). Values are hardcoded from
results/judge_v125_kappa.md and §7's per-model cost table to keep this
script self-contained.

Output: reports/figures/judge_cost_vs_reliability.{png,pdf}
"""

from pathlib import Path
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "figures" / "judge_cost_vs_reliability"

# (name, family, kappa v1.25, cost per 1k prompts USD, marker)
# Cost is for the judge alone at the §7 defense-stack call shape.
# Kappa from results/judge_v125_kappa.md overall rows under AMBIG=HIJACKED.
JUDGES = [
    ("Claude Haiku 4.5",  "Anthropic", 0.554, 0.42, "o"),
    ("Claude Sonnet 4.6", "Anthropic", 0.466, 1.10, "o"),
    ("Claude Opus 4.7",   "Anthropic", 0.550, 2.16, "o"),
    ("GPT-4o-mini",       "OpenAI",    0.403, 0.09, "s"),
]
FAMILY_COLOR = {"Anthropic": "#cc6633", "OpenAI": "#3b7a57"}


def main() -> None:
    fig, ax = plt.subplots(figsize=(8, 5.2))

    for name, family, kappa, cost, marker in JUDGES:
        ax.scatter(
            cost, kappa,
            s=180, marker=marker,
            color=FAMILY_COLOR[family], edgecolor="black", linewidth=0.8,
            zorder=3,
        )
        dx, dy = 0.06, 0.005
        ha = "left"
        if name == "Claude Haiku 4.5":
            dy = 0.012
        if name == "GPT-4o-mini":
            dx, dy = 0.04, -0.015
        ax.annotate(
            name, (cost, kappa), xytext=(cost + dx, kappa + dy),
            fontsize=10, ha=ha, va="bottom",
        )

    # Reference band: Landis-Koch "moderate" 0.41-0.60
    ax.axhspan(0.41, 0.60, color="#bbbbbb", alpha=0.15, zorder=0)
    ax.text(
        2.35, 0.505, "moderate\n(Landis-Koch)",
        fontsize=9, color="#666666", ha="right", va="center",
    )

    ax.set_xscale("log")
    ax.set_xlim(0.05, 3.5)
    ax.set_ylim(0.30, 0.65)
    ax.set_xlabel("Judge cost per 1,000 prompts (USD, log scale)", fontsize=11)
    ax.set_ylabel("Cohen's kappa vs 150-row human gold subset", fontsize=11)
    ax.set_axisbelow(True)
    ax.grid(which="both", linestyle="--", alpha=0.4)

    handles = [
        plt.Line2D([0], [0], marker="o", linestyle="",
                   color=FAMILY_COLOR["Anthropic"], markeredgecolor="black",
                   markersize=10, label="Anthropic"),
        plt.Line2D([0], [0], marker="s", linestyle="",
                   color=FAMILY_COLOR["OpenAI"], markeredgecolor="black",
                   markersize=10, label="OpenAI"),
    ]
    ax.legend(handles=handles, loc="lower right", frameon=True, fontsize=10)
    ax.set_title(
        "Judge reliability vs cost (v1.25 rubric, 150-row gold subset)\n"
        "Haiku 4.5 matches Opus 4.7 at one-fifth the cost",
        fontsize=12, pad=10,
    )

    fig.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(f"{OUT}.png", dpi=200)
    fig.savefig(f"{OUT}.pdf")
    print(f"Wrote {OUT}.png and {OUT}.pdf")


if __name__ == "__main__":
    main()
