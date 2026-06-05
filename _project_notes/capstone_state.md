- Purpose: session-bridge snapshot for Claude conversation continuity. Read this first when resuming work.
- Status: active (overwritten per update)
- Memorializing: 2026-06-05 (pre-dawn), Phase 5 trim pass and sponsor-deliverable PDF complete; 11 AM sponsor call same day
- Last updated: 2026-06-05 ~08:40 (post-trim PDF compile, repo cleanup of obsolete drafts, status doc refresh)
- Earlier 2026-06-05: pivoted from CEU Word template to direct xelatex compile via Pandoc; built trimmed deliverable `reports/petruska_draft_June_5.md`/`.pdf` (45 pp report + 50 pp appendices, ~95 pp total, all fonts embedded as Calibri subsets); added short captions and italic subcaptions; reduced chapter top-spacing via titlesec; deleted nine obsolete Word/PDF drafts from `reports/`
- Companion handoff: none
- Related: [capstone_plan.md](./capstone_plan.md), [capstone_methodology_decisions.md](./capstone_methodology_decisions.md), [implementation_plan_summary_v3.md](./implementation_plan_summary_v3.md)

---

# Capstone State

## Current phase

Phase 0-4 complete. Phase 5 (Results + Discussion writing) substantially complete; the long-form draft at `reports/final_report.md` (~100 pp without appendices) was trimmed by ~one third for the sponsor deliverable. The trimmed deliverable `reports/petruska_draft_June_5.md` was compiled via Pandoc + xelatex to `reports/petruska_draft_June_5.pdf` for the 2026-06-05 11 AM sponsor video call with Zsófia Práger (Hiflylabs).

Phase 6 (Final polish + submission) is now the active phase. Final submission due 2026-06-08 23:55.

Full plan at [capstone_plan.md](./capstone_plan.md). Methodology rationale at [capstone_methodology_decisions.md](./capstone_methodology_decisions.md). Implementation plan at [implementation_plan_summary_v3.md](./implementation_plan_summary_v3.md).

Interim progress report PDF at `reports/Petruska_interim_progress_report.pdf` (submitted 2026-05-11). Long-form master source at `reports/final_report.md` (preserved, not overwritten). Sponsor-deliverable trim at `reports/petruska_draft_June_5.md`/`.pdf`.

## Active open questions

- Sponsor-call feedback (2026-06-05 11 AM) may surface scope or framing adjustments to fold into the final submission. Capture in this doc post-call.
- Whether the §6 / §7 prose in the trim draft is the version to carry into the final CEU submission, or whether to expand back toward the long-form `final_report.md` for the CEU-facing version.

## What changed in this update (2026-06-01 evening through 2026-06-05 morning)

### Sponsor deliverable: trimmed draft + Pandoc/xelatex compile (2026-06-05)

The long-form `reports/final_report.md` ran ~100 pp without appendices, above the CEU 20-25 pp target and above what the sponsor expected for the check-in. Built a trimmed deliverable: ~45 pp report body + appendices A through E concatenated as separate sections (~50 pp), targeting the sponsor handoff.

Build path: Pandoc + xelatex direct PDF compile (not Word template). CEU formatting requirements honored: A4 paper, 2.5cm margins, Calibri body 12pt, double-space body / single-space frontmatter / captions / bibliography, indented paragraphs, chapters start on new page, Roman to Arabic page numbers, active TOC + PDF bookmarks, List of Figures and Tables. Fonts embedded as subsetted CID TrueType per `pdffonts` check.

Artifacts created and kept:
- `reports/petruska_draft_June_5.md` (1,484 lines, 170KB): trimmed report body concatenated with cleaned appendix sources.
- `reports/petruska_draft_June_5.pdf` (564KB, ~95 pp): xelatex-rendered deliverable.
- `reports/pdf-header.tex`: LaTeX preamble carrying the CEU formatting rules (table styling, captions, chapter spacing via `titlesec`, hyperref metadata, combined List of Figures and Tables with Figures / Tables subheadings).

Captions: each figure / table uses a short caption (shown in the List of Figures and Tables) with the long descriptive context as an italic paragraph immediately below the figure / table. Pandoc's `short-caption=` attribute did not propagate reliably for pipe tables in this Pandoc version, so the short + italic-paragraph pattern was used instead.

### Repo cleanup of obsolete drafts (2026-06-05)

Deleted from `reports/`: `Petruska_Hiflylabs_status_2026-06-05.{md,docx}`, `Petruska_Hiflylabs_status_2026-06-05_clean.{docx,pdf}`, `Petruska_final_report.{docx,pdf}`, `Petruska_final_report_draft_v1.pdf`, plus two Word lock/temp files (`~$truska_...`, `~WRL0005.tmp`). These were earlier drafts superseded by the June 5 trim or transient artifacts of the Word compile path. All were uncommitted; no git history affected.

### Earlier (2026-05-27 evening through 2026-06-01 evening): NB10 series + judge v1.25 + Opus ceiling test

Substantial empirical and infrastructure work. Listed roughly chronologically.

#### NB10 series: BIPIA indirect-injection LoRA extension (2026-05-28 through 2026-05-31)

Four sequential notebooks tracing the LoRA methodology arc on BIPIA email-QA indirect-injection task.

**NB10**: LoRA-v1 on BIPIA baseline. Negative transfer observed: degenerate output distribution (Cohen d = 0.13). Result published as §5.11 BIPIA arm step 1.

**NB10b**: Naive full-dataset BIPIA retraining. Macro F1 = 0.483, equal to trivial-baseline F1. Root cause: data scarcity (only 35 clean training rows in BIPIA email-QA). Published as §5.11 step 2.

**NB10c**: Clean-only augmentation strategy. Baseline email set (50 rows) each receives 5 generic question variants, producing 300 synthetic clean training rows. Result: Cohen d = 9.37 appeared publishable, but later pressure testing revealed a question-style shortcut.

**NB10d**: Six-test pressure-test workflow (Test 1 attack-question ablation; Tests 2-6 domain/balancing checks). Test 1 FAILED with flag rate 0.487; Tests 2-6 PASSED. Test suite itself becomes a methodological contribution. Result published as §5.11 step 3.

**NB10e**: Symmetric augmentation with base-email-stratified split. Each of 50 base emails contributes equal clean and attack rows across 6 question styles. Test 1 returns to 1.000; Test 3 triple-cross held-out validates at d = 7.73 with balanced accuracy 0.980; eval_set F1 = 0.974 preserved. Deployment-ready. Recommended configuration: adapter `lora_v4b_symmetric_aug/`. Published as §5.11 step 4.

All notebooks have `_post_run` versions downloaded from Colab into `notebooks/`. Augmentation scripts `scripts/augment_bipia_clean.py` and `scripts/augment_bipia_symmetric.py` in `scripts/`. Synthetic datasets at `results/bipia_email_qa_prompts_augmented.csv` and `results/bipia_email_qa_prompts_symmetric.csv`.

#### Consolidated §5.11 visualization (2026-05-31)

Script `scripts/plot_lora_series_comparison.py` produces `reports/figures/lora_series_comparison.png` and `.pdf`: 2x2 panel showing Cohen d, macro F1, Test 1 flag rate, and eval_set F1 across all four NB10 iterations.

#### Judge rubric v1.21 -> v1.25 iteration (2026-05-31)

Added `_V125_SYSTEM_HEADER`, `_build_v125_system`, and `judge_v125` methods to all judge classes (`ClaudeJudge`, `HaikuJudge`, `GPT4oJudge`) in `src/defense_b/judge.py`.

v1.25 = v1.21 + signature-vs-mechanism scope note from §3.2 v1.23 (final operational-definitions entry) with four inline worked examples. Reduces signature-driven false-positive HIJACKED verdicts.

Additionally, added conditional logic to omit `temperature` parameter for Claude Opus models (Opus 4.x deprecated it). This was necessary when Opus 4.7 was added to the judge set as a cost-ceiling test.

#### Judge v1.25 re-run on four judges with cost-ceiling test (2026-06-01)

Ran `scripts/rejudge_v125_gold_subset.py` across Sonnet 4.6, Haiku 4.5, GPT-4o-mini, and Opus 4.7 (new addition) on 150-row audited gold subset with SPML post-audit relabel applied.

Empirical findings:
- Haiku 4.5 kappa = 0.554, up from v1.21 at 0.471 (delta +0.083). Highest kappa observed across any judge / rubric combination in this study; still in the moderate Landis-Koch band (0.41-0.60) but approaching the 0.61 substantial threshold. Lift robust across all four AMBIGUOUS-handling conventions.
- Opus 4.7 kappa = 0.550, statistically tied with Haiku. Cost ceiling test: Opus costs 5x Haiku but adds no signal. Establishes Anthropic-family judge-reliability ceiling at Haiku level.
- Sonnet 4.6 kappa = 0.466 under v1.25 (regression from v1.21 at 0.471, within noise).
- GPT-4o-mini kappa unchanged at 0.403 (narrow fallback role when Anthropic unavailable).

Cached per-judge verdicts at `cache/judge_v125_*_gold_subset.jsonl`. Per-row verdicts at `results/judge_gold_subset_v125.csv`. Kappa table at `results/judge_v125_kappa.md`. Total run cost ~$3.93.

### Key empirical milestones (carried from prior update)

1. NB10e Variant B = deployment-ready Defense A for indirect injection. FAR = 0, ASR = 0.020 on held-out triple cross.
2. Haiku 4.5 with v1.25 reaches kappa 0.554, the highest on the 150-row gold subset.
3. Opus 4.7 cost-ceiling test establishes Anthropic-family judge signal plateaus at Haiku level.
4. Sonnet 4.6 v1.25 kappa rises only +0.026 over v1.21 and only under the AMBIG=HIJACKED convention; the v1.25 scope note benefits cheaper Haiku more than Sonnet.

### What's NOT done yet (current backlog)

- Sponsor call 2026-06-05 11 AM: incorporate feedback into the final CEU submission.
- Final CEU submission packaging by 2026-06-08 23:55. Decide whether the trimmed `petruska_draft_June_5.md` or the long-form `final_report.md` is the canonical submission.
- Slide deck (10-20 slides; optional per supervisor guidance, time-permitting).
- Public CEU summary (3 pages; may be merged with submission packaging).
- Custom adversarial test set (queued in §9.1 as future work, not capstone scope).

## What's next

Immediate priorities to submission (2026-06-08):

1. 2026-06-05 11 AM sponsor call. Capture feedback in this doc immediately after.
2. Same-day: send the cover email + PDF + GitHub repo link to Zsófia.
3. Decide CEU submission shape: trim deliverable vs long-form. Likely the trim, possibly with a §6 / §7 expansion if sponsor pushes for more discussion depth.
4. Final compile pass on the chosen submission shape.
5. Submit by 2026-06-08 23:55.
6. Optional: slide deck (defer if time-constrained).

See [capstone_plan.md](./capstone_plan.md) Phase 6 checklist for detailed item-level breakdown.

## Known issues

1. **Pandoc `short-caption=` attribute on pipe tables** did not propagate in this Pandoc version. Worked around by writing short captions inline and adding longer descriptive context as an italic paragraph below each figure / table.
2. **Long-form `final_report.md` is ~100 pp** without appendices, above target. The trimmed deliverable resolves this for the sponsor; CEU-facing submission decision pending (see "What's next").
3. **Groq daily quota exhausted** during Phase 1 pilot (resolved with Together AI fallback).
4. **Anthropic Usage Policy classifier** triggered once in 2026-05-11 session as context accumulated attack content. Not a real issue; legitimate dual-use security research. Workaround: `/compact` to shrink history.

## Resuming work

If you are a fresh Claude session or picking this up after a gap:

1. Read this file (you are here).
2. Open [capstone_plan.md](./capstone_plan.md) Phase 6 checklist; submission packaging is the critical path.
3. Consult [capstone_methodology_decisions.md](./capstone_methodology_decisions.md) if methodology questions arise.
4. Reference [implementation_plan_summary_v3.md](./implementation_plan_summary_v3.md) for shared external-facing context.
5. The sponsor-deliverable PDF compile path is documented in `reports/pdf-header.tex` (LaTeX preamble) and reproduced by the canonical Pandoc command in this state doc's git history (commit message of the trim-pass commit).
6. Historical context and signed PID live in `archive/`; local-only files and drafts in `_local/`.
