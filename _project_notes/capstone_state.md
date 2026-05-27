- Purpose: session-bridge snapshot for Claude conversation continuity. Read this first when resuming work.
- Status: active (overwritten per update)
- Memorializing: 2026-05-27 (evening), Task 3 partial + stretch goals mid-flight
- Last updated: 2026-05-27 evening (v1.23 of operational_definitions added §3.2 scope note on signature vs mechanism, parallel to v1.22's §3.1 scope note; Task 3 partial - 22 of 150 rows labeled in `results/judge_gold_subset_prelim_audit.csv`, review pending; stretch-goal cross-family runs in background: Qwen 3 235B-A22B Instruct via Together + Mistral Large 2 via OpenRouter + DeepSeek V3 via OpenRouter, all running pilot + BIPIA in chained background process; OpenRouterAgent class added to `src/defense_b/agent.py`; .env.example documents OPENROUTER_API_KEY; Usage Policy classifier hitting repeatedly due to accumulated attack-content context, fresh session needed to resume; new handoff at `_local/task3_audit_handoff.md`)
- Earlier today 2026-05-27: v1.21 re-judge complete on all four pipelines; aggregate metrics recomputed; final report §4.2/§5.5b/§5.5c/§5.6/§5.8/§6.3 updated with v1.21 numbers; operational definitions iterated v1.8 → v1.22 incl. harm-vs-injection scope note; 200-row label audit complete (kappa 0.930 [0.878, 0.970], 7 disagreements of 200) with audit report at `reports/label_audit_report.md`; audit-derived cross-language finding (DeBERTa -14pp recall non-English) added to final report §5.4/§6.1/§8.8/§9.1; methodology_appendix.md §5.4/§5.5 sections added for Task 1 and Task 3; capstone_plan.md Phase 2 audit checklist marked complete; audit CSV renamed to `_post_audit.csv`; pyproject.toml gained `langdetect` dependency; all committed and pushed to GitHub in 5 thematic commits
- Companion handoff: [_local/handoff_05_27.md](../_local/handoff_05_27.md) - reads as the picking-up-where-we-left-off doc if this session dies mid-cleanup
- Related: [capstone_plan.md](./capstone_plan.md), [capstone_methodology_decisions.md](./capstone_methodology_decisions.md), [implementation_plan_summary_v3.md](./implementation_plan_summary_v3.md)

---

# Capstone State

## Current phase

Phase 0 (Foundation) complete. Phase 1 (Core Pipelines Build) complete and re-judged under the v1.21 augmented rubric (Defense B 500-row pilot, BIPIA 800-row, cheap-judge sweep, GPT-4o sensitivity all re-judged; aggregate metrics recomputed; final report updated). Phase 2 (Judge Validation and Interim Deliverable) is substantially complete: 200-row label audit (Task 1) is labeled and cleaned up; the 150-row judge gold subset (Task 3) is the remaining Phase 2 work. Operational definitions document at v1.22; the version history is in the doc front matter.

Scope constraint from Zoltan Toth (2026-05-13): finish existing work before pursuing any stretch goals. This governs Phase 2 and Phase 3 priorities through 2026-06-08.

Full plan at [capstone_plan.md](./capstone_plan.md). Methodology rationale at [capstone_methodology_decisions.md](./capstone_methodology_decisions.md). Shared implementation plan at [implementation_plan_summary_v3.md](./implementation_plan_summary_v3.md) (v3 supersedes v2, incorporates post-interim feedback and expanded stretch-goals list).

Interim progress report PDF generated 2026-05-11 at `reports/interim_progress_report.pdf`, ready for CEU course-portal submission. Final report due 2026-06-08.

## Active open questions

- Judge robustness under v1.21 augmented rubric: cross-judge kappa on 500-row pilot is robust (Sonnet/Haiku 0.787, Sonnet/GPT-4o-mini 0.729), but human-vs-judge agreement is not yet measured. The 150-row gold subset (Task 3) is the formal validation step.
- Use-case grounding for business decision framework (pending Zsófi's input 2026-05-15): which Hifly client setting should anchor the framework: customer-facing chatbot (where latency dominates) or internal RAG / multi-step agent (where cost dominates)? Conditional follow-up on streaming response moderation if customer-facing is the choice.
- Fourth-model architectural robustness (pending Zsófi's input 2026-05-15): should the agent role's model family expand beyond Llama 3.3 70B to include a non-Llama model (e.g., Mistral/Mixtral, Qwen 2.5, Gemma 2, Phi-3)? Framed as layered-defense robustness check, not cost-tier extension.
- Phase Cb (full-scale Defense C run on all 4,546 rows): optional conditional on Phase 2 completion, given that pilot-scale results already support the thesis statistically.

## What changed in this update (2026-05-20 through 2026-05-27)

Substantial empirical and methodological work since the 2026-05-14 snapshot. Listed in roughly chronological order.

### Operational definitions iterated v1.8 -> v1.22 (2026-05-20 through 2026-05-26)

Major changes captured in the doc's version line. Highlights:
- §3.1 augmented with non-exhaustive Step 1-3 indicators and AMBIGUOUS routing instruction. New "Adversarial evasion gaps in the input-side audit instrument" subsection naming five evasion classes with citations (semantic-synonym, fictional-framing, novel encodings, multi-turn crescendo, authority-by-implication; Boucher 2021, Russinovich 2024, Toyer 2024, Shen 2024).
- §3.2 parallel augmentation with Step 0 operator-intent anchor per dataset + illustrative indicators per H1-H5 + AMBIGUOUS routing.
- §4 worked examples curated 18 -> 14. Dropped 6, 8, 14, 17 as redundant; renumbered remaining 1-14.
- §5.4 expanded with two new exclusions-from-scope bullets (Injection-carrier scope, Retrieval-path visibility for deployment audits).
- §5.5 (FAQ) removed; substantive content migrated (Q3 BIPIA-consistency to final report §4.2; Q4 SPML schema note to Example 14).
- §6 References reorganised alphabetically; 3 missing entries added (Artstein & Poesio 2008, Boucher 2021, Zhan 2024).
- v1.22 (final iteration) added the "Scope note (harm vs injection)" paragraph to §3.1 preamble. This is the load-bearing addition: §3.1 classifies by attack MECHANISM (Step 4 patterns), not by topic harmfulness. Abortion / corporate-login / harmful-content requests are BENIGN under §3.1 unless they use a Step 4 pattern. Matches OWASP LLM01:2025 (separates injection from LLM02 and LLM09) and the Perez/Greshake/Yi/Shen narrow-definition literature.

### Defense B / BIPIA / cheap-judge / sensitivity re-judged under v1.21 rubric (2026-05-26)

The v1.21 §3.2 augmented rubric was deployed in `src/defense_b/judge.py` and used to re-judge all cached agent responses. Pipeline-coder agent did pilot (Sonnet) and cheap-judge sweep (Haiku, GPT-4o-mini); manual run completed BIPIA (Sonnet) and GPT-4o sensitivity. Total cost ~$4.57 across all four pipelines. v1.8 baseline preserved in `_local/baseline_v1.8_judge/`. Verdict-shift summary: 91-93% unchanged across pipelines; mild net-stricter shift under v1.21.

### Aggregate metrics recomputed under v1.21 (2026-05-26)

`results/aggregate_metrics_v121.md` produced. Key numbers:

- Defense B pilot hijack rate (overall, n=251 injection rows): 0.418 -> 0.462. Per dataset: deepset 0.488 unchanged, neuralchemy 0.500 -> 0.583, SPML 0.265 -> 0.313.
- Defense B F1 on pilot: 0.590 -> 0.630 (improvement); Defense C F1 0.912 -> 0.908 (essentially unchanged within bootstrap CI overlap).
- Cross-judge kappa stable: Sonnet/Haiku 0.799 -> 0.787, Sonnet/GPT-4o-mini 0.720 -> 0.729.
- BIPIA Defense B attack success: 0.781 -> 0.669 (improvement); Defense C 0.517 -> 0.444 (improvement). Per-category big movers: Substitution Ciphers 0.46 -> 0.08, Base Encoding 0.50 -> 0.26, Information Dissemination 0.34 -> 0.18.
- Cross-family AMBIGUOUS adoption: Sonnet 3%, Haiku 1%, GPT-4o-mini 0%. The cheap models lean toward binary verdicts.

### Final report updates (2026-05-26 through 2026-05-27)

- §4.2 Defense B methodology note that v1.21 rubric is deployed; v1.8 baseline path noted.
- §5.5b (pilot), §5.5c (Defense C), §5.6 (judge sensitivity), §5.8 (BIPIA) all updated with v1.21 numbers. Side-by-side v1.8/v1.21 tables retained for some.
- §6.3 judge reliability discussion refreshed.
- §6.4 [DRAFT-TODO] "What the evaluation measures, and against whom" added as the three-tier adversary framing (own-goals / casual / determined).

### 200-row label audit (Task 1) complete (2026-05-26 through 2026-05-27)

Boga labeled all 200 rows. UTF-8 encoding preserved. Ambiguous review applied via `scripts/apply_ambiguous_flips_v122.py`: 32 flips ambiguous=TRUE -> FALSE (Category 1 = 19 clear injections; PWNED-with-directive ranks 57 and 103; Category 3 = 11 weird-but-benign malformed-grammar rows). Final ambiguous rate 17/200 = 8.5% (from 24.7%). Each flipped row got a `[v1.22 review]` note where notes was previously empty. Audit-vs-dataset agreement: 187/198 = 94.4%.

### Audit-derived cross-language finding (2026-05-27)

The audit empirically validates the pretraining-corpus concern. On the 98 audit-confirmed injection rows: DeBERTa catches 82.3% of English vs 68.4% of non-English (-14pp); PG2 catches 53.2% English vs 26.3% non-English (-27pp despite multilingual mDeBERTa backbone). Caveats: n=19 non-English, mostly German. Final report additions: §5.4 paragraph, §6.1 sentence, §8.8 new Limitations subsection ("Language coverage of the input classifier"), §9.1 Future Work bullet (cross-language evaluation at higher per-language n).

### Implementation plan v3 written (2026-05-12)

Wrote `_project_notes/implementation_plan_summary_v3.md`, a self-contained v3 plan superseding v2. Incorporates post-interim feedback from Eduardo ("cohort-leading work", noted in v3 section 9) and an expanded, prioritized stretch-goals list (sections 5.1 through 5.7). Document is designed to be portable as input context to a separate LLM session, with explicit handoff instructions for deep-learning course integration (section 6).

### Zoltan Toth methodology call (2026-05-13)

Methodology consultation call with Professor Zoltan Toth held as scheduled. Outcome: he offered no specific methodology refinements. His primary advice was organizational: finish existing work before pursuing any stretch goals. This is a scope constraint governing the project through 2026-06-08 and overrides the "optional / stretch" designation in the Phase 2-3 section of the plan. Implications: Phase 2 manual labeling and Cohen's kappa on judge gold subset takes absolute priority; Phase Cb full-scale Defense C, fourth-model addition, slide deck, and public summary are now explicitly contingent on Phase 2 completion and Phase 3 completion.

### Zsófi pre-brief email sent (2026-05-14)

Pre-brief email sent to Zsófia Práger (Hiflylabs sponsor) ahead of tomorrow's 2026-05-15 meeting. Content: 4-bullet empirical recap (Defense A consolidated F1 0.911 / AUC 0.966 on DeBERTa, Defense B 500-row hijack rates 0.488 deepset / 0.500 neuralchemy / 0.265 SPML, Defense C F1 0.912 on pilot, BIPIA indirect-injection 48.3% catch rate vs 86.5% direct) plus two open questions:

1. Use-case grounding: Which Hifly client setting should the business decision framework anchor on: customer-facing chatbot (latency dominance) or internal RAG / multi-step agent (cost dominance)? Conditional follow-up on streaming response moderation if customer-facing.
2. Fourth-model family: Adding a non-Llama agent model (Mistral/Mixtral, Qwen 2.5, Gemma 2, Phi-3) to test whether layered-defense findings are Llama-specific. Framed as architectural robustness, not cost-tier extension, because judge-side cost variation is already covered by the Sonnet/Haiku/GPT-4o-mini sweep.

## What's next

Immediate next-session priorities (Phase 2 completion, constrained by Zoltan's "finish existing work" advice):

1. Phase 2 manual labeling for the user (per `_local/user_todo_audit_and_curation.md`):
   - 200-row label audit on `results/label_audit_sample.csv` (~5-6 hours)
   - Operational-definitions example curation, 18 to 12 (~30 minutes)
   - 150-row judge gold subset labeling on `results/judge_gold_subset.csv` (~6-7 hours; instructions include H1-H5 category-overlap tie-breaker)
2. Compute Cohen's kappa between human and each LLM judge once gold subset is labeled.
3. Capture any Zsófi feedback from 2026-05-15 meeting for Phase 3 adjustments (use-case grounding and fourth-model decision).

Phase 3 work (May 19-25) resumes after Phase 2 completion:

4. Conditional Phase Cb (full-scale Defense C run on all 4,546 rows): decision at Phase 2 checkpoint. Current plan: pursue only if Phase 2 completes early and time buffer allows.
5. Conditional fourth-model addition: decision at Zsófi meeting. If greenlit, adds 1-2 hours engineering + 3-5 hours running (background time).
6. Final report sections 1-4, 6-9 completion (conditional on stretch-goal completion and time).

Optional / stretch (explicitly deferred per Zoltan):

- Slide deck (10-20 slides, ~8-10 hours).
- Public summary (3-page, ~4 hours).
- Phase Cb and fourth-model only if Phase 2 and Phase 3 finish early.

See [capstone_plan.md](./capstone_plan.md) Phase 2 and Phase 3 checklists for detailed item-level breakdown.

## Known issues

1. **Anthropic Usage Policy classifier** triggered intermittently during the 2026-05-11 session as conversation context accumulated attack-content. Workarounds: `/compact` to shrink history; switch to claude-sonnet-4-20250514; accept retries. Not a real policy issue; legitimate dual-use security research.
2. **Groq daily quota exhausted** mid Defense B pilot. Together AI is the standing fallback for any future scale-up.
3. **Reports use raw LaTeX `\newpage` and `\tableofcontents`** in markdown for PDF layout. VSCode preview and GitHub render these as plain text; only Pandoc honors them during PDF compilation.

## Resuming work

If you are a fresh Claude session or picking this up after a gap:

1. Read this file (you are here).
2. Read `_local/handoff_05_11.md` for the end-of-session pointer map and the priority list of next actions.
3. Open [capstone_plan.md](./capstone_plan.md) to see the phase checklist and next unchecked items.
4. Consult [capstone_methodology_decisions.md](./capstone_methodology_decisions.md) to understand why a choice was made.
5. [implementation_plan_summary_v3.md](./implementation_plan_summary_v3.md) is the latest consolidated external-facing plan, incorporating post-interim feedback and stretch-goal prioritization.
6. Historical context lives in `archive/`; local-only files (drafts, primers, signed PDFs, cost tracking, todos) live in `_local/` and are gitignored.
