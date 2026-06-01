- Purpose: session-bridge snapshot for Claude conversation continuity. Read this first when resuming work.
- Status: active (overwritten per update)
- Memorializing: 2026-06-01 (evening), Phase 2 and 3 stretch work complete, final report substantially drafted, submission-ready
- Last updated: 2026-06-01 evening (NB10 series Defense A LoRA indirect-injection extension complete; v1.25 judge rubric deployed; Opus 4.7 judge-reliability ceiling test complete; all final report sections 1-9 drafted [§6, §7 marked DRAFT])
- Earlier today 2026-06-01: NB10e symmetric augmentation final deployment path validated; judge v1.25 re-run on four judges with Opus added; notebooks/README.md rewritten as methodology map; reports sections updated throughout
- Companion handoff: none (work is flowing; see "Resuming work" section below for continuity)
- Related: [capstone_plan.md](./capstone_plan.md), [capstone_methodology_decisions.md](./capstone_methodology_decisions.md), [implementation_plan_summary_v3.md](./implementation_plan_summary_v3.md)

---

# Capstone State

## Current phase

Phase 0 (Foundation) complete. Phase 1 (Core Pipelines Build) complete. Phase 2 (Judge Validation and Interim Deliverable) complete. Phase 3 (Analysis and Stretch Goals) substantially complete with extension into BIPIA Phase 2 (full LoRA methodology arc). 

All empirical work is now frozen. Remaining work: final-report §6 Discussion and §7 Business Framework (currently DRAFT status), sponsor handoff summary, optional slide deck. Submission deadline 2026-06-08.

Scope constraint from Zoltan Toth (2026-05-13) was fully honored: existing work (judge validation, BIPIA pilot, cross-family judge robustness) completed before stretch goals (LoRA extension, Opus ceiling test). This enabled the Phase 3 stretch work on NB10 series and judge v1.25 iteration without busting the time budget.

Full plan at [capstone_plan.md](./capstone_plan.md). Methodology rationale at [capstone_methodology_decisions.md](./capstone_methodology_decisions.md). Implementation plan at [implementation_plan_summary_v3.md](./implementation_plan_summary_v3.md).

Interim progress report PDF at `reports/Petruska_interim_progress_report.pdf` (submitted 2026-05-11). Final report in-progress at `reports/final_report.md`.

## Active open questions

- None. All Phase 0-3 methodology and empirical questions have been resolved and documented.
- Remaining work: final-report prose completion (Discussion and Business Framework sections), Hiflylabs sponsor summary, optional slide deck.

## What changed in this update (2026-05-27 evening through 2026-06-01 evening)

Substantial empirical and infrastructure work, covering Defense A LoRA indirect-injection extension, judge rubric iteration, cross-judge validation, and final-report integration. Listed roughly chronologically.

### NB10 series: BIPIA indirect-injection LoRA extension (2026-05-28 through 2026-05-31)

Four sequential notebooks tracing the LoRA methodology arc on BIPIA email-QA indirect-injection task.

**NB10**: LoRA-v1 on BIPIA baseline. Negative transfer observed: degenerate output distribution (Cohen d = 0.13). Result published as §5.11 BIPIA arm step 1.

**NB10b**: Naive full-dataset BIPIA retraining. Macro F1 = 0.483, equal to trivial-baseline F1. Root cause: data scarcity (only 35 clean training rows in BIPIA email-QA). Published as §5.11 step 2.

**NB10c**: Clean-only augmentation strategy. Baseline email set (50 rows) each receives 5 generic question variants, producing 300 synthetic clean training rows. Result: Cohen d = 9.37 appeared publishable, but later pressure testing revealed a question-style shortcut.

**NB10d**: Six-test pressure-test workflow (Test 1 attack-question ablation; Tests 2-6 domain/balancing checks). Test 1 FAILED with flag rate 0.487; Tests 2-6 PASSED. Test suite itself becomes a methodological contribution. Result published as §5.11 step 3.

**NB10e**: Symmetric augmentation with base-email-stratified split. Each of 50 base emails contributes equal clean and attack rows across 6 question styles. Test 1 returns to 1.000; Test 3 triple-cross held-out validates at d = 7.73 with balanced accuracy 0.980; eval_set F1 = 0.974 preserved. Deployment-ready. Recommended configuration: adapter `lora_v4b_symmetric_aug/`. Published as §5.11 step 4.

All notebooks have `_post_run` versions downloaded from Colab into `notebooks/`. Augmentation scripts `scripts/augment_bipia_clean.py` and `scripts/augment_bipia_symmetric.py` in `scripts/`. Synthetic datasets at `results/bipia_email_qa_prompts_augmented.csv` and `results/bipia_email_qa_prompts_symmetric.csv`.

### Consolidated §5.11 visualization (2026-05-31)

Script `scripts/plot_lora_series_comparison.py` produces `reports/figures/lora_series_comparison.png` and `.pdf`: 2x2 panel showing Cohen d, macro F1, Test 1 flag rate, and eval_set F1 across all four NB10 iterations.

### Judge rubric v1.21 -> v1.25 iteration (2026-05-31)

Added `_V125_SYSTEM_HEADER`, `_build_v125_system`, and `judge_v125` methods to all judge classes (`ClaudeJudge`, `HaikuJudge`, `GPT4oJudge`) in `src/defense_b/judge.py`. 

v1.25 = v1.21 + signature-vs-mechanism scope note from §3.2 v1.23 (final operational-definitions entry) with four inline worked examples. Reduces signature-driven false-positive HIJACKED verdicts.

Additionally, added conditional logic to omit `temperature` parameter for Claude Opus models (Opus 4.x deprecated it). This was necessary when Opus 4.7 was added to the judge set as a cost-ceiling test.

### Judge v1.25 re-run on four judges with cost-ceiling test (2026-06-01)

Ran `scripts/rejudge_v125_gold_subset.py` across Sonnet 4.6, Haiku 4.5, GPT-4o-mini, and Opus 4.7 (new addition) on 150-row audited gold subset with SPML post-audit relabel applied.

Empirical findings:
- Haiku 4.5 kappa = 0.554, up from v1.21 at 0.471 (delta +0.083). Highest kappa observed across any judge / rubric combination in this study; still in the moderate Landis-Koch band (0.41-0.60) but approaching the 0.61 substantial threshold. Lift robust across all four AMBIGUOUS-handling conventions.
- Opus 4.7 kappa = 0.550, statistically tied with Haiku. Cost ceiling test: Opus costs 5x Haiku but adds no signal. Establishes Anthropic-family judge-reliability ceiling at Haiku level.
- Sonnet 4.6 kappa = 0.466 under v1.25 (regression from v1.21 at 0.471, within noise).
- GPT-4o-mini kappa unchanged at 0.403 (narrow fallback role when Anthropic unavailable).

Cached per-judge verdicts at `cache/judge_v125_*_gold_subset.jsonl`. Per-row verdicts at `results/judge_gold_subset_v125.csv`. Kappa table at `results/judge_v125_kappa.md`. Total run cost ~$3.93.

### Final report sections updated (2026-05-27 through 2026-06-01)

- §5.8: Forward pointer to §5.11 (NB10e) explaining that the 38% FAR and 65.6% ASR are off-the-shelf measurements that motivated the §5.11 fix, not deployment numbers.
- §5.11: Full BIPIA arm rewrite with four iterations (NB10 a-d) and deployment recipe (NB10e). Now the capstone's main stretch-goal contribution.
- §6.3: Judge reliability discussion refreshed with five measurements now including Opus ceiling test.
- §7.4: Opus added to cost table. Recommendation framing flattened to Haiku across all cost tiers.
- §7.10: NB10e documented as operational template for periodic-retrain cycle.

### notebooks/README.md rewritten as methodology map (2026-06-01)

Complete rewrite covering all phases (matches `notebooks/README.md`):
- Phase 0: 01_data_validation, 02_eval_set_construction, 04_contamination_check.
- Phase 1 Defense A baseline: 05_defense_a_pilot, 06_defense_a_neuralchemy, 07_defense_a_spml, 06_augmentation_run (scaffolded but not executed; prompt augmentation arm was deprioritised), colab_defense_a (GPU batched inference).
- Phase 2 Defense B and BIPIA: 08_bipia_email_qa, 09_analysis_and_plots (Wilson CIs, cross-dataset variance, judge reliability).
- Phase 3 stretch: 08_defense_a_lora_finetune (§5.11 LoRA on direct injection with 5-config robustness), 09_defense_c_distillation (DistilBERT student for OR-gate distillation).
- Phase 4 NB10 series: 10 / 10b / 10c / 10d / 10e (LoRA v1 through v4 on BIPIA indirect injection, pressure-test workflow in NB10d, symmetric augmentation in NB10e).
- The 500-row Defense B pilot was executed via `scripts/run_defense_b_pilot.py` (Together AI), not via a notebook.
- The 200-row label audit was executed via `scripts/` not via a notebook.

### Plan B' (AgentDojo BF16 reproduction) confirmed DOA (2026-05-30)

Not pursued. Rationale: infrastructure is possible, but the result would not change deployment recommendations. Stays as honest §5.9 infrastructure-tier framing (currently [DRAFT]).

### Key empirical milestones this session

1. NB10e Variant B = deployment-ready Defense A for indirect injection. FAR = 0, ASR = 0.020 on held-out triple cross. First Hiflylabs-applicable result in the capstone.
2. Haiku 4.5 with v1.25 reaches kappa 0.554, the highest on the 150-row gold subset (up from 0.471 under v1.21). Still in the moderate Landis-Koch band (0.41-0.60) but approaching the 0.61 substantial threshold and the highest kappa observed across any judge / rubric combination in this study.
3. Opus 4.7 cost-ceiling test establishes that Anthropic-family judge signal plateaus at Haiku level (Opus kappa 0.550 vs Haiku 0.554 at 5x the cost), justifying cost-optimised deployment recommendation.
4. Sonnet 4.6 v1.25 kappa rises only +0.026 over v1.21 (0.466 vs 0.440) and only under the AMBIG=HIJACKED convention; under stricter conventions Sonnet v1.25 is essentially tied with v1.21. The v1.25 scope note benefits cheaper Haiku more than it benefits Sonnet, possibly because Haiku's pre-iteration reasoning leaned more heavily on signature pattern matching.

### What's NOT done yet (current backlog)

- §6 Discussion and §7 Business Framework still tagged [DRAFT].
- Sponsor handoff summary for Hiflylabs / Zsófia Práger.
- Slide deck (10-20 slides, optional).
- Custom adversarial test set (queued in §9.1 as future work, not capstone scope).

## What's next

Immediate priorities to submission (2026-06-08):

1. Complete §6 Discussion (interpretation, tradeoffs, limitations, threats to validity): ~4-5 hours.
2. Complete §7 Business Framework (cost/latency decision trees, Hifly-specific recommendations, operational deployment checklist): ~3-4 hours.
3. Executive summary (§0): ~2 hours.
4. Top-to-bottom final edit pass on all sections: ~4-5 hours.
5. Sponsor handoff summary (3-5 pages, 2 hours).
6. Optional: slide deck (10-12 hours, defer if time-constrained).

Final submission due 2026-06-08. 7 days remaining from 2026-06-01.

See [capstone_plan.md](./capstone_plan.md) Phase 6 checklist for detailed item-level breakdown.

## Known issues

1. **Reports use raw LaTeX `\newpage` and `\tableofcontents`** in markdown. VSCode preview and GitHub render as plain text; only Pandoc honors during PDF compilation.
2. **Groq daily quota exhausted** during Phase 1 pilot (resolved with Together AI fallback).
3. **Anthropic Usage Policy classifier** triggered once in 2026-05-11 session as context accumulated attack content. Not a real issue; legitimate dual-use security research. Workaround: `/compact` to shrink history.

## Resuming work

If you are a fresh Claude session or picking this up after a gap:

1. Read this file (you are here).
2. Open [capstone_plan.md](./capstone_plan.md) Phase 6 checklist; items 1-5 under "Report completion" are the critical path.
3. Consult [capstone_methodology_decisions.md](./capstone_methodology_decisions.md) if methodology questions arise.
4. Reference [implementation_plan_summary_v3.md](./implementation_plan_summary_v3.md) for shared external-facing context.
5. NB10 series notebooks (10, 10b, 10c, 10d, 10e and their `_post_run` versions) contain the LoRA methodology arc. Read their markdown cells for the pressure-test framework logic.
6. Historical context and signed PID live in `archive/`; local-only files and drafts in `_local/`.
