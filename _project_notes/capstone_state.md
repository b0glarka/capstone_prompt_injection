- Purpose: session-bridge snapshot for Claude conversation continuity. Read this first when resuming work.
- Status: active (overwritten per update)
- Memorializing: 2026-04-24 (after Eduardo meeting and external LLM reviews)
- Last updated: 2026-04-24
- Related: [capstone_plan.md](./capstone_plan.md), [capstone_methodology_decisions.md](./capstone_methodology_decisions.md), [implementation_plan_summary_v2.md](./implementation_plan_summary_v2.md)

---

# Capstone State

## Current phase

Phase 0 (Foundation) in progress. Full plan at [capstone_plan.md](./capstone_plan.md). Methodology rationale at [capstone_methodology_decisions.md](./capstone_methodology_decisions.md). Shared implementation plan at [implementation_plan_summary_v2.md](./implementation_plan_summary_v2.md).

Interim progress report due May 11. Final due June 8.

## Active open questions

- Interim format, audience, and polish level: partially answered by Eduardo (he had no real critiques, no formal template required). Full answer pending confirmation but lower-priority than initially assumed.
- Deferred scope decisions remain in user hands (stress-test set, error taxonomy, Defense C, BIPIA expansion, etc.). Go/no-go at checkpoints per the plan.
- Budapest visit window: flexible, low priority.

## What changed in this update

Since 2026-04-21 planning session:

- **Eduardo office meeting (2026-04-24)**: no substantive critiques of the implementation plan. Encouraged running it past other LLMs for additional review.
- **External LLM reviews completed**: Kimi, Qwen, and DeepSeek each reviewed `implementation_plan_summary.md`. Reviews stored in `_local/reviews/` (gitignored). All three flagged the absence of a business decision framework as the largest gap; all three also wanted the tool-execution limitation stated more explicitly.
- **Implementation plan v2 produced** at [implementation_plan_summary_v2.md](./implementation_plan_summary_v2.md). Key changes: added Section 6a Business decision framework; elaborated scope-of-measurement limitation in Sections 3 and 4; added Holm-Bonferroni correction for McNemar's paired comparisons; clarified Meta Prompt Guard 2 architecture (mDeBERTa backbone, not Llama-family).
- **Repo hygiene**: created `_local/` folder for files that should stay local (signed PID, external LLM reviews, PDF exports). Gitignored. Deleted `eduardo_meeting_agenda.md` as ephemeral purpose served.

## What's next

See [capstone_plan.md](./capstone_plan.md) Phase 0 checklist.

High-priority:
- Verify notebook runs from new location
- Write operational definitions document
- Run 200-row label audit
- Contamination check on Defense A classifier model cards
- Build frozen eval set
- Verify all API keys working

## Resuming work

If you are a fresh Claude session or picking this up after a gap:
1. Read this file (you are here).
2. Open [capstone_plan.md](./capstone_plan.md) to see the phase checklist and next unchecked items.
3. Consult [capstone_methodology_decisions.md](./capstone_methodology_decisions.md) to understand why a choice was made.
4. [implementation_plan_summary_v2.md](./implementation_plan_summary_v2.md) is the consolidated external-facing plan shared with Eduardo.
5. Historical context lives in `archive/`; local-only files (reviews, signed docs, PDFs) live in `_local/` and are gitignored.
