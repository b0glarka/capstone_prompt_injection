# reports

Written deliverables and associated methodology documents.

## Final thesis

- `Petruska_2026_MS_Thesis.md` + `.pdf` : the final submitted MS Business Analytics thesis (submitted 2026-06-08), compiled via Pandoc + xelatex. 132 pages with CEU formatting: A4, 2.5cm margins, Calibri 12pt body, double-spaced body / single-spaced frontmatter, active TOC, List of Figures and Tables, chapter-on-new-page, Roman to Arabic page numbering, embedded font subsets. Recompile with `bash scripts/compile_thesis.sh`.

## Source documents linked from the thesis appendices

These are the canonical source documents that the thesis Appendices A through D condense. The thesis links to each via GitHub URL.

- `operational_definitions.md` : operational definitions of "prompt injection" and "hijacked agent response" at v1.23. Anchored on OWASP LLM01:2025, Greshake et al. (2023), BIPIA, Perez and Ribeiro (2022), Toyer et al. (2024). Includes the input-side decision tree (with v1.22 harm-vs-injection scope note) and the output-side decision tree (with v1.23 signature-vs-mechanism scope note operationalised in the v1.25 judge prompt at `src/defense_b/judge.py::_V125_SYSTEM_HEADER`). Decision tree plus worked examples. Condensed into Appendix A of the thesis.
- `methodology_appendix.md` : statistical-methods companion to the thesis. Documents Wilson 95% CIs, Cohen's kappa, McNemar's test, bootstrap CI per `src/metrics.py`. Condensed into Appendix B.
- `label_audit_report.md` : results of the 200-row label audit completed 2026-05-27. Cohen's kappa 0.930 [0.878, 0.970] between human auditor and dataset gold labels. Per-dataset disagreement rates documented; cross-language finding (DeBERTa minus 14 percentage-point recall on non-English) flagged. Condensed into Appendix C.
- `judge_validation_report.md` : 150-row judge gold-subset validation, with v1.21 vs v1.25 rubric comparison and Opus 4.7 cost-ceiling test added 2026-06-01. Headline: Haiku 4.5 with v1.25 is the production-recommended judge among the four tested. Condensed into Appendix D.
- `business_decision_framework.md` : early standalone draft of the practitioner-facing framework. Superseded by Section 7 of the thesis (the framework was integrated into the body rather than kept as an appendix).

## Living documents (reference)

- `literature_tracker.md` : capture file for references encountered during the project. Canonical store is Zotero; this file holds quick notes plus a scope decision (main / appendix / future / skip).

## Compilation supporting files

- `pdf-header.tex` : LaTeX header for Pandoc plus xelatex PDF compilation.
- `references.bib` : bibliography in Better BibLaTeX format exported from Zotero.
- `apa.csl` : APA 7 citation style for citeproc.

## Figures

Final figures used in the thesis are in `figures/`. Notable:

- `figures/cross_dataset_f1.png` : Figure 0.1 in the thesis (Section 5.1 cross-dataset F1 spread).
- `figures/bipia_per_category.png` : Figure 0.2 (Section 5.5 BIPIA per-category attack success rates).
- `figures/lora_series_comparison.png` and `.pdf` : Figure 0.3 (Section 5.6 four-iteration LoRA arc on BIPIA indirect injection).

## Archive

`archive/` : superseded documents preserved for traceability. Includes the April 21 final-report outline, the May 11 operational-definitions v1.2 predecessor, the May 11 interim progress report (markdown plus submitted PDF), and the June 5 long-form `final_report.md` that the trimmed thesis was derived from.
