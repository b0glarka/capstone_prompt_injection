#!/usr/bin/env bash
# Canonical compile command for the MS thesis PDF.
# Run from the repo root: bash scripts/compile_thesis.sh
#
# Produces: reports/Petruska_2026_MS_Thesis.pdf
#
# Formatting choices baked in (do not re-derive these):
#   - A4 paper, 2.5cm margins (CEU requirement)
#   - Calibri 12pt body (CEU requirement, font embedded as subset)
#   - documentclass=report with --top-level-division=chapter
#     (each # heading becomes a chapter starting on a new page)
#   - colorlinks=true with linkcolor=black for TOC and internal refs
#     (so the TOC reads as plain text), urlcolor and citecolor set to
#     Word's link-blue (#0563C1) so URLs and citations stand out
#   - APA citation style via reports/apa.csl
#   - Bibliography from reports/references.bib via citeproc
#   - Page numbering, title page, front-matter declarations, and
#     manual placement of \tableofcontents and \listoffigures live
#     in the markdown source, not in this command (so the command
#     does NOT include --toc, lof:true, lot:true).

set -e

pandoc reports/Petruska_2026_MS_Thesis.md \
  -H reports/pdf-header.tex \
  --bibliography=reports/references.bib \
  --citeproc --csl=reports/apa.csl \
  --pdf-engine=xelatex \
  --top-level-division=chapter \
  -V geometry:"a4paper,margin=2.5cm" \
  -V fontsize=12pt \
  -V mainfont="Calibri" \
  -V documentclass=report \
  -V colorlinks=true \
  -V linkcolor=black \
  -V urlcolor="[HTML]{0563C1}" \
  -V citecolor="[HTML]{0563C1}" \
  -o reports/Petruska_2026_MS_Thesis.pdf

echo "Compiled: reports/Petruska_2026_MS_Thesis.pdf"
