| Purpose | Slim agenda for office meeting with Eduardo |
| Status | Ephemeral — delete after meeting; answers integrated into state.md and methodology_decisions.md |
| Created | 2026-04-21 |
| Meeting date | TBD this week |
| After meeting | Integrate answers into [capstone_state.md](./capstone_state.md) and [capstone_methodology_decisions.md](./capstone_methodology_decisions.md), then delete this file |

---

# Meeting Agenda with Eduardo

Office meeting. Target length 20-30 min. Reference for deeper detail: [capstone_methodology_decisions.md](./capstone_methodology_decisions.md).

---

## 1. Quick status (2 min)

- Plan of action is in place, 7 weekly phases through June 8 (see `capstone_plan.md`)
- Phase 0 starts this week: operational definitions doc, label audit, contamination check, eval set freeze, Groq / Anthropic / OpenAI API keys verified
- Interim (May 11) target: EDA, prompt augmentation baseline (3 conditions), Defense A (both classifiers), Defense B pilot on 500 rows, judge validation via Cohen's kappa, 3-5 page progress report
- External update: Lakera PINT dataset access is no longer available to outside researchers. Published PINT scores (DeBERTa 79.1%, Prompt Guard 78.8%) still usable as external benchmark.

## 2. Methodological input needed (10-15 min)

### 2a. Evaluation set design

Proposing a stratified sample of ~4,546 rows rather than the full 20,949:
- All 546 deepset rows
- 2,000 sampled from neuralchemy (stratified by label and attack subcategory)
- 2,000 sampled from SPML (stratified by label)
- Rationale: SPML's 16k rows would otherwise dominate pooled metrics; paired comparisons still rigorous at this size
- Optional supplementary: full-dataset Defense A run (free, fast) for subcategory-level analysis

**Question**: Is the stratified sample acceptable as primary analysis? Or do you prefer a full-dataset primary pass?

Reference: Decision #1 in [capstone_methodology_decisions.md](./capstone_methodology_decisions.md) for pros/cons/citations.

### 2b. Rigor priorities

Planned methodological rigor items:
- Operational definition of "hijacked" anchored on OWASP LLM01, BIPIA, Greshake et al.
- 200-row dataset label audit before scaling defenses
- Contamination check on ProtectAI and Prompt Guard training data disclosures
- 150-row human-labeled gold subset for judge validation (with optional second-annotator extension via Hiflylabs)
- Cohen's kappa on judge agreement (primary Sonnet 4.6 vs sensitivity GPT-4o)
- Paired McNemar's test for defense-vs-defense comparisons
- Bootstrap 95% CIs on every metric
- ROC/PR curves for Defense A threshold analysis

**Question**: Any rigor expectation I am missing? Anything you want me to emphasize or de-emphasize?

Reference: Methodological additions M1-M4 in [capstone_methodology_decisions.md](./capstone_methodology_decisions.md).

## 3. Interim logistics (5 min)

The CEU language says "Student submits interim progress report to program coordinator. The report should discuss the project's status, interim outcomes, work to be done, any problems or issues." This is loose and I want to pin it down.

**Questions**:
- Is the interim submitted to you, to a program coordinator, or to a committee? Or some combination?
- Format expectations: document only, document plus repo walkthrough, presentation, or other?
- Page limit or template?
- What level of polish do you want? Raw working doc, or something more formal?

## 4. Anything else (5 min)

- Open question: Hiflylabs offered API keys for Gemini / Claude / OpenAI as a secondary closed-source model comparison. Worth pursuing now, or defer?
- Any concerns you want to raise that I haven't anticipated?

---

## Docs to show if asked for depth

- [capstone_methodology_decisions.md](./capstone_methodology_decisions.md): comprehensive scope and methodological decisions with citations
- `capstone_plan.md`: week-by-week plan with checkboxes
- [capstone_state.md](./capstone_state.md): current project state snapshot

## What I want to leave with

- Clear interim expectations (format, audience, polish level)
- Sign-off or push-back on eval set design
- Any rigor priorities you care about
