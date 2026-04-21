# results

Computed artifacts from the pipeline. Small files (predictions, metric tables) committed to git. Large figures (PNG) may be gitignored depending on size; final figures for the report should be committed.

## Expected files

- `eval_set.parquet` — the frozen stratified 6,000-row evaluation set, seed 42.
- `label_audit_sample.parquet` — 200 audited prompts with Boga's re-label, dataset label, and agreement flag.
- `contamination_report.md` — summary of training-data overlap checks for Defense A classifiers.
- `defense_a_predictions.csv` — per-prompt predictions from DeBERTa and Prompt Guard.
- `augmentation_verdicts.csv` — per-prompt judge verdicts for the 3 augmentation conditions.
- `defense_b_verdicts.csv` — per-prompt judge verdicts for Defense B (no augmentation, agent only).
- `gold_subset_labels.parquet` — Boga-labeled gold subset, second annotator labels if applicable, kappa.
- `metrics_tables/` — CSV metric tables per defense, per dataset, per subcategory.
- `figures/` — final figures used in the report.
