| Purpose | Historical snapshot at end of 2026-04-21 planning session. Bloated (duplicates content later split into plan/methodology_decisions/state). Kept for record. |
| Status | Archived |
| Memorializing | 2026-04-21 (afternoon) |
| Archived | 2026-04-21 (same day, archived during doc reorg) |
| Superseded by | [capstone_state.md](../capstone_state.md), [capstone_plan.md](../capstone_plan.md), [capstone_methodology_decisions.md](../capstone_methodology_decisions.md) |

---

# Capstone Project State
*Updated: April 21, 2026 (afternoon, post-planning session)*

---

## Current Phase
Active implementation, Phase 0 (Foundation) starting this week. Comprehensive plan and methodology decisions documented across three new files:
- `capstone_plan.md`: week-by-week plan with checkboxes, 6 phases through June 8
- `capstone_decisions_for_eduardo.md`: 11 scope decisions + 5 methodological additions + 5 deferred scope items, each with pros/cons/citations
- `eduardo_meeting_agenda.md`: slim agenda for upcoming office meeting with Eduardo

Interim progress report due May 11. Final due June 8.

---

## Confirmed Decisions

### Scope and framing
**Scope**: Comparative evaluation of prompt injection defenses for enterprise AI agent deployments. Narrowed from Hiflylabs' original five-category brief to prompt injection (direct and indirect) to satisfy CEU's requirement for a statistical analytics workflow.

**Business scenario**: Autonomous agent with broad tool access (email, APIs, code execution). Identified by Zsófi as most relevant to Hiflylabs client work.

**Contribution framing**: Not novel modeling. Evaluation study with genuinely novel elements uncommon in the literature: paired head-to-head comparison of input-side vs output-side defenses on the same prompts, cross-dataset generalization check, attack-subcategory breakdowns, deployment-relevant FPR/TPR framing, judge prompt sensitivity analysis, statistical rigor (McNemar's paired test + bootstrap CIs).

### Defenses
- Defense A (input classifier): ProtectAI DeBERTa v3 + Meta Llama Prompt Guard 2. Both pre-trained models run locally on Colab Pro GPU. No training.
- Defense B (output validation / LLM-as-judge): agent is Llama 3.3 70B via Groq paid tier, simulated via system prompt per BIPIA methodology. Primary judge is Claude Sonnet 4.6 via Anthropic API. Sensitivity judge is GPT-4o on 500-row subsample. Cohen's kappa reported between judges.
- Defense C (combined): deferred, go/no-go at post-interim checkpoint.
- Prompt augmentation baseline: three conditions (no-aug control, instruction-only, combined delimiters + sandwich + instruction). Anchors the A vs B comparison.

### Evaluation design
**Stratified evaluation set**: ~4,546 rows total, frozen to `results/eval_set.parquet`, seed 42.
- deepset: all 546 rows (dataset total below the 2,000 target; no resampling)
- neuralchemy: 2,000 from 4,391, stratified by label + attack subcategory (proportional)
- SPML: 2,000 from 16,012, stratified by label
- Supplementary: Defense A additionally run on all 4,391 neuralchemy rows for per-subcategory analysis at full power (free on GPU)

**Paired comparison design**: same prompts through all defenses, enabling McNemar's test on paired binary predictions and bootstrap CIs on every metric.

**Metrics**: accuracy, precision, recall, F1, macro F1, TPR, FPR, AUC where applicable. Both threshold-specific and curve-based reporting for Defense A.

### Datasets
Three HuggingFace datasets confirmed via EDA:
- deepset/prompt-injections: 546 train rows, binary labels, avg 118 chars
- neuralchemy/Prompt-injection-dataset: 4,391 train rows, 29 attack subcategories (meaningful subgroups: direct_injection ~1,400, adversarial ~380, jailbreak ~290)
- reshabhs/SPML_Chatbot_Prompt_Injection: 16,012 train rows, binary labels, avg 603 chars (includes system prompts)
- Combined pool: 20,949 rows, all binary (0=benign, 1=injection)
- BIPIA (Microsoft): in scope for indirect injection component, phased (start with email QA; checkpoint decision to expand to web QA or beyond)
- PINT (Lakera): no longer externally available (organization closed the dataset distribution; published scores DeBERTa 79.1%, Prompt Guard 78.8% usable as external reference only)

### Infrastructure
**Environment**: conda `capstone`, Python 3.11. `python-dotenv` installed. Staying with conda for the capstone; uv migration considered and deferred to post-capstone.

**Repo structure**: `src/` for reusable modules (subfolders for defense_a, defense_b, augmentation), `notebooks/` for pipeline drivers, `cache/` (gitignored) for JSONL API response logs, `results/` for predictions and figures, `reports/` for written deliverables. README files in each directory.

**Data validation notebook**: moved to `notebooks/01_data_validation.ipynb`. Restructured into Setup + Section 1 (download, idempotent with per-dataset guards) + Section 2 (EDA from local disk). Paths resolve repo root dynamically via `.git` walker. Figures write to `results/figures/`.

**Secrets**: `.env` at repo root with HF_TOKEN (confirmed working), GROQ_API_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY. Gitignored.

**Caching**: JSONL append-log per call type. Temperature 0 for all calls. Crash-resistant via immediate flush on each call. Dedup on `prompt_idx`. Final cache published on Google Drive as supplementary artifact.

**Compute**: Colab Pro for Defense A GPU-accelerated inference (user already uses this for DS 4). Local capstone env for everything else (API calls, analysis, writing).

### Methodological additions (identified as critical to defensibility)
Baked into Phase 0 of the plan:
- Dataset label audit on 200-row stratified sample (~5 hrs); addresses noise concerns per Northcutt et al. 2021
- Operational definition of "hijacked" anchored on OWASP LLM01 + BIPIA + Greshake et al. + Perez & Ribeiro (~4 hrs); becomes appendix to final report
- Contamination check on ProtectAI and Prompt Guard training data disclosures (~2 hrs); before scaling Defense A
- 150-item human-labeled gold subset for judge validation with optional second-annotator extension (~6-8 hrs)
- Repo structure and report outline (completed this session)

### Deliverables
- Interim progress report: 3-5 pages, due May 11, format TBD with Eduardo
- Final report: 20-25 pages consulting style, due June 8
- Slide deck: 10-20 slides
- 3-page public CEU summary
- All code and cache published for reproducibility

### Project sponsor and cadence
Zsófi Práger. Weekly 30-minute check-ins resuming. Meeting today (2026-04-21) to review updated PPT from last week. Next meeting Friday (2026-04-24).

### Implementation approach
**Primary tool**: Claude Code CLI in VSCode terminal.

**Two-Claude division of labor**: Claude Code CLI for implementation, debugging, pipeline work. Chat project for strategy, methodology decisions, emails, project state updates.

---

## Open Questions

Things genuinely still open. Everything else has been resolved or documented.

- **Interim format and audience** (for Eduardo meeting): document only vs document + repo walkthrough vs presentation; you only vs coordinator vs committee; polish level; page limit or template
- **Budapest visit to Hiflylabs**: flexible window, no date pinned yet; low priority
- **Deferred scope additions** (user-side checkpoints, not Eduardo decisions):
  - Custom adversarial test set (50-100 novel prompts)
  - Defense transfer analysis
  - Error taxonomy on false negatives
  - Defense C combined pipeline
  - Full BIPIA expansion beyond email QA
  - Prompt augmentation decomposition (5 variants)
  - Second annotator for gold subset

### Closed since last update
- PINT dataset access: no longer externally available (dataset closed by Lakera 2026-04)
- LLM and inference provider selection: Llama 3.3 70B via Groq paid (agent) + Claude Sonnet 4.6 (primary judge) + GPT-4o (sensitivity judge)
- Hiflylabs API key offer: not needed (user paying for all keys directly)
- Zsófi check-in cadence: resumed, weekly 30-min meetings
- Data validation notebook restructure: completed, moved to notebooks/, idempotent download

---

## Just Completed (this session, 2026-04-21)

- Data validation notebook restructured into Setup + Section 1 + Section 2 with idempotent download guards
- Data validation notebook moved to `notebooks/01_data_validation.ipynb`, paths repo-root-relative, figures go to `results/figures/`
- `.env` with HF_TOKEN added, `load_dotenv()` wired into notebook, authentication verified
- `python-dotenv` installed into `capstone` conda env
- Repo structure created: `src/`, `notebooks/`, `cache/`, `results/`, `reports/` with READMEs each
- Top-level README rewritten with setup instructions, deliverable list, repo structure overview
- `.gitignore` updated (added cache/, figures, checkpoints)
- Final report outline drafted at `reports/final_report_outline.md` (9 sections + 6 appendices)
- Comprehensive capstone plan written at `_project_notes/capstone_plan.md` (6 phases, checkboxes)
- Comprehensive decisions doc written at `_project_notes/capstone_decisions_for_eduardo.md` (11 scope decisions + 5 methodological additions + 5 deferred items, all with pros/cons and verified citations)
- Slim meeting agenda at `_project_notes/eduardo_meeting_agenda.md` (20-30 min office meeting prep)
- Interview completed on 11 scope decisions, all locked pending Eduardo review of eval set size and rigor priorities
- Top 5 methodological concerns identified and baked into Phase 0
- Lakera PINT update received, closed out as open question (dataset no longer externally available)

---

## What's Next (Phase 0, this week)

Checklist tracked in detail at `capstone_plan.md`. Top-level summary:

1. Verify moved notebook runs end-to-end from new location
2. Pin `environment.yml` with exact package versions
3. Write `reports/operational_definitions.md` (operational definition of "hijacked" anchored on OWASP + BIPIA + Greshake + Perez & Ribeiro, with 10-15 worked examples)
4. Run 200-row label audit, write `reports/label_audit_report.md`
5. Contamination check on ProtectAI + Prompt Guard model cards vs our three datasets; write `results/contamination_report.md`
6. Build stratified eval set (~4,546 rows) and freeze to `results/eval_set.parquet`
7. Verify Groq + Anthropic + OpenAI API keys working with test calls
8. Office meeting with Eduardo to lock interim format and get eval set sign-off

Phase 1 (week of April 28) builds Defense A, augmentation, and Defense B pipelines. Phase 2 (week of May 5) covers gold subset labeling, judge sensitivity, full Defense B run, interim report. See plan doc for details.

---

## Prior history (kept for context)

PID fully executed with all signatures (April 1-8). NDA signed by all required parties. EDA confirmed datasets suitable: 20,949 labeled examples, consistent binary labels, neuralchemy subcategories support interaction analysis for meaningful subgroups. OpenAI API key confirmed active and working. Claude Code CLI decided as primary implementation tool.
