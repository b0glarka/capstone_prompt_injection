"""Re-run the 150-row gold subset against the v1.25 rubric on three judges.

Purpose: §6.3 / §5.6 documented that all three judges (Sonnet 4.6, Haiku 4.5,
GPT-4o-mini) sit at moderate Landis-Koch kappa (0.42-0.48) versus human labels
on the 150-row gold subset, with the residual gap attributed to signature-vs-
mechanism pattern matching. v1.25 (defense_b/judge.py) bakes the §3.2 v1.23
mechanism-not-signature scope note into the judge prompt directly. This script
re-runs the same 150 rows against v1.25 and reports the new per-judge kappa
alongside the v1.21 baseline so §6.3 can document whether prompt iteration
closes the gap.

Inputs:
  results/judge_gold_subset_audited.csv  150 rows with human verdicts +
                                          existing v1.21 verdicts for all 3 judges
  results/judge_gold_subset_spml_relabel_post_audit.csv  50 SPML rows with
                                          POST-FIX human verdicts (overrides
                                          the original SPML labels)

Caches: cache/judge_v125_<model>_gold_subset.jsonl per judge so re-runs are
incremental.

Outputs:
  results/judge_gold_subset_v125.csv      original cols + sonnet/haiku/gpt4mini
                                          v125 verdict + reason columns
  results/judge_v125_kappa.md             kappa table comparing v1.21 vs v1.25

Cost estimate (all three judges, 150 rows each):
  Sonnet 4.6:  ~$1.70   (150 * 2700 input tokens * $3/M + 150 * 200 output * $15/M)
  Haiku 4.5:   ~$0.55
  GPT-4o-mini: ~$0.10
  Total:       ~$2.35

Run from repo root:
  python scripts/rejudge_v125_gold_subset.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import cohen_kappa_score
from tqdm import tqdm

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from dotenv import load_dotenv
load_dotenv(REPO / ".env")

from src.cache import append_records, existing_keys, load_records
from src.defense_b.judge import ClaudeJudge, GPT4oJudge, HaikuJudge

CACHE = REPO / "cache"
RESULTS = REPO / "results"
GOLD_AUDITED = RESULTS / "judge_gold_subset_audited.csv"
SPML_RELABEL = RESULTS / "judge_gold_subset_spml_relabel_post_audit.csv"
OUT_CSV = RESULTS / "judge_gold_subset_v125.csv"
OUT_MD = RESULTS / "judge_v125_kappa.md"


def _load_gold() -> pd.DataFrame:
    """Load the 150-row audited gold subset and apply the SPML post-audit relabel."""
    df = pd.read_csv(GOLD_AUDITED)
    print(f"Loaded {len(df)} rows from {GOLD_AUDITED.name}")
    print(f"  Dataset distribution: {df['dataset'].value_counts().to_dict()}")
    print(f"  v1.21 human verdicts: {df['human_verdict'].value_counts().to_dict()}")

    # Apply post-audit SPML relabel for the 50 SPML rows
    if SPML_RELABEL.exists():
        relabel = pd.read_csv(SPML_RELABEL)
        relabel_map = dict(zip(relabel["prompt_idx"], relabel["human_verdict"]))
        agent_resp_map = dict(zip(relabel["prompt_idx"], relabel["agent_response"]))
        # Override human_verdict and agent_response for SPML rows present in relabel
        mask = df["prompt_idx"].isin(relabel_map.keys())
        df.loc[mask, "human_verdict"] = df.loc[mask, "prompt_idx"].map(relabel_map)
        df.loc[mask, "agent_response"] = df.loc[mask, "prompt_idx"].map(agent_resp_map)
        print(f"  Applied SPML post-audit relabel to {mask.sum()} rows")
        print(f"  Post-relabel human verdicts: {df['human_verdict'].value_counts().to_dict()}")
    return df


def _run_judge(
    df: pd.DataFrame, judge_fn, cache_path: Path, label: str
) -> pd.DataFrame:
    """Run a judge across all rows, caching to JSONL. Returns df with verdict + reason cols added."""
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    done = existing_keys(cache_path, key="prompt_idx")
    todo = [r for _, r in df.iterrows() if r["prompt_idx"] not in done]
    print(f"\n[{label}] cached={len(done)}, to_judge={len(todo)}")

    for row in tqdm(todo, desc=label):
        pid = row["prompt_idx"]
        ds = str(row.get("dataset", "deepset")).lower()
        oi = row["system_prompt"] if ds == "spml" else None
        result = judge_fn(row.get("prompt", ""), row.get("agent_response", ""), ds, oi)
        append_records(cache_path, [{"prompt_idx": pid, **result}])
        time.sleep(0.05)

    # Merge cache back into df
    cached = {r["prompt_idx"]: r for r in load_records(cache_path) if "prompt_idx" in r}
    df = df.copy()
    df[f"{label}_verdict_v125"] = df["prompt_idx"].map(lambda k: cached.get(k, {}).get("verdict"))
    df[f"{label}_categories_v125"] = df["prompt_idx"].map(
        lambda k: json.dumps(cached.get(k, {}).get("hijack_categories", []))
    )
    df[f"{label}_reason_v125"] = df["prompt_idx"].map(lambda k: cached.get(k, {}).get("reason", ""))
    df[f"{label}_blocked_v125"] = df["prompt_idx"].map(
        lambda k: cached.get(k, {}).get("judge_blocked_v121", False)
    )
    return df


def _binary_verdict(v, ambig_as: str = "HIJACKED") -> str:
    """Collapse {CLEAN, HIJACKED, AMBIGUOUS, blocked} into binary {CLEAN, HIJACKED}.

    Args:
        v: raw verdict string from the judge or human label.
        ambig_as: where AMBIGUOUS verdicts go. Defaults to HIJACKED (matches
            §5.6 reporting convention and §7.6 fail-closed deployment
            semantic). Pass "CLEAN" for the strict-rubric alternative.
    """
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "CLEAN"
    s = str(v).strip().upper()
    if s == "AMBIGUOUS":
        return ambig_as
    if s == "HIJACKED":
        return "HIJACKED"
    return "CLEAN"


def _three_class_verdict(v) -> str:
    """Return CLEAN, HIJACKED, AMBIGUOUS as three distinct categories for kappa."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "CLEAN"
    s = str(v).strip().upper()
    if s in ("CLEAN", "HIJACKED", "AMBIGUOUS"):
        return s
    return "CLEAN"


def _kappa(df: pd.DataFrame, judge_col: str, ambig_as: str = "HIJACKED") -> dict:
    """Cohen's kappa between human verdict and a judge column, binarised."""
    h = df["human_verdict"].map(lambda v: _binary_verdict(v, ambig_as)).values
    j = df[judge_col].map(lambda v: _binary_verdict(v, ambig_as)).values
    valid = (h != "UNKNOWN") & (j != "UNKNOWN")
    kappa = cohen_kappa_score(h[valid], j[valid])
    agree = float((h[valid] == j[valid]).mean())
    n_hij = int((h[valid] == "HIJACKED").sum())
    n_cln = int((h[valid] == "CLEAN").sum())
    return {"kappa": float(kappa), "agreement": agree, "n": int(valid.sum()),
            "n_hijacked": n_hij, "n_clean": n_cln}


def _kappa_3class(df: pd.DataFrame, judge_col: str) -> dict:
    """Cohen's kappa over three distinct verdict categories (no binarisation)."""
    h = df["human_verdict"].map(_three_class_verdict).values
    j = df[judge_col].map(_three_class_verdict).values
    kappa = cohen_kappa_score(h, j)
    return {"kappa": float(kappa), "n": int(len(df))}


def _kappa_drop_ambig(df: pd.DataFrame, judge_col: str) -> dict:
    """Cohen's kappa on the strict-binary subset (rows where BOTH human and judge gave CLEAN or HIJACKED)."""
    h_raw = df["human_verdict"].astype(str).str.strip().str.upper()
    j_raw = df[judge_col].astype(str).str.strip().str.upper()
    mask = h_raw.isin({"CLEAN", "HIJACKED"}) & j_raw.isin({"CLEAN", "HIJACKED"})
    if mask.sum() < 5:
        return {"kappa": float("nan"), "n": int(mask.sum())}
    kappa = cohen_kappa_score(h_raw[mask].values, j_raw[mask].values)
    return {"kappa": float(kappa), "n": int(mask.sum())}


def main() -> None:
    df = _load_gold()

    print("\n=== Running v1.25 across four judges (Sonnet, Haiku, GPT-4o-mini, Opus) ===")
    sonnet = ClaudeJudge()
    haiku = HaikuJudge()
    gpt4mini = GPT4oJudge(model="gpt-4o-mini")
    opus = ClaudeJudge(model="claude-opus-4-7")

    df = _run_judge(df, lambda p, a, d, oi: sonnet.judge_v125(p, a, dataset=d, operator_intent=oi),
                    CACHE / "judge_v125_sonnet_gold_subset.jsonl", "sonnet")
    df = _run_judge(df, lambda p, a, d, oi: haiku.judge_v125(p, a, dataset=d, operator_intent=oi),
                    CACHE / "judge_v125_haiku_gold_subset.jsonl", "haiku")
    df = _run_judge(df, lambda p, a, d, oi: gpt4mini.judge_v125(p, a, dataset=d, operator_intent=oi),
                    CACHE / "judge_v125_gpt4mini_gold_subset.jsonl", "gpt4mini")
    df = _run_judge(df, lambda p, a, d, oi: opus.judge_v125(p, a, dataset=d, operator_intent=oi),
                    CACHE / "judge_v125_opus_gold_subset.jsonl", "opus")

    df.to_csv(OUT_CSV, index=False)
    print(f"\nSaved {OUT_CSV.name} ({len(df)} rows)")

    # Compute kappa for v1.21 (existing) and v1.25 (new), per judge, overall + per dataset
    print("\n=== Kappa: human vs judge, v1.21 (existing) vs v1.25 (new) ===")
    lines = ["# v1.21 vs v1.25 judge kappa on the 150-row audited gold subset",
             "",
             "Cohen's kappa, human verdict (post-SPML-fix) vs judge verdict, binarised CLEAN/HIJACKED.",
             "AMBIGUOUS verdicts counted as HIJACKED (matches §5.6 convention).",
             ""]
    table = ["| Judge | Slice | v1.21 kappa | v1.25 kappa | Delta | n | n_hij | n_clean |",
             "|---|---|---|---|---|---|---|---|"]

    for jname, v21col, v25col in [
        ("Sonnet 4.6", "sonnet_verdict_v121", "sonnet_verdict_v125"),
        ("Haiku 4.5", "haiku45_verdict_v121", "haiku_verdict_v125"),
        ("GPT-4o-mini", "gpt4mini_verdict_v121", "gpt4mini_verdict_v125"),
        ("Opus 4.7", None, "opus_verdict_v125"),
    ]:
        if v25col not in df.columns:
            print(f"  SKIP {jname}: missing column ({v25col})")
            continue
        # Opus has no v1.21 baseline (added in v1.25 iteration); report v1.25 only
        if v21col is None or v21col not in df.columns:
            k25 = _kappa(df, v25col)
            print(f"  {jname:<12}  overall   v1.21=n/a       v1.25 kappa={k25['kappa']:.3f}  delta=n/a    (n={k25['n']})")
            table.append(f"| {jname} | overall | n/a | {k25['kappa']:.3f} | n/a | {k25['n']} | {k25['n_hijacked']} | {k25['n_clean']} |")
            for ds in ["deepset", "neuralchemy", "spml"]:
                sub = df[df["dataset"] == ds]
                if len(sub) < 5:
                    continue
                k25s = _kappa(sub, v25col)
                print(f"  {jname:<12}  {ds:<10}   v1.21=n/a     v1.25={k25s['kappa']:.3f}  delta=n/a    (n={k25s['n']})")
                table.append(f"| {jname} | {ds} | n/a | {k25s['kappa']:.3f} | n/a | {k25s['n']} | {k25s['n_hijacked']} | {k25s['n_clean']} |")
            continue
        k21 = _kappa(df, v21col)
        k25 = _kappa(df, v25col)
        delta = k25["kappa"] - k21["kappa"]
        print(f"  {jname:<12}  overall   v1.21 kappa={k21['kappa']:.3f}  v1.25 kappa={k25['kappa']:.3f}  delta={delta:+.3f}  (n={k25['n']})")
        table.append(f"| {jname} | overall | {k21['kappa']:.3f} | {k25['kappa']:.3f} | {delta:+.3f} | {k25['n']} | {k25['n_hijacked']} | {k25['n_clean']} |")
        for ds in ["deepset", "neuralchemy", "spml"]:
            sub = df[df["dataset"] == ds]
            if len(sub) < 5:
                continue
            k21s = _kappa(sub, v21col)
            k25s = _kappa(sub, v25col)
            ds_delta = k25s["kappa"] - k21s["kappa"]
            print(f"  {jname:<12}  {ds:<10}   v1.21={k21s['kappa']:.3f}  v1.25={k25s['kappa']:.3f}  delta={ds_delta:+.3f}  (n={k25s['n']})")
            table.append(f"| {jname} | {ds} | {k21s['kappa']:.3f} | {k25s['kappa']:.3f} | {ds_delta:+.3f} | {k25s['n']} | {k25s['n_hijacked']} | {k25s['n_clean']} |")

    OUT_MD.write_text("\n".join(lines + table) + "\n")
    print(f"\nSaved {OUT_MD.name}")

    # Verdict-shift summary per judge: what changed v1.21 -> v1.25 (Opus skipped: no v1.21 baseline)
    print("\n=== Verdict shifts v1.21 -> v1.25 (per judge) ===")
    for jname, v21col, v25col in [
        ("Sonnet 4.6", "sonnet_verdict_v121", "sonnet_verdict_v125"),
        ("Haiku 4.5", "haiku45_verdict_v121", "haiku_verdict_v125"),
        ("GPT-4o-mini", "gpt4mini_verdict_v121", "gpt4mini_verdict_v125"),
    ]:
        if v21col not in df.columns or v25col not in df.columns:
            continue
        b21 = df[v21col].map(_binary_verdict)
        b25 = df[v25col].map(_binary_verdict)
        same = (b21 == b25).sum()
        h2c = ((b21 == "HIJACKED") & (b25 == "CLEAN")).sum()
        c2h = ((b21 == "CLEAN") & (b25 == "HIJACKED")).sum()
        print(f"  {jname:<12}  unchanged={same}  HIJACKED->CLEAN={h2c}  CLEAN->HIJACKED={c2h}")

    # Opus 4.7 verdict distribution (v1.25 only; new addition this iteration)
    if "opus_verdict_v125" in df.columns:
        opus_dist = df["opus_verdict_v125"].value_counts().to_dict()
        print(f"  Opus 4.7    v1.25 verdict distribution: {opus_dist}")

    # Supplementary: kappa under four AMBIGUOUS-handling conventions
    # for both v1.21 and v1.25, on the same 150 rows.
    print("\n=== Supplementary kappa under four AMBIGUOUS-handling conventions ===")
    print("  AMBIG=HIJACKED is the primary §5.6 / §7.6 fail-closed convention.")
    print("  Other conventions reported for methodology transparency.")

    supp_lines = [
        "",
        "## Supplementary: kappa under four AMBIGUOUS-handling conventions",
        "",
        "Primary convention (AMBIG=HIJACKED) matches §5.6 reporting and §7.6 fail-closed deployment semantic.",
        "Other conventions reported for methodology transparency.",
        "",
        "| Judge | Rubric | AMBIG=HIJACKED | AMBIG=CLEAN | 3-class | Drop AMBIG (n) |",
        "|---|---|---|---|---|---|",
    ]
    for jname, v21col, v25col in [
        ("Sonnet 4.6", "sonnet_verdict_v121", "sonnet_verdict_v125"),
        ("Haiku 4.5", "haiku45_verdict_v121", "haiku_verdict_v125"),
        ("GPT-4o-mini", "gpt4mini_verdict_v121", "gpt4mini_verdict_v125"),
        ("Opus 4.7", None, "opus_verdict_v125"),
    ]:
        if v25col not in df.columns:
            continue
        # Build rubric/column pairs: skip v1.21 row if Opus (no baseline)
        rubric_pairs = []
        if v21col is not None and v21col in df.columns:
            rubric_pairs.append(("v1.21", v21col))
        rubric_pairs.append(("v1.25", v25col))
        for rubric_label, col in rubric_pairs:
            k_hij = _kappa(df, col, ambig_as="HIJACKED")["kappa"]
            k_cln = _kappa(df, col, ambig_as="CLEAN")["kappa"]
            k3 = _kappa_3class(df, col)["kappa"]
            k_drop = _kappa_drop_ambig(df, col)
            drop_str = f"{k_drop['kappa']:.3f} (n={k_drop['n']})" if not np.isnan(k_drop['kappa']) else f"n/a (n={k_drop['n']})"
            print(f"  {jname:<12} {rubric_label}  AMBIG=HIJ={k_hij:.3f}  AMBIG=CLN={k_cln:.3f}  3class={k3:.3f}  drop={drop_str}")
            supp_lines.append(
                f"| {jname} | {rubric_label} | {k_hij:.3f} | {k_cln:.3f} | {k3:.3f} | {drop_str} |"
            )

    # Append to the existing markdown output
    with OUT_MD.open("a", encoding="utf-8") as f:
        f.write("\n".join(supp_lines) + "\n")
    print(f"\nAppended supplementary table to {OUT_MD.name}")


if __name__ == "__main__":
    main()
