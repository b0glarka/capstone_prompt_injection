# results

Computed artifacts from the pipeline. Small files (predictions, metric tables) committed to git. Large figures are written to `reports/figures/` and committed there.

## Canonical evaluation set

- `eval_set.parquet` — the frozen stratified 4,546-row evaluation set (all 546 deepset rows, 2,000-row stratified neuralchemy sample, 2,000-row balanced SPML sample), seed 42. Constructed by `src/eval_set.py` and consumed by every downstream Defense A, B, C measurement.

## Defense A artifacts

- `defense_a_full_metrics.csv` — per-dataset and overall F1, recall, precision, ROC AUC with bootstrap 95% CIs. Source for the headline Table 0.1 numbers.
- `defense_a_full_eval_set.csv` — per-prompt DeBERTa and Prompt Guard 2 predictions on the full 4,546-row eval set.
- `defense_a_neuralchemy_by_subcategory.csv` — per-subcategory recall on neuralchemy with Wilson 95% intervals, source for Table 0.2.
- `defense_a_ensemble_metrics.csv` and `defense_a_ensemble_mcnemar.csv` — OR-gate / AND-gate ensemble metrics and the paired McNemar comparison against DeBERTa solo.
- `defense_a_calibration_metrics.md` — expected calibration error pre- and post-temperature-scaling.
- `defense_a_bootstrap_cis.csv` — bootstrap CI distribution detail.
- `contamination_report.md` and `contamination_check.csv` — exact-match overlap between evaluation set and ProtectAI training sources.

## Defense B and Defense C pilot artifacts (v1.21 and v1.25)

- `defense_b_pilot.csv` — 500-row pilot per-prompt agent outputs plus v1.21 Sonnet judge verdicts.
- `defense_b_pilot_metrics_v125.csv` and `defense_c_pilot_metrics_v125.csv` — re-judged v1.25 Defense B and Defense C precision/recall/F1 with bootstrap CIs. Source for the headline Section 5.3 numbers.
- `defense_c_pilot_mcnemar_v125.csv` — per-dataset paired McNemar comparison of Defense C against Defense A under v1.25.
- `defense_b_pilot_{deepseek,mistral,qwen}.csv` and `_v125_metrics.csv` counterparts — cross-agent pilot artifacts for Section 5.7.
- `judge_v125_kappa.md` — per-judge kappa under v1.25 (Sonnet, Haiku, Opus, GPT-4o-mini) on the 150-row gold subset.
- `judge_gold_subset_audited.csv` — gold subset rows with the human auditor's labels, v1.8 and v1.21 judge verdicts.
- `judge_gold_subset_v125.csv` — same subset with v1.25 verdicts.
- `defense_b_judge_cost_comparison.csv` and `.md` — per-judge cost breakdown.

## BIPIA indirect-injection artifacts

- `bipia_email_qa_prompts.csv` — base BIPIA email-QA prompts.
- `bipia_email_qa_prompts_augmented.csv` and `bipia_email_qa_prompts_symmetric.csv` — third and fourth LoRA-iteration augmentation outputs.
- `bipia_email_qa_metrics.csv`, `_v125.csv`, and per-agent variants — BIPIA email-QA Defense B/C metrics.
- `bipia_email_qa_per_category.csv` and `_v125.csv` — per-category attack success rates (15 BIPIA categories).
- `lora_v2_metrics.json` through `lora_v4_metrics.json` plus `lora_v3_pressure_tests.json` — per-iteration LoRA metrics on BIPIA test split, including the four-iteration arc reported in Section 5.6.

## Label audit (Appendix C source)

- `label_audit_sample_disagreement_sorted_post_audit.csv` — 200 audited prompts with the human auditor's verdict, dataset gold label, ambiguous-flag, notes, language detection. Canonical artifact.
- Earlier intermediate audit CSVs are preserved for reproducibility but should not be read as authoritative.

## Business decision framework

- `business_decision_matrix.csv` — per-defense expected cost table at three cost-ratio regimes. Source for Table 0.10.

## Compiled and aggregated reports

- `aggregate_metrics_v121.md` — earlier v1.21 aggregate metric snapshot. Superseded by v1.25 artifacts above for headline numbers but preserved for traceability.
- `bipia_email_qa.md`, `defense_a_pilot.md`, `defense_b_pilot.md`, and related `.md` files — narrative summaries written during each phase of the pipeline.
