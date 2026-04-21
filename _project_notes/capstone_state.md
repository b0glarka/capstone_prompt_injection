| Purpose | Session-bridge snapshot for Claude conversation continuity. Read this first when resuming work. |
| Status | Active (overwritten per update) |
| Memorializing | 2026-04-21 (afternoon, end of planning session) |
| Last updated | 2026-04-21 |
| Related | [capstone_plan.md](./capstone_plan.md), [capstone_methodology_decisions.md](./capstone_methodology_decisions.md) |

---

# Capstone State

## Current phase

Phase 0 (Foundation) starting this week. Full plan at [capstone_plan.md](./capstone_plan.md). Methodology rationale at [capstone_methodology_decisions.md](./capstone_methodology_decisions.md).

Interim progress report due May 11. Final due June 8.

## Active open questions

Things the plan and decisions docs do NOT resolve on their own:

- Interim format, audience, and polish level (to be locked at Eduardo office meeting; see [eduardo_meeting_agenda.md](./eduardo_meeting_agenda.md))
- Eduardo sign-off on eval set size (stratified ~4,546 rows)
- Eduardo's rigor priorities (any expectations I am missing)
- Budapest visit window (flexible, low priority)

Deferred scope decisions remain in user hands (stress-test set, error taxonomy, Defense C, BIPIA expansion, etc.). Not open questions; go/no-go at checkpoints per the plan.

## What changed in this update

Full planning session (2026-04-21 afternoon). Key outputs:

- Eleven scope decisions locked via structured interview (eval set, paired design, defense models, caching, interim target, time commitment)
- Five methodological additions baked into Phase 0 (label audit, operational definitions, contamination check, human gold subset, repo structure and report outline)
- Repo restructured with `src/`, `notebooks/`, `cache/`, `results/`, `reports/`, each with README
- `data_validation.ipynb` moved to `notebooks/01_data_validation.ipynb`, idempotent download guards added, paths resolve repo root dynamically
- `.env` with HF_TOKEN configured, `python-dotenv` installed in capstone env, authentication verified
- Four planning documents now canonical: this file, plan, methodology decisions, meeting agenda
- Three historical docs archived to `_project_notes/archive/`

## What's next

See [capstone_plan.md](./capstone_plan.md) Phase 0 checklist.

High-priority this week:
- Verify notebook runs from new location
- Write operational definitions document
- Run 200-row label audit
- Contamination check on Defense A classifier model cards
- Build frozen eval set
- Verify all API keys working
- Eduardo office meeting

## Resuming work

If you are a fresh Claude session or picking this up after a gap:
1. Read this file (you are here).
2. Open [capstone_plan.md](./capstone_plan.md) to see the phase checklist and next unchecked items.
3. Consult [capstone_methodology_decisions.md](./capstone_methodology_decisions.md) only if you need to understand why a choice was made.
4. Historical context lives in `archive/` (pre-PID notes, older state snapshots).
