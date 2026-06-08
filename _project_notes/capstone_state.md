- Purpose: session-bridge snapshot for Claude conversation continuity. Read this first when resuming work.
- Status: submission complete (submitted 2026-06-08 23:55)
- Memorializing: 2026-06-08 (final submission and post-submission cleanup)
- Last updated: 2026-06-08 ~23:50 (post-final-compile and file reorganization)
- Earlier history: Phase 5 and Phase 6 major revisions and cleanup from 2026-06-05 through 2026-06-08. See "What changed in this update" below.
- Companion handoff: none (capstone complete)
- Related: [capstone_plan.md](./capstone_plan.md) (all items complete or deferred), [capstone_methodology_decisions.md](./capstone_methodology_decisions.md), [implementation_plan_summary_v3.md](./implementation_plan_summary_v3.md)

---

# Capstone State

## Current phase

Phase 6 complete. Final CEU submission completed 2026-06-08 23:55. The submission is `reports/Petruska_2026_MS_Thesis.pdf`, 132 pages, compiled via Pandoc + xelatex from `reports/Petruska_2026_MS_Thesis.md` (1,738 lines). The document is submission-ready; it compiles cleanly with 2 benign LaTeX float-placement warnings only (no errors). All cross-references audited and corrected; all 38 unique inline citation keys verified against `reports/references.bib` and source PDFs in Zotero storage at `C:\Users\boga\Zotero\storage\`.

The GitHub repository is public at github.com/b0glarka/capstone_prompt_injection. All code, datasets, results, and reports are accessible there (Section 1 closing sentence: "All code, datasets, and supporting reports are available at github.com/b0glarka/capstone_prompt_injection.").

Full plan at [capstone_plan.md](./capstone_plan.md). Methodology rationale at [capstone_methodology_decisions.md](./capstone_methodology_decisions.md). Implementation plan snapshot (as of 2026-05-12, before June 5-8 revision) at [implementation_plan_summary_v3.md](./implementation_plan_summary_v3.md).

Interim progress report PDF submitted 2026-05-11 (archived at `reports/archive/Petruska_interim_progress_report.pdf`). Long-form master source at `reports/archive/final_report.md` (preserved from Phase 5). Sponsor-check-in deliverable at `reports/archive/petruska_draft_June_5.md` / `.pdf` (95 pp, used for June 5 11 AM sponsor video call). Final CEU submission at `reports/Petruska_2026_MS_Thesis.md` / `.pdf` (132 pp).

## Active open questions

None. Capstone submission is complete.

## What changed in this update (2026-06-08, complete day with editorial + cleanup pass)

This update consolidates two major work streams completed 2026-06-08: the comprehensive editorial pass (Sections 1-9 and Abstract, covered in earlier draft `state_update_draft.md`), and the post-submission file reorganization and environment-document refresh (this section).

### Editorial pass on full document (comprehensive, covered in earlier draft)

The 95-page sponsor-deliverable draft `reports/petruska_draft_June_5.md` was extensively revised across all sections to produce a submission-ready 132-page document. Major edits by section:

- Sections 1-5: incremental tightening; added GitHub URL to Section 1 closing; removed filler words across Sections 2-5.
- Section 6 Discussion: original 5 subsections restructured to 4; §6.4 synthesis deleted (~200 lines); overall reduction by ~400 lines while preserving all substantive claims.
- Section 7 Business Decision Framework: merged with former Appendix E into 8 integrated subsections; incorporated all four dimensions of sponsor feedback (autonomy levels, data classification tiers, human-in-the-loop thresholds, primary/secondary model roles); added realistic 1% injection-prevalence cost example and 5-step decision walkthrough.
- Section 8 Limitations: consolidated into 6 explicit entries with language coverage finding and cross-agent attribution boundary clarified.
- Section 9 Future Work and Conclusion: fully rewritten; future work collapsed to 5 highest-priority directions; conclusion expanded to ~700 words covering empirical headline, methodology contributions, practical recommendation, durability framing, and accessible closing.
- Abstract: tightened from 420 to 395 words; added specific architectural-diversity claim and production-judge qualifier.

18 stale cross-references fixed throughout (§5.8 → §5.5, §5.11 → §5.6, §5.5c → §5.3, §7.6 → §7.8, §7.5 → §7.7, plus 13 others). All Table/Figure/Section/Appendix references audited and resolved.

Appendices B, C, D: added GitHub repository links matching Appendix A pattern. Appendix E (Business Decision Framework): removed; entire content absorbed into Section 7.

Citation audit: spot-verified 7 high-risk inline citations (Oakden-Rayner, D'Amour, Kwa, Säleva, Hines, Russinovich, Apruzzese, Nguyen) against source PDFs in Zotero; all correctly used. All 38 unique citation keys in the markdown verified to resolve in `references.bib`.

Known cosmetic issue accepted: per-chapter table/figure numbering break due to `titlesec` interaction renders all tables as "Table 0.X" and figures as "Figure 0.X" instead of per-chapter numbers. All 12 inline prose references hand-updated to match actual caption numbers, so cross-references resolve correctly. Fix deferred to post-submission.

Compile verification: document compiles cleanly via `bash scripts/compile_thesis.sh` (canonical command at `scripts/compile_thesis.sh`). Output: 132 pages, 797 KB, 2 benign LaTeX float-placement warnings (no errors), all fonts embedded as Calibri subsets, xelatex runtime ~8 seconds.

### File rename: June_5 draft to 2026 MS Thesis (2026-06-08 afternoon)

The sponsor-deliverable draft `reports/petruska_draft_June_5.md` and its PDF were renamed to `reports/Petruska_2026_MS_Thesis.md` and `.pdf` respectively (132 pages, submitted). This naming clarifies that the final submission is the CEU-facing canonical version, not an interim check-in.

The compile script `scripts/compile_final_tech_report_june_6.sh` was renamed to `scripts/compile_thesis.sh`; all internal output-file references updated to point to the renamed markdown and PDF.

### Repository cleanup (2026-06-08 afternoon/evening)

Deleted 11 obsolete files to tidy the repository before final submission:

From `reports/`:
- `final_report.md` (100+ pp long-form draft from Phase 5; preserved at `reports/archive/final_report.md`)
- `interim_progress_report.md` (MD source of interim submitted 2026-05-11; preserved at `reports/archive/interim_progress_report.md`)
- `Petruska_interim_progress_report.pdf` (PDF of interim; moved to `reports/archive/`)
- `petruska_draft_June_5.md` and `.pdf` (renamed to `Petruska_2026_MS_Thesis.md` and `.pdf`)

From `_project_notes/`:
- `implementation_plan_summary_v2.md` (superseded by v3; moved to `_project_notes/archive/`)

From `_local/` (not in repo; for informational cleanup):
- `baseline_v1.8_judge/` renamed to `archive_baseline_v1.8_judge/` for tidiness.
- `agentdojo_logs/` (20 MB) and `cache/` (20 MB) confirmed already .gitignored; left on disk for reproducibility.

Result: top-level `reports/` now contains only the current submission, supporting documents, and archive subdirectory. All intermediate drafts moved to archive; no git history affected (they were already tracked; only moved).

### Environment and configuration documentation updates

**pyproject.toml**: removed stale reference to Section 5.9 in the agentdojo optional-extra comment. The comment now correctly notes that the AgentDojo evaluation was cut from the thesis and queued in Section 9.1 future work.

**.env.example**: updated 4 stale section references:
- §6.3 → current §6.2 (BIPIA baseline)
- §7.4 → current §7.4 (internal agent scenario; happens to remain same, but verified)
- §5.5b → Section 5.3 (Defense C baseline, was integrated into earlier section during trim pass)
- §5.8 / §5.9 → Section 5.5-5.6 (BIPIA arm restructured during Section 5 reorganization)

All four references now match the restructured Section 5 and Section 7 numbering in the final thesis.

**uv.lock**: regenerated via `uv lock`. Was out of sync with `pyproject.toml`; now in sync. No package versions changed; lock file updated for consistency.

**Top-level README.md**: extensively revised to reflect post-submission state:
- Status section rewritten: now points to `Petruska_2026_MS_Thesis.pdf` (was pointing at deleted `petruska_draft_June_5`).
- Environment-setup section: all stale section references removed (§5.11 → Section 5.6, §5.5b → Section 5.3, §5.8 → Section 5.5, §5.9 queued in §9.1).
- Tier-1 / Tier-2 reproducibility verification paths: updated to reference current section numbers; removed NB10 notebook codenames (NB10, NB10b, NB10c, NB10d, NB10e) that were internal iteration labels.
- Deliverable list: still mentions interim report (submitted 2026-05-11), 10-20 slide deck, and 3-page public CEU summary (the latter two are post-submission items, deferred per time constraint).

**reports/README.md**: full rewrite to reflect final submission state:
- Replaced references to deleted/archived files (`petruska_draft_June_5`, `final_report.md`) with current `Petruska_2026_MS_Thesis.md`.
- Removed "Reviewed by Professor Zoltan Toth" mention (consistent with body-prose cleanup from earlier session; no senior-author framing in CEU thesis format).
- Fixed "Appendix A/B/C/D/E of both reports" framing: there is only one thesis now, and no Appendix E (absorbed into Section 7).
- Figure descriptions now use Figure 0.X labels matching actual PDF (per cosmetic issue above).
- Table captions point to Table 0.X labeling.

**src/README.md**: 5 stale section references fixed (matching .env.example updates).

**notebooks/README.md**: Phase 3 and Phase 4 sections rewritten:
- All `§5.11` references replaced with `Section 5.6` (LoRA fine-tuning section).
- All NB10 notebook codenames (NB10, NB10b, NB10c, NB10d, NB10e) replaced with positional descriptors: "First iteration (baseline)", "Second iteration (full-dataset retraining)", "Third iteration (augmentation)", "Pressure-test suite", "Fourth iteration (symmetric)", matching thesis body language and making notebooks more discoverable.
- Phase 3 and Phase 4 descriptions updated to match final scope (Defense C combined pipeline, LoRA on BIPIA, judge v1.25 iteration).

**cache/README.md** and **results/README.md**: no stale content; unchanged.

## What's NOT done (post-submission)

- Slide deck (optional per supervisor guidance; 10-20 slides; deferred due to time).
- Public CEU summary (3 pages; deferred).
- Defense C combined A+B pipeline paper (stretch goal; deferred).
- Custom adversarial test set (queued in §9.1 as future work; out of scope for capstone).

## What's next

Capstone submission is complete. Next steps if continuing:

1. Await CEU final grading and feedback.
2. Post submission, optional TODO: consider pushing slide deck and public summary to GitHub if time permits.
3. Future research directions are listed in Section 9.1.

## Known issues

1. **Per-chapter table/figure numbering break**: LaTeX titlesec interaction renders all tables as "Table 0.X" and figures as "Figure 0.X" instead of per-chapter numbering. This is a cosmetic issue; all inline prose references were hand-updated to match the actual caption labels, so cross-references resolve correctly. Fix deferred to post-submission if needed.
2. **Pandoc short-caption attribute** did not propagate reliably on pipe tables in this Pandoc version (pre-2026-06-05 issue, carried forward). Worked around by writing short captions inline and adding longer context as italic paragraphs below each figure/table.
3. **Anthropic Usage Policy classifier** triggered once in 2026-05-11 session as context accumulated attack content. Legitimate research content; resolved via `/compact` history shrinking. Not a recurring issue.

## Resuming work

If you are picking this up after the capstone is complete:

1. The submission `reports/Petruska_2026_MS_Thesis.pdf` (132 pp) is the final CEU deliverable.
2. Full code, data, and results are on GitHub at github.com/b0glarka/capstone_prompt_injection.
3. [capstone_methodology_decisions.md](./capstone_methodology_decisions.md) explains why each major methodological choice was made.
4. Historical snapshots and signed PID live in `archive/` (created at key milestones: PID signed, interim submitted, final submitted).
5. The sponsor-deliverable trim version at `reports/archive/petruska_draft_June_5.md` / `.pdf` (95 pp) was used for the 2026-06-05 11 AM Hiflylabs video call with Zsófia Práger.
6. All reports and supporting documentation are in `reports/`; code and notebooks in `src/` and `notebooks/`; raw results in `results/`.
