# Notebooks

Each notebook tests one hypothesis. Heavy reusable code is in `src/`; notebooks orchestrate, evaluate, and produce figures or trained adapters. Numbering is chronological in the workflow; `_post_run` suffixes mark notebooks downloaded from Colab with execution outputs preserved for the audit trail.

## Phase 0: data and eval-set construction

- `01_data_validation.ipynb` — Download and EDA on the three direct-injection datasets (deepset, neuralchemy, SPML).
- `02_eval_set_construction.ipynb` — Build the frozen 4,546-row stratified eval set (`results/eval_set.parquet`) used by every downstream experiment.
- `04_contamination_check.ipynb` — Verify the eval set is not overlapping with ProtectAI DeBERTa and Llama Prompt Guard 2 published training data disclosures.

## Phase 1: Defense A baseline runs

- `05_defense_a_pilot.ipynb` — Pilot ProtectAI DeBERTa on a small slice; debug pipeline before full eval.
- `06_defense_a_neuralchemy.ipynb` — Full Defense A run on the neuralchemy slice of the eval set.
- `07_defense_a_spml.ipynb` — Full Defense A run on the SPML slice.
- `06_augmentation_run.ipynb` — Prompt-augmentation baseline (Defense B prompt-hardening comparison).
- `colab_defense_a.ipynb` — GPU-accelerated batched inference for Defense A across the full eval set.

## Phase 2: Defense B and BIPIA email-QA

- `08_bipia_email_qa.ipynb` — Compose and evaluate the BIPIA indirect-injection benchmark (Yi et al. 2025) through Defense A + B.
- `09_analysis_and_plots.ipynb` — Compute Wilson 95% CIs, cross-dataset variance plots, judge reliability tables for the report.

## Phase 3: Stretch experiments — §5.11 LoRA fine-tune

The §5.11 finding originated in NB08 (direct injection) and was tested for transfer to indirect injection (BIPIA) in the NB10 series. The chronology below documents the methodology iteration that produced the final deployment-ready result.

- `08_defense_a_lora_finetune.ipynb` (+ `_post_run`) — Train LoRA-v1 on the eval set (direct injection: deepset + neuralchemy + SPML). Five robustness configs reported: base FP16, large FP16, LoRA-from-ProtectAI (the §5.11 winner at 0.981 F1), INT8 quantization, and duplicate/length/confusion-matrix audits.
- `09_defense_c_distillation.ipynb` (+ `_post_run`) — Distill the OR-gate ensemble (Defense A + B) into a single DistilBERT student. Tests whether the two-layer architecture can be collapsed without losing performance.

## Phase 4: BIPIA indirect-injection fine-tune (NB10 series)

Four iterations test whether the §5.11 LoRA-fine-tune lever extends to indirect injection. Each notebook tests one specific hypothesis.

- `10_lora_v1_on_bipia.ipynb` (+ `_post_run`) — Hypothesis: does §5.11 LoRA-v1 transfer to BIPIA indirect injection? Outcome: NEGATIVE TRANSFER. Scores collapse to a near-constant 0.81 cluster (Cohen d ≈ 0.1); no discriminative signal. Direct-injection LoRA does not generalize to indirect injection.

- `10b_lora_v2_bipia_retraining.ipynb` (+ `_post_run`) — Hypothesis: does naive BIPIA retraining (combined eval_set + BIPIA train split) fix the transfer failure? Outcome: FAILED DUE TO DATA SCARCITY. BIPIA provides only 50 clean controls (35 in train). Class-weighted loss could not overcome the imbalance; the model latched onto BIPIA's email format rather than attack content. Cohen d on BIPIA test = 0.13.

- `10c_lora_v3_bipia_augmented.ipynb` (+ `_post_run`) — Hypothesis: does augmenting clean controls (each base email paired with 5 generic legitimate questions, raising clean from 50 to 300) fix the scarcity? Outcome: APPARENTLY YES, but pressure-testing required. Headline d = 9.37, macro F1 = 0.992 on BIPIA test, with eval_set F1 = 0.979 maintained (no interference with direct injection).

- `10d_lora_v3_pressure_tests.ipynb` (+ `_post_run`) — Hypothesis: is the NB10c d = 9.37 genuine generalization or methodology artifact? Six pressure tests run on the trained NB10c Variant B adapter. Outcome: ONE FAILURE. Test 1 (attack-question ablation, swap BIPIA-style attack questions for generic ones) collapses to flag rate 0.487. The model learned the training-time (question style × label) correlation as a shortcut. Test 3 (held-out base emails) PASSED, confirming email-body generalization. The shortcut is fixable, not fundamental.

- `10e_lora_v4_symmetric_augmented.ipynb` (+ `_post_run`) — Hypothesis: does symmetric augmentation (also pair attack rows with generic questions, so question style is decorrelated from label) plus base-email-stratified split fix the shortcut from NB10d? Outcome: YES. Test 1 returns to 1.000; Test 3 triple-cross (held-out emails + generic questions + held-out attack templates) still d = 7.73, balanced accuracy 0.980; eval_set F1 preserved at 0.974 (vs §5.11 LoRA-v1 0.981). Verdict: deployment-ready. This is the final §5.11 LoRA recipe for indirect injection.

## Augmentation scripts (in `scripts/`, referenced from the NB10 series)

- `augment_bipia_clean.py` — NB10c augmentation: 50 base emails × 5 generic questions = 250 augmented clean rows.
- `augment_bipia_symmetric.py` — NB10e augmentation: each base email contributes 6 clean + 15 attack rows, with each attack assigned a random question style; base-email-stratified split. Decorrelates question style from label.
