# reports

Written deliverables and associated methodology documents.

## Final deliverables

- `petruska_draft_June_5.md` + `.pdf` : trimmed sponsor-facing deliverable compiled via Pandoc + xelatex (2026-06-05). ~45 pp report body + ~50 pp appendices A-E concatenated as separate sections. CEU formatting honored: A4, 2.5cm margins, Calibri 12pt body, double-spaced body / single-spaced frontmatter, active TOC, List of Figures and Tables, chapter-on-new-page, Roman to Arabic page numbering, embedded font subsets. This is the current submission-ready PDF.
- `final_report.md` : long-form master source for the main capstone report (~100 pp without appendices). Preserved as the deeper version that `petruska_draft_June_5.md` is derived from. Final CEU submission shape (trim vs long-form) decided in the final week.
- `Petruska_interim_progress_report.pdf` : the submitted interim progress report PDF (submitted 2026-05-11 via Pandoc + xelatex compilation of `interim_progress_report.md`).
- `interim_progress_report.md` : markdown source of the interim PDF, frozen as a historical record.

## Methodology appendices (referenced from the final report)

- `operational_definitions.md` : operational definitions of "prompt injection" and "hijacked agent response" at v1.23. Anchored on OWASP LLM01:2025, Greshake et al. (2023), BIPIA, Perez & Ribeiro (2022), Toyer et al. (2024). §3.1 input-side decision tree (with v1.22 harm-vs-injection scope note) and §3.2 output-side decision tree (with v1.23 signature-vs-mechanism scope note operationalised in the v1.25 judge prompt at `src/defense_b/judge.py::_V125_SYSTEM_HEADER`). Decision tree plus worked examples. Appendix A of both reports.
- `methodology_appendix.md` : statistical-methods companion to the final report. Documents Wilson 95% CIs, Cohen's kappa, McNemar's test, bootstrap CI per `src/metrics.py`. Reviewed by Professor Zoltan Toth. Appendix B of both reports.
- `business_decision_framework.md` : practitioner-facing framework for translating the evaluation results into deployment recommendations. Layered: harm taxonomy, cost-weighted scoring, defense decision matrix, scenario mapping. Brief summary in §7 of both reports; full framework here. Appendix E of both reports.

## Supporting reports referenced in §5

- `label_audit_report.md` : results of the 200-row label audit completed 2026-05-27. Cohen's kappa 0.930 [0.878, 0.970] between human auditor and dataset gold labels. Per-dataset disagreement rates documented; cross-language finding (DeBERTa -14pp recall on non-English) flagged. Appendix C of both reports.
- `judge_validation_report.md` : 150-row judge gold-subset validation completed 2026-05-27, with v1.21 vs v1.25 rubric comparison and Opus 4.7 cost-ceiling test added 2026-06-01. Final headline: Haiku 4.5 with v1.25 is the strongly-recommended production judge. Appendix D of both reports.

## Living documents (reference)

- `literature_tracker.md` : capture file for references encountered during the project. Canonical store is Zotero; this file holds quick notes plus a scope decision (main / appendix / future / skip).

## Compilation supporting files

- `pdf-header.tex` : LaTeX header for pandoc + xelatex PDF compilation.
- `references.bib` : bibliography in Better BibLaTeX format exported from Zotero.

## Figures

- `figures/lora_series_comparison.png` and `.pdf` : the consolidated 2x2 figure showing Cohen d, macro F1, Test 1 flag rate, and eval_set F1 across the four NB10 iterations on BIPIA indirect injection. Referenced from §5.11.

## Archive

- `archive/` : superseded documents preserved for traceability. Includes `operational_definitions-v1.2-2026-05-11.md` (predecessor of current v1.23) and `final_report_outline-2026-04-21.md` (the April 21 skeleton that the final report superseded).
