- Purpose: navigation index for `_project_notes/`. Start here to orient.
- Status: active
- Created: 2026-04-21
- Last edited: 2026-06-01

---

# Project Notes Index

Active working documents in `_project_notes/`. Each has a standard metadata header that shows its role, status, and last-edited date.

## Active

- [**capstone_state.md**](./capstone_state.md): session-bridge snapshot. Read first when resuming work after a gap.
- [**capstone_plan.md**](./capstone_plan.md): week-by-week phase plan with checkboxes. Use daily.
- [**capstone_methodology_decisions.md**](./capstone_methodology_decisions.md): why each choice was made, with citations. Consult when a question comes up about prior decisions.
- [**implementation_plan_summary_v3.md**](./implementation_plan_summary_v3.md): consolidated implementation plan as a 2026-05-12 snapshot. Used as stakeholder communication document at that point. Not refreshed since; for current state of stretch-goal work (NB10 series, v1.25 judge iteration, Opus 4.7 ceiling test) see `capstone_state.md`.
- [**implementation_plan_summary_v2.md**](./implementation_plan_summary_v2.md): prior version of the implementation plan, kept for traceability. Shared with Eduardo before the v3 revision.

## Key reports and audit artifacts

Not in `_project_notes/` but worth cross-referencing from here:

- [**../reports/operational_definitions.md**](../reports/operational_definitions.md): canonical labeling instrument (v1.22), referenced by all human labeling work and the Defense B judge prompt.
- [**../reports/label_audit_report.md**](../reports/label_audit_report.md): 200-row label audit results (Task 1, complete 2026-05-27). Cohen's kappa 0.930 between audit and dataset gold labels.
- [**../reports/methodology_appendix.md**](../reports/methodology_appendix.md): statistical methodology rationale.
- [**../_local/handoff_05_27.md**](../_local/handoff_05_27.md): insurance handoff doc for the 2026-05-26/27 sessions. Gitignored; for working-context continuity only.

## Archive

- [**archive/**](./archive/): historical snapshots (pre-PID notes, older project state docs). Preserved for context but not actively maintained.

## Conventions

- All active docs carry a metadata header as the first block (Purpose, Status, Created, Last edited, Related).
- Status vocabulary: Active, Ephemeral, Archived.
- Dates in ISO 8601 (YYYY-MM-DD).
- Cross-references use relative markdown links so they click through in rendered previews.
- "Last edited" on plan.md only bumps on structural changes, not per checkbox tick.
