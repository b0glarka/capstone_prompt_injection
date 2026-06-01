"""Compute Wilson score 95% CIs for per-subcategory recall numbers.

Reads `results/defense_a_full_subcategory_recall.csv`, adds Wilson interval
columns for DeBERTa and Prompt Guard 2, plus an `overlaps` flag indicating
whether the two CIs overlap (a defensible proxy for "classifiers not
distinguishable at this n").

Wilson is preferred over Wald (normal approximation) for binary proportions
at any n, but the difference matters most when p_hat is near 0 or 1 (Wald
under-covers) and when n is small (Wald is symmetric around p_hat, which
is incorrect at the boundaries). Brown, Cai and DasGupta (2001) recommend
Wilson as the default. Hesterberg (2015) documents bootstrap's parallel
issue at small n.

Output: `results/defense_a_full_subcategory_recall_wilson.csv` with all
original columns + 4 new columns + overlap flag. Also prints a clean
markdown table for direct paste into the report.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.metrics import wilson_ci  # noqa: E402

IN_CSV = REPO_ROOT / "results" / "defense_a_full_subcategory_recall.csv"
OUT_CSV = REPO_ROOT / "results" / "defense_a_full_subcategory_recall_wilson.csv"


def _overlap(lo_a: float, hi_a: float, lo_b: float, hi_b: float) -> bool:
    """Two intervals overlap iff neither is strictly above the other."""
    return not (hi_a < lo_b or hi_b < lo_a)


def main() -> None:
    df = pd.read_csv(IN_CSV)
    rows = []
    for _, r in df.iterrows():
        n = int(r["n"])
        # Reconstruct successes from recall (round to nearest integer)
        s_deb = round(n * float(r["deberta_recall"]))
        s_pg2 = round(n * float(r["pg2_recall"]))
        lo_deb, hi_deb = wilson_ci(s_deb, n)
        lo_pg2, hi_pg2 = wilson_ci(s_pg2, n)
        rows.append({
            "subcategory":   r["subcategory"],
            "n":             n,
            "deberta_recall": float(r["deberta_recall"]),
            "deberta_lo":    lo_deb,
            "deberta_hi":    hi_deb,
            "pg2_recall":    float(r["pg2_recall"]),
            "pg2_lo":        lo_pg2,
            "pg2_hi":        hi_pg2,
            "delta":         float(r["delta"]),
            "cis_overlap":   _overlap(lo_deb, hi_deb, lo_pg2, hi_pg2),
        })
    out = pd.DataFrame(rows)
    out.to_csv(OUT_CSV, index=False)
    print(f"wrote {OUT_CSV.relative_to(REPO_ROOT)}")

    # Print pasteable markdown for the report (subcategories with n >= 30)
    print()
    print("| Subcategory | n | DeBERTa recall [95% CI] | PG2 recall [95% CI] | CIs overlap? |")
    print("|---|---|---|---|---|")
    for r in rows:
        if r["n"] < 30:
            continue
        deb = f"{r['deberta_recall']:.3f} [{r['deberta_lo']:.3f}, {r['deberta_hi']:.3f}]"
        pg2 = f"{r['pg2_recall']:.3f} [{r['pg2_lo']:.3f}, {r['pg2_hi']:.3f}]"
        ov = "Yes" if r["cis_overlap"] else "No"
        print(f"| {r['subcategory']} | {r['n']} | {deb} | {pg2} | {ov} |")


if __name__ == "__main__":
    main()
