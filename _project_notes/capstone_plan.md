- Purpose: active work tracker with phases, checkboxes, hours, dependencies. Check off items as they are done.
- Status: active
- Created: 2026-04-21
- Last edited: 2026-06-05 (checkbox sweep covering Phase 5 §6 / §7 prose done via trim pass + appendices, Phase 6 trim-and-compile complete for sponsor deliverable; remaining unchecked items are sponsor-call follow-up, final CEU submission packaging, slide deck, public summary)
- Related: [capstone_methodology_decisions.md](./capstone_methodology_decisions.md) (why each choice), [capstone_state.md](./capstone_state.md) (current snapshot)

---

# Capstone Plan of Action

Interim due 2026-05-11. Final due 2026-06-08. Decision rationale lives in [capstone_methodology_decisions.md](./capstone_methodology_decisions.md).

## How to use

- Check boxes as work completes.
- Hours are estimates; revise inline if they prove wrong.
- Phase boundaries are the schedule, not daily targets.
- Only bump "Last edited" above when structure changes (new phase, new task), not per checkbox.
- Go/no-go checkpoints are explicit; do not expand scope without hitting them.

## Time budget

- Available: 30+ hrs/week × 7 weeks = 210+ hrs
- Blackouts: DS4 exam prep ~8 hrs (May 17-20), geospatial project ~10 hrs (May 22-25)
- Net capstone: ~192 hrs, Scope estimate: ~175 hrs, Buffer: ~17 hrs

## Deferred scope additions (go/no-go at checkpoints)

Not in baseline. Decide at phase checkpoints.

- Custom adversarial test set (50-100 crafted prompts)
- Defense transfer analysis
- Error taxonomy on false negatives
- Defense C combined A+B pipeline
- BIPIA expansion beyond email QA
- Prompt augmentation decomposition (5 variants)
- Second-annotator gold labeling

---

## Phase 0: Foundation (Apr 21 - Apr 27)

Target: ~17 active hrs. Goal: everything needed before running any defense is in place.

### Setup and structure

- [x] Repo structure (src, notebooks, cache, results, reports) with READMEs
- [x] Top-level README rewritten with setup instructions
- [x] .gitignore updated for cache, figures, checkpoints
- [x] `data_validation.ipynb` moved to `notebooks/01_data_validation.ipynb`, paths repo-root-relative
- [x] Report outline drafted at `reports/final_report_outline.md`
- [x] Verify moved notebook runs end-to-end from new location
- [x] Migrate from conda to uv (`pyproject.toml` + `uv.lock`); supersedes the planned `environment.yml` pin
- [x] Add short note in README about Colab-vs-local hybrid workflow (done 2026-05-11)

### Methodological foundation

- [x] **Operational definitions document** at `reports/operational_definitions.md` (done 2026-05-08, iterated to v1.8 by 2026-05-11)
  - Anchor definition of "prompt injection" on OWASP LLM01 + Greshake et al. 2023
  - Anchor definition of "hijacked agent response" on BIPIA categories (task execution, info gathering, ad insertion, phishing) + Greshake taxonomy
  - Binary decision tree with 10-15 worked examples drawn from the three datasets
  - This is an appendix in the final report
- [x] **Label audit** (done 2026-05-27; full Phase 2 breakdown checked off at lines 156-167 below; canonical post-audit at `results/label_audit_sample_disagreement_sorted_post_audit.csv`; report at `reports/label_audit_report.md`; overall kappa 0.930 [0.878, 0.970])
- [x] **Contamination check for Defense A classifiers** (done 2026-04-24, see `results/contamination_report.md`)
  - ProtectAI DeBERTa V2 named sources cross-referenced with deepset, neuralchemy, SPML
  - Result: max 1.96% overlap (neuralchemy), under 1% on deepset and SPML
  - Decision: accept and caveat
  - Limitations documented: Harelix removed from HuggingFace, 15 V2 sources disclosed by license category only, Meta Prompt Guard 2 enumerates zero training sources

### Evaluation set

- [x] **Build stratified eval set** (done 2026-05-08; `results/eval_set.parquet`, 4,546 rows)
  - Implement `src/eval_set.py` with these rules:
    - deepset: use all 546 rows (below the 2,000 target; do not oversample)
    - neuralchemy: sample 2,000 from 4,391, stratified by label and by attack subcategory on the injection side
    - SPML: sample 2,000 from 16,012, stratified by label
    - Seed 42
  - Export to `results/eval_set.parquet` with columns: prompt_idx (unique global), dataset, prompt, label, subcategory (if any)
  - Freeze this file; downstream pipelines read it only
  - Notebook `notebooks/02_eval_set_construction.ipynb` drives it

### Accounts and API verification

- [x] Groq API key in `.env`, smoke test with Llama 3.3 70B Versatile succeeds (done 2026-05-08, see `scripts/smoke_test_apis.py`)
- [x] Anthropic API key in `.env`, smoke test with Claude Sonnet 4.6 succeeds (done 2026-05-08)
- [x] OpenAI API key in `.env`, smoke test with GPT-4o succeeds (done 2026-05-08, after $10 credit top-up)
- [ ] Optional: Gemini API key if used elsewhere

### Week 1 checkpoint

- [x] Email Eduardo to confirm interim format expectations (resolved at 2026-04-24 office meeting: document, no formal template, standard submission)
- [x] Push all Phase 0 commits to main (done across multiple commits 2026-05-08 through 2026-05-11)
- [x] Update `_project_notes/capstone_state.md` with Phase 0 completion status (continuously updated 2026-04-24, 2026-05-08)

---

## Phase 1: Core Pipelines Build (Apr 28 - May 4)

Target: ~29 active hrs. Goal: all defense pipelines working end-to-end on small samples and ready to scale.

### Shared infrastructure

- [x] `src/cache.py`: JSONL append-log utility with existing-keys lookup (done 2026-05-08)
- [x] `src/utils.py`: env logging helper, seed setter, pathing helpers (done 2026-05-11)
- [x] `src/metrics.py`: accuracy, precision, recall, F1, Cohen's kappa, McNemar's test, bootstrap CI (done 2026-05-11)

### Defense A (input classifier)

- [x] `src/defense_a/deberta.py`: ProtectAI DeBERTa v2 inference wrapper, batched, device auto-detect (done 2026-05-08)
- [x] `src/defense_a/prompt_guard.py`: Meta Llama Prompt Guard 2 inference wrapper (done 2026-05-08, license access granted mid-session)
- [x] `notebooks/05_defense_a_pilot.ipynb`: local pilot, runs on CPU on the deepset 546-row subset (done 2026-05-08, see `results/defense_a_pilot.md`)
- [x] `notebooks/colab_defense_a.ipynb`: Colab Pro version with GPU for the full eval-set run (done 2026-05-11)
- [x] Run Defense A on full eval set, both classifiers, save consolidated predictions (done 2026-05-11; see `results/defense_a_full_eval_set.csv` and `results/defense_a_full_metrics.csv`)
- [x] Run Defense A (DeBERTa) on all 4,391 neuralchemy rows for supplementary per-subcategory analysis (done 2026-05-08, see `notebooks/06_defense_a_neuralchemy.ipynb` and `results/defense_a_pilot.md`)
- [x] Run Defense A (DeBERTa) on 2,000-row balanced SPML subsample (done 2026-05-08, see `notebooks/07_defense_a_spml.ipynb`)

### Prompt augmentation baseline

- [x] `src/augmentation/variants.py`: three templates (control, instruction-only, combined) (done 2026-05-11)
- [x] `src/defense_b/agent.py`: Groq client wrapper for Llama 3.3 70B Versatile (done 2026-05-08; sneak-preview level, no retry logic yet)
- [x] `notebooks/06_augmentation_run.ipynb`: drives the 3 conditions end-to-end agent + judge on 100-row pilot sample (scaffolded 2026-05-11, not yet executed)
- [ ] Scale augmentation runs to full ~4,546 rows (background time, ~3-5 hrs wait)

### Defense B (LLM-as-judge)

- [x] `src/defense_b/judge.py`: Anthropic client wrapper for Claude Sonnet 4.6 with structured JSON-verdict parsing (done 2026-05-08; minimum-rubric, OpenAI/GPT-4o leg still to add)
- [x] Judge rubric prompt (sneak-preview iteration 0): minimal rubric in `src/defense_b/judge.py`. Production rubric pending operational-definitions integration in Phase 2.
- [x] Sneak-preview Defense B runs on 24 hardest cases across three attack classes:
  - 8 deepset role-play misses: judge flagged 4/8 hijacked
  - 8 neuralchemy jailbreak misses: judge flagged 0/8 (Llama refused all 8 on alignment)
  - 8 neuralchemy encoding-class misses: judge flagged 1/8 (agent treated encoded payloads as cipher puzzles, didn't comply)
  - Artifacts: `results/defense_b_sneak_preview.md`, `results/defense_b_neuralchemy_jailbreak_preview.md`, `results/defense_b_neuralchemy_encoding_preview.md`
- [x] Defense B 500-row pilot (done 2026-05-11 via `scripts/run_defense_b_pilot.py` on Together AI; pilot writeup at `results/defense_b_pilot.md`)
- [x] Review judge outputs on pilot, refine rubric if needed (done across v1.8 -> v1.21 -> v1.25 iterations 2026-05-26 through 2026-06-01; final v1.25 prompt at `src/defense_b/judge.py::_V125_SYSTEM_HEADER`)

### Week 2 checkpoint

- [x] Push all Phase 1 commits (done 2026-05-11 in commit `70bd849`)
- [x] Confirm Defense A predictions CSV exists and makes sense (done 2026-05-11; consolidated to `results/defense_a_full_eval_set.csv`)
- [ ] Confirm augmentation pipeline produces plausible outputs (notebook scaffolded; execution deferred)
- [x] Confirm Defense B pilot verdicts look sensible on a spot-check (done 2026-05-11; 500-row pilot complete)

---

## Phase 2: Human Validation + Interim Deliverable (May 5 - May 11)

Target: ~23 active hrs. Goal: judge validation, interim report, everything committed cleanly for Eduardo.

### 200-row label audit (Task 1)

- [x] **Generate stratified 200-row audit sample** (done 2026-05-08 via `scripts/make_label_audit_sample.py`; 67 deepset + 67 neuralchemy + 66 SPML, 50/50 SAFE/INJECTION balance, seed 42)
- [x] **Rerank by classifier disagreement** (done 2026-05-21 via `scripts/rerank_label_audit_by_disagreement.py`; binary-disagreement boundary cases concentrated at top of file)
- [x] **Add SPML system_prompt column** (done 2026-05-26 via `scripts/add_spml_system_prompt_to_audit.py`; required for §3.2 Step 0 operator-intent grounding)
- [x] **Human auditor labels all 200 rows** (done 2026-05-27 by Boga; applied operational_definitions.md v1.22 §3.1 decision tree)
- [x] **v1.22 §3.1 review pass** (done 2026-05-27 via `scripts/apply_ambiguous_flips_v122.py`; 32 ambiguous flips, final ambiguity rate 8.5%)
- [x] **Notes cleanup, language detection, mojibake fixes** (done 2026-05-27 via `scripts/add_language_column_and_notes.py` and `scripts/audit_notes_and_language_cleanup.py`)
- [x] **Definition-boundary consistency flips on ranks 39 and 62** (done 2026-05-27 via `scripts/audit_finalize_and_kappa.py`)
- [x] **Cohen's kappa, agreement rate, ambiguity rate, cross-language stats** (done 2026-05-27; overall kappa 0.930 [0.878, 0.970], 7 disagreements of 200, ambiguity 8.5%)
- [x] **Audit report writeup** (done 2026-05-27: `reports/label_audit_report.md`)
- [x] **Final report integration** (done 2026-05-27: §5.1 noise-floor paragraph, §8.4 dataset label noise update, §5.4 / §6.1 / §8.8 / §9.1 cross-language findings)

Canonical post-audit data file: `results/label_audit_sample_disagreement_sorted_post_audit.csv`. Earlier intermediate files (`label_audit_sample.csv`, `label_audit_sample_disagreement_sorted.csv`) are kept for reproducibility but superseded.

### Gold subset for judge validation

- [x] **Label 150-item human gold subset** against operational definition (done 2026-05-27 across deepset 59 / neuralchemy 41 / SPML 50; final at `results/judge_gold_subset_audited.csv` with SPML post-audit relabel at `results/judge_gold_subset_spml_relabel_post_audit.csv`)
- [x] Run primary judge (Claude Sonnet 4.6) on gold subset (done 2026-05-27 under v1.21; re-run 2026-06-01 under v1.25)
- [x] Compute agreement: Boga-vs-Claude Sonnet 4.6 kappa (done; v1.21 Sonnet kappa 0.477 [0.336, 0.608], v1.25 Sonnet 0.466, Haiku 0.554, Opus 4.7 0.550, GPT-4o-mini 0.403)
- [ ] Optional: reach out to Zsófi or Hiflylabs engineer about 50-item co-label for inter-annotator kappa
- [x] Record findings in `reports/judge_validation_report.md` (done 2026-05-28; v1.25 + Opus 4.7 results integrated into final report §6.3 and §7.4 2026-06-01)

### Sensitivity check on Defense B

- [x] Cheap-judge sweep on 500-row pilot (done 2026-05-11 via `scripts/run_judge_cost_sweep.py`; Haiku 4.5 and GPT-4o-mini as alternative judges)
- [x] Compute kappa across judges (done 2026-05-11; Sonnet vs Haiku 4.5 = 0.799, Sonnet vs GPT-4o-mini = 0.720)
- [x] Add results to judge cost-comparison report at `results/defense_b_judge_cost_comparison.md`

### Defense B full run

- [ ] Scale Defense B agent + primary judge to full ~4,546-row eval set (~3-5 hrs background time, run overnight if needed)
- [ ] Verify JSONL cache populated, no missing rows
- [ ] Save `results/defense_b_verdicts.csv`

### Interim report

- [x] Write `reports/interim_progress_report.md` (done 2026-05-11; restructured to match the CEU MSBA Capstone Interim Progress Report template, 13 numbered sections + Final Self-Check; PDF compiled at `reports/interim_progress_report.pdf` via Pandoc + xelatex)
- [x] Verify all repo contents pushed; README is clean (done 2026-05-11; commit `70bd849` pushed to GitHub)
- [x] Submit interim report (done 2026-05-11 evening; submitted PDF preserved at `reports/Petruska_interim_progress_report.pdf`)

### Week 3 checkpoint (May 11 interim deadline)

- [x] Interim report submitted (done 2026-05-11)
- [x] Update `capstone_state.md` with post-interim status (done 2026-05-11; refreshed continuously through 2026-06-01)
- [x] Capture any Eduardo or coordinator feedback for Phase 3 adjustments (resolved 2026-05-13 in conversation with Zoltan Toth: finish existing work before pursuing stretch goals; scope constraint honored)

---

## Phase 3: Analysis + BIPIA Phase 1 (May 12 - May 18)

Target: ~25 active hrs capstone + ~4 hrs DS4 prep. Goal: core analysis done and BIPIA indirect-injection extension started.

### Statistical analysis of core results

- [x] Notebook `09_analysis_and_plots.ipynb` (done 2026-05 across Defense A bootstrap CIs, cross-dataset breakdowns, error-pattern analysis; results integrated into final report §5.1 through §5.7)
- [x] Defense A vs Defense B paired comparison (done; McNemar tests in `results/defense_a_mcnemar.csv` and `defense_a_ensemble_mcnemar.csv`; final report §5.5b/c reports paired analysis with b=0 c=25 p=5.96e-08 for the Defense A vs Defense C comparison)

### BIPIA phase 1: email QA

- [x] Read BIPIA paper and repo, understand email QA task structure (done 2026-05; Yi et al. 2025 cited throughout §5.8 and §5.11)
- [x] `src/bipia/email_qa.py`: BIPIA email QA pipeline adapter (done 2026-05; includes loader, compose_agent_input, compose_for_defense_a)
- [x] `notebooks/08_bipia_email_qa.ipynb`: run all three defenses through BIPIA email QA (done; full results at `results/bipia_email_qa_results.csv` 800 rows; per-category breakdown at `results/bipia_email_qa_per_category.csv`)
- [x] Analysis of BIPIA email QA results, added to main analysis notebook (done; report §5.8 reports headline ASR/FAR and v1.21 rubric per-category big movers)

### Non-capstone: DS4 exam prep

- [ ] Study for DS4 exam May 20 (~4-8 hrs across the week)

### Week 4 checkpoint (Scope Expansion Decision)

- [x] **Decision: BIPIA scope** (decided 2026-05; stopped at email QA per "focused case study" framing; BIPIA expansion replaced by §5.11 LoRA indirect-injection arm NB10 series which became the primary stretch contribution)
- [x] Push all Phase 3 commits (done 2026-05; multiple thematic commits including `70bd849` Phase 1 complete + later commits for §5.11 LoRA arm)

---

## Phase 4: Scope Additions + Writing Ramp (May 19 - May 25)

Target: ~11 active hrs capstone + ~4 hrs DS4 exam day + ~10 hrs geospatial project.

### Scope addition decisions (go/no-go)

- [x] Review Phase 3 results and timeline buffer. Decide which of the deferred scope additions to pursue:
  - Defense C combined pipeline: DONE (results in §5.5c / §6.2 of final report; OR-gate Defense A + B)
  - Error taxonomy (qualitative coding): DONE in §5.4 of final report (override-keyword signature reliance documented across DeBERTa false negatives vs true positives)
  - Defense A LoRA fine-tune: DONE as §5.11 stretch (closed cross-dataset F1 spread from 0.36 to 0.031)
  - §5.11 BIPIA arm (LoRA on indirect injection): DONE 2026-05-28 through 2026-06-01 across NB10 a-e iterations with pressure-test discipline
  - Defense C distillation (DistilBERT student): DONE in NB09 (results JSON saved)
  - Custom adversarial test set: deferred to §9.1 future work
  - Full BIPIA expansion beyond email QA: deferred to §9.1 future work
- [x] Note the decisions in project state (continuously updated in `capstone_state.md`)

### Selected scope addition work (flex)

- [x] Execute chosen additions with clear scope limits, cap hours (done across §5.11 LoRA direct-injection and BIPIA arm; Defense C distillation; v1.25 judge iteration; Opus 4.7 ceiling test)

### Non-capstone commitments

- [ ] DS4 exam (May 20, ~4 hrs including travel)
- [ ] Geospatial data term project (~10 hrs across May 22-25, submitted May 25)

### Writing ramp

- [x] Fill in report outline sections 1-4 (Introduction, Background, Data, Methods) with actual content, drawing on operational_definitions.md, label_audit_report.md, judge_validation_report.md, contamination_report.md (done; §1-§4 of `reports/final_report.md` carry filled-in content)

---

## Phase 5: Results + Discussion Writing (May 26 - Jun 1)

Target: ~30 active hrs.

### Report writing: results and discussion

- [x] Section 5 (Results): headline metrics, subgroup breakdowns, paired comparison, threshold analysis, judge reliability, BIPIA, cost/latency (done across §5.1 through §5.11; figures and tables embedded; LoRA BIPIA arm in §5.11 with four-iteration table)
- [x] Section 6 (Discussion): interpretation, tradeoffs, limitations, threats to validity — completed in trim-pass draft `reports/petruska_draft_June_5.md`; long-form `final_report.md` retains the deeper version.
- [x] Section 7 (Practitioner Recommendations): decision framework for enterprise deployment — summarised in trim-pass draft §7; full Layer 1-4 detail in Appendix E (Business Decision Framework).
- [x] Integrate figures and tables into the report body (done; `reports/figures/lora_series_comparison.png/pdf` plus inline tables throughout §5 and §7)

### Literature review finalization

- [x] Zotero library exported via Better BibTeX to `reports/references.bib`; tagged threat-vector taxonomy lives in `reports/literature_tracker.md`.
- [ ] Appendix F (structured literature review across adjacent threat vectors) deprioritised; deferred to post-submission if time permits.

### Repo hygiene

- [ ] Zip cache directory, upload to Google Drive, add link to README as supplementary material (~1 hr)
- [x] Migrated to uv (`pyproject.toml` + `uv.lock`); README documents `uv sync --extra api` setup. Stale conda environment.yml step retired.

---

## Phase 6: Final Polish + Submission (Jun 2 - Jun 8)

Target: ~32 active hrs.

### Report completion

- [x] Sections 8-9 (Limitations, Future Work + Conclusion) filled in long-form `reports/final_report.md`.
- [x] Trim pass: produced sponsor-facing `reports/petruska_draft_June_5.md` (~45 pp report + ~50 pp appendices A-E) via Pandoc + xelatex.
- [x] CEU formatting applied: A4, 2.5cm margins, Calibri body 12pt, double-space body / single-space frontmatter, active TOC, List of Figures and Tables with subheadings, chapter-on-new-page, Roman to Arabic page numbering, embedded font subsets.
- [ ] Decide CEU submission shape: trim deliverable vs long-form expansion.
- [ ] Section 0 (Executive Summary): may be added if CEU submission is the long-form shape.
- [ ] Final compile pass on the chosen CEU submission shape.

### Slide deck

- [ ] Draft outline: 10-20 slides matching report arc (~2 hrs)
- [ ] Build deck (~8 hrs)
- [ ] Review with a classmate or Zsófi if possible (~1 hr)

### Public summary

- [ ] Write 3-page public CEU summary, layperson-accessible (~4 hrs)

### Sponsor handoff

- [x] Cleaned `reports/` of obsolete drafts (9 files deleted 2026-06-05): old Word/PDF compiles of `Petruska_final_report*`, status-note variants, Word lock/temp files.
- [ ] 2026-06-05 11 AM sponsor video call with Zsófia Práger; cover email + PDF + GitHub link sent same day.
- [ ] Capture sponsor feedback in `capstone_state.md` immediately after the call.

### Submission

- [ ] Final commit and tag on GitHub
- [ ] Submit all deliverables per CEU format
- [ ] Send final versions to Zsófi / Hiflylabs

---

## Risk log

Items to revisit at each phase checkpoint.

- **Groq rate limits on paid tier**: may still hit bursts; mitigation is JSONL caching with resume and backoff/retry
- **Judge prompt design sensitivity**: results from Phase 1 pilot will indicate if further rubric iteration needed
- **Contamination finding**: if Defense A classifier training data heavily overlaps with our datasets, may need to carve out a contamination-free subset and report both (contaminated vs clean) metrics
- **BIPIA fit for pipeline**: if BIPIA task formats are harder to adapt than expected, fall back to token-BIPIA and label honestly
- **DS4 / geospatial time drift**: if either runs longer than estimated, scope additions are the first thing cut

## Weekly rhythm

- Start of week: scan the current phase, confirm top 3 priorities for the week
- End of week: check off completed items, note slippage, commit everything pushed
- Monday updates to Zsófi when meetings resume

## Dependencies between items

Critical path (approximate):

```
Phase 0 operational definitions ---> Phase 1 judge rubric ---> Phase 2 judge validation
Phase 0 contamination check ---> Phase 1 Defense A run ---> Phase 3 analysis
Phase 0 eval set ---> all defense runs ---> Phase 3 analysis ---> Phase 5 writing
Phase 2 interim ---> Phase 3 adjustments (based on Eduardo feedback)
```

Do not start anything downstream before its upstream is done.
