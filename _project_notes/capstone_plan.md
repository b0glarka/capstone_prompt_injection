- Purpose: active work tracker with phases, checkboxes, hours, dependencies. Check off items as they are done.
- Status: active
- Created: 2026-04-21
- Last edited: 2026-04-21
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
- [ ] Verify moved notebook runs end-to-end from new location (Restart Kernel + Run All, Section 1 prints 3 "skipping" lines)
- [ ] Pin `environment.yml` to exact versions of all installed packages (`conda env export --no-builds > environment.yml`)
- [ ] Add short note in README about Colab-vs-local hybrid workflow

### Methodological foundation

- [ ] **Operational definitions document** at `reports/operational_definitions.md` (~4 hrs)
  - Anchor definition of "prompt injection" on OWASP LLM01 + Greshake et al. 2023
  - Anchor definition of "hijacked agent response" on BIPIA categories (task execution, info gathering, ad insertion, phishing) + Greshake taxonomy
  - Binary decision tree with 10-15 worked examples drawn from the three datasets
  - This is an appendix in the final report
- [ ] **Label audit** (~5 hrs)
  - Stratified sample 200 prompts (60-70 per dataset) into `notebooks/03_label_audit.ipynb`
  - Re-label each against operational definition
  - Record: agreement with dataset label, ambiguous cases, notes
  - Save to `results/label_audit_sample.parquet`
  - Write `reports/label_audit_report.md` with noise rate, ambiguity rate, notable examples
- [ ] **Contamination check for Defense A classifiers** (~2 hrs)
  - Read ProtectAI DeBERTa model card on HuggingFace; list training data sources
  - Read Meta Llama Prompt Guard model card; list training data sources
  - Cross-reference with deepset, neuralchemy, SPML
  - Record findings in `results/contamination_report.md`
  - Decide handling: remove overlap, stratify out, or caveat

### Evaluation set

- [ ] **Build stratified eval set** (~4 hrs)
  - Implement `src/eval_set.py` with these rules:
    - deepset: use all 546 rows (below the 2,000 target; do not oversample)
    - neuralchemy: sample 2,000 from 4,391, stratified by label and by attack subcategory on the injection side
    - SPML: sample 2,000 from 16,012, stratified by label
    - Seed 42
  - Export to `results/eval_set.parquet` with columns: prompt_idx (unique global), dataset, prompt, label, subcategory (if any)
  - Freeze this file; downstream pipelines read it only
  - Notebook `notebooks/02_eval_set_construction.ipynb` drives it

### Accounts and API verification

- [ ] Groq paid tier activated, API key in `.env` as `GROQ_API_KEY`, test call with Llama 3.3 70B succeeds
- [ ] Anthropic API key in `.env` as `ANTHROPIC_API_KEY`, test call with Claude Sonnet 4.6 succeeds
- [ ] OpenAI API key in `.env` as `OPENAI_API_KEY`, test call with GPT-4o succeeds
- [ ] Optional: Gemini API key if used elsewhere

### Week 1 checkpoint

- [ ] Email Eduardo to confirm interim format expectations (audience, document vs presentation, page target, rubric if any)
- [ ] Push all Phase 0 commits to main
- [ ] Update `_project_notes/capstone_state.md` with Phase 0 completion status

---

## Phase 1: Core Pipelines Build (Apr 28 - May 4)

Target: ~29 active hrs. Goal: all defense pipelines working end-to-end on small samples and ready to scale.

### Shared infrastructure

- [ ] `src/cache.py`: JSONL append-log utility with dedup-on-load (~2 hrs)
- [ ] `src/utils.py`: env logging helper, seed setter, pathing helpers (~1 hr)
- [ ] `src/metrics.py`: accuracy, precision, recall, F1, Cohen's kappa, McNemar's test, bootstrap CI (~4 hrs)

### Defense A (input classifier)

- [ ] `src/defense_a/deberta.py`: ProtectAI DeBERTa inference wrapper with JSONL caching (~2 hrs)
- [ ] `src/defense_a/prompt_guard.py`: Meta Llama Prompt Guard inference wrapper (~2 hrs)
- [ ] `notebooks/05_defense_a_run.ipynb`: local version, runs on CPU for testing (~1 hr)
- [ ] `notebooks/colab_defense_a.ipynb`: Colab Pro version with GPU, writes predictions to Google Drive + committed CSV (~2 hrs)
- [ ] Run Defense A on full ~4,546-row eval set, both classifiers, save `results/defense_a_predictions.csv` (~1 hr wait)
- [ ] Run Defense A (both classifiers) on all 4,391 neuralchemy rows for supplementary per-subcategory analysis; save `results/defense_a_predictions_neuralchemy_full.csv` (~15 min wait)

### Prompt augmentation baseline

- [ ] `src/augmentation/variants.py`: three templates (control, instruction-only, combined) (~1 hr)
- [ ] `src/defense_b/agent.py`: Groq client for Llama 3.3 70B agent calls, JSONL caching, retry logic (~3 hrs)
- [ ] `notebooks/06_augmentation_run.ipynb`: drives the 3 conditions end-to-end agent + judge on 100-row pilot sample (~2 hrs)
- [ ] Scale augmentation runs to full ~4,546 rows (background time, ~3-5 hrs wait)

### Defense B (LLM-as-judge)

- [ ] `src/defense_b/judge.py`: Anthropic client for Sonnet 4.6, OpenAI client for GPT-4o, unified interface, JSONL caching (~3 hrs)
- [ ] Judge rubric prompt (iteration 1), informed by operational definitions doc (~2 hrs)
- [ ] `notebooks/07_defense_b_run.ipynb`: agent + primary judge pipeline on 500-row pilot sample (~3 hrs)
- [ ] Review judge outputs on pilot, refine rubric if needed (~2 hrs)

### Week 2 checkpoint

- [ ] Push all Phase 1 commits
- [ ] Confirm Defense A predictions CSV exists and makes sense (sanity check: known-injection prompts → high injection scores)
- [ ] Confirm augmentation pipeline produces plausible outputs
- [ ] Confirm Defense B pilot verdicts look sensible on a spot-check of ~10 cases

---

## Phase 2: Human Validation + Interim Deliverable (May 5 - May 11)

Target: ~23 active hrs. Goal: judge validation, interim report, everything committed cleanly for Eduardo.

### Gold subset for judge validation

- [ ] **Label 150-item human gold subset** against operational definition (~6 hrs)
  - Mix of agent outputs from augmentation control and Defense B pilot
  - Balance across datasets and across "obvious hijack" / "obvious clean" / "ambiguous" expected categories
  - Save to `results/gold_subset_labels.parquet`
- [ ] Run primary judge (Claude Sonnet 4.6) on gold subset (~1 hr)
- [ ] Compute agreement: Boga-vs-Claude Sonnet 4.6 kappa (~1 hr)
- [ ] Optional: reach out to Zsófi or Hiflylabs engineer about 50-item co-label for inter-annotator kappa
- [ ] Record findings in `reports/judge_validation_report.md`

### Sensitivity check on Defense B

- [ ] Run GPT-4o judge on 500-row subsample (~1 hr wait)
- [ ] Compute Sonnet 4.6 vs GPT-4o kappa (~1 hr)
- [ ] Add results to judge validation report

### Defense B full run

- [ ] Scale Defense B agent + primary judge to full ~4,546-row eval set (~3-5 hrs background time, run overnight if needed)
- [ ] Verify JSONL cache populated, no missing rows
- [ ] Save `results/defense_b_verdicts.csv`

### Interim report

- [ ] Write `reports/interim_progress_report.md`, 3-5 pages, matching CEU's four required sections (~6 hrs)
  - Project status
  - Interim outcomes (with tables from Phase 0 + 1 results)
  - Work to be done (summary from this plan doc)
  - Problems or issues (limitations identified so far, scope questions, any blockers)
- [ ] Verify all repo contents pushed; README is clean; notebooks run end-to-end
- [ ] Submit interim report per Eduardo's confirmed format

### Week 3 checkpoint (May 11 interim deadline)

- [ ] Interim report submitted
- [ ] Update `capstone_state.md` with post-interim status
- [ ] Capture any Eduardo or coordinator feedback for Phase 3 adjustments

---

## Phase 3: Analysis + BIPIA Phase 1 (May 12 - May 18)

Target: ~25 active hrs capstone + ~4 hrs DS4 prep. Goal: core analysis done and BIPIA indirect-injection extension started.

### Statistical analysis of core results

- [ ] Notebook `09_analysis_and_plots.ipynb` (~6 hrs)
  - Load eval set, Defense A predictions, augmentation verdicts, Defense B verdicts
  - Compute per-defense: accuracy, precision, recall, F1, macro F1, TPR, FPR, AUC (where applicable)
  - Bootstrap 95% CIs on each
  - Subgroup breakdowns: per dataset, per neuralchemy subcategory, per SPML role-play type
  - Defense A threshold analysis (ROC and PR curves, multiple operating points)
- [ ] Defense A vs Defense B paired comparison (~3 hrs)
  - McNemar's test on paired predictions for the binary hijack-detected outcome
  - Contingency tables showing where each wins and loses
  - Table: "prompts Defense A catches that Defense B misses" and vice versa (write list to results/ for error analysis)

### BIPIA phase 1: email QA

- [ ] Read BIPIA paper and repo, understand email QA task structure (~2 hrs)
- [ ] `src/bipia/email_qa.py`: BIPIA email QA pipeline adapter (~4 hrs)
- [ ] `notebooks/08_bipia_email_qa.ipynb`: run all three defenses through BIPIA email QA (~2 hrs active + background)
- [ ] Analysis of BIPIA email QA results, added to main analysis notebook (~3 hrs)

### Non-capstone: DS4 exam prep

- [ ] Study for DS4 exam May 20 (~4-8 hrs across the week)

### Week 4 checkpoint (Scope Expansion Decision)

- [ ] **Decision: BIPIA scope**
  - If email QA took ~10 active hours and judge kappa on BIPIA outputs > 0.70: expand to web QA (add ~6 hrs)
  - If email QA took longer or judge noise higher: stop at email QA, label as "focused case study"
  - If both budget and quality allow: consider 3rd task type as post-interim stretch
- [ ] Push all Phase 3 commits

---

## Phase 4: Scope Additions + Writing Ramp (May 19 - May 25)

Target: ~11 active hrs capstone + ~4 hrs DS4 exam day + ~10 hrs geospatial project.

### Scope addition decisions (go/no-go)

- [ ] Review Phase 3 results and timeline buffer. Decide which of the deferred scope additions to pursue:
  - Custom adversarial test set (50-100 prompts): ~8-12 hrs, high-value
  - Error taxonomy (qualitative coding of false negatives, ~100 per defense): ~8-10 hrs, medium-value
  - Defense C combined pipeline: ~4-6 hrs, medium-value, completes the "A+B" analysis
  - Full BIPIA expansion: ~15+ hrs, only if Phase 3 checkpoint green-lit
- [ ] Note the decisions in project state

### Selected scope addition work (flex)

- [ ] Execute chosen additions with clear scope limits, cap hours

### Non-capstone commitments

- [ ] DS4 exam (May 20, ~4 hrs including travel)
- [ ] Geospatial data term project (~10 hrs across May 22-25, submitted May 25)

### Writing ramp

- [ ] Fill in report outline sections 1-4 (Introduction, Background, Data, Methods) with actual content, drawing on reports/operational_definitions.md, reports/label_audit_report.md, reports/judge_validation_report.md, reports/contamination_report.md (~6 hrs this phase)

---

## Phase 5: Results + Discussion Writing (May 26 - Jun 1)

Target: ~30 active hrs.

### Report writing: results and discussion

- [ ] Section 5 (Results): headline metrics, subgroup breakdowns, paired comparison, threshold analysis, judge reliability, BIPIA, cost/latency (~10 hrs)
- [ ] Section 6 (Discussion): interpretation, tradeoffs, limitations, threats to validity (~6 hrs)
- [ ] Section 7 (Practitioner Recommendations): decision framework for enterprise deployment (~3 hrs)
- [ ] Integrate figures and tables into the report body (~3 hrs)

### Literature review finalization

- [ ] Zotero library tagged by threat vector, export reference list (~2 hrs)
- [ ] Write Appendix F: structured literature review across adjacent threat vectors (Hiflylabs requested) (~4 hrs)

### Repo hygiene

- [ ] Zip cache directory, upload to Google Drive, add link to README as supplementary material (~1 hr)
- [ ] Verify all notebooks run end-to-end on a clean `conda env create -f environment.yml` (~1 hr)

---

## Phase 6: Final Polish + Submission (Jun 2 - Jun 8)

Target: ~32 active hrs.

### Report completion

- [ ] Sections 0 (Executive Summary) and 8-9 (Future Work, Conclusion) written (~4 hrs)
- [ ] Top-to-bottom edit pass for clarity, consistency, flow (~6 hrs)
- [ ] Second pass: verify every claim is backed by a table or figure reference (~3 hrs)
- [ ] Third pass: tighten prose, trim redundancy, check formatting (~3 hrs)
- [ ] Export final report to PDF, verify page count 20-25

### Slide deck

- [ ] Draft outline: 10-20 slides matching report arc (~2 hrs)
- [ ] Build deck (~8 hrs)
- [ ] Review with a classmate or Zsófi if possible (~1 hr)

### Public summary

- [ ] Write 3-page public CEU summary, layperson-accessible (~4 hrs)

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
