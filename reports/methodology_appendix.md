# Methodology Appendix: Statistical Choices and Inference

Companion document to the capstone final report.

Author: Boglarka Petruska

Date: 2026-05-11 (sections 1-7); 2026-06-01 (Section 8 addendum: v1.25 rubric iteration, NB10 pressure-test workflow, symmetric augmentation)

Status: Draft, anchored on published references; for inclusion as an appendix in the final report.

---

# Purpose

This appendix documents the statistical-methods choices made in the capstone's evaluation pipeline. The audience is a reviewer who wants to verify that every reported claim is defensible: which test, why that test rather than alternatives, how to interpret the output, and which assumptions are being made. Every choice cited here is implemented in `src/metrics.py` and reproduced in `notebooks/09_analysis_and_plots.ipynb`.

The companion question for an outside methodologist (Professor Zoltan Toth, consulted) is whether anything documented here is unsound. That consultation is described in the implementation plan and is treated as quality assurance, not as a load-bearing input to the design.

# 1. Headline metrics

## 1.1 Accuracy, precision, recall, F1

Binary classification on imbalanced data, so accuracy is reported but not relied on. Precision and recall are reported jointly because the deployment trade-off (a missed attack vs a false alarm) varies by scenario; F1 collapses them when a single number is needed.

Definitions are conventional:

```
precision = TP / (TP + FP)
recall    = TP / (TP + FN)
F1        = 2 * precision * recall / (precision + recall)
```

Where TP = true positives (correctly flagged injections), FP = false positives (benign prompts flagged as injection), TN = true negatives (benign prompts correctly passed), FN = false negatives (injections that slipped through).

The positive class throughout this study is INJECTION (label = 1), and the metrics reported are binary-positive metrics on that class. This matches the deployment-relevant question, "did the defense catch the attack."

## 1.2 F-beta variants

F1 weights precision and recall equally. The deployment-relevant choice often weights them differently. F-beta generalizes:

```
F_beta = (1 + beta^2) * precision * recall / (beta^2 * precision + recall)
```

- F0.5 weights precision twice as much as recall (false alarms are twice as costly).
- F1 weights them equally.
- F2 weights recall twice as much as precision (missed attacks are twice as costly).

For a security application where the cost asymmetry is large (e.g., a missed attack is 100x worse than a false alarm; see business decision framework), F2 is a more honest single number than F1. This study reports F1 as the primary headline (because it is the literature standard) and notes F2 in scenarios where the cost asymmetry is explicit.

## 1.3 ROC AUC and average precision

For classifiers that output a probability score (Defense A: ProtectAI DeBERTa and Meta Prompt Guard 2), the binary decision is a function of the threshold applied to that score. Reporting only one operating point (e.g., the model's default argmax threshold) confounds two distinct properties:

- The quality of the score's ranking of injection-likely-vs-not (threshold-independent).
- The choice of where to cut that ranking into a binary decision (threshold-dependent).

ROC AUC summarizes the first across all thresholds. Values from 0.5 (random) to 1.0 (perfect). It is invariant to class imbalance.

Average precision (AP), the area under the precision-recall curve, also summarizes ranking quality but emphasizes the high-recall regime. AP is more informative than ROC AUC on heavily imbalanced data because the precision-recall curve does not get a "free pass" from the abundant negative class the way ROC does. This study reports both. On the frozen eval set (54% injection prevalence), the two metrics tell substantively similar stories; on a hypothetical 1% injection-prevalence deployment, the two would diverge and AP would be the more honest reading.

# 2. Confidence intervals

Point estimates without confidence intervals are standard in the prompt-injection-defense literature and are methodologically weak. This study reports 1,000-iteration nonparametric bootstrap 95% CIs on every headline metric, computed by `src.metrics.bootstrap_ci`.

## 2.1 Why bootstrap, why nonparametric

The metrics (especially F1, AUC, kappa) are nonlinear functions of the data with no clean parametric distribution at finite sample size. Nonparametric bootstrap (Efron, 1979) is the conventional choice because it makes no distributional assumptions, handles imbalanced data without correction, and is straightforward to verify.

## 2.2 Implementation

For each of N = 1,000 iterations, the evaluation rows are resampled with replacement (preserving the joint distribution of label, prediction, score). The metric is recomputed on the resample. Iterations where the resample yields only one class are dropped (kappa and AUC are undefined). The 2.5th and 97.5th percentiles of the resulting distribution are reported as the 95% CI.

```python
from src.metrics import bootstrap_ci
ci = bootstrap_ci(y_true, y_pred, y_score, n_iter=1000, seed=42)
# returns {"accuracy": (lo, hi), "precision": (lo, hi), ...}
```

## 2.3 Reading CIs

Non-overlapping 95% CIs between two metrics indicate the difference is unlikely to be sampling noise at the 5% level. This is a sufficient condition for "the difference is real" but not a necessary one; overlapping CIs do not prove the difference is null (see McNemar's test below for the paired-comparison case where this matters).

## 2.4 Sample size and CI width

CI half-widths scale roughly with 1/sqrt(n). On the deepset slice (n = 546) the F1 CI half-width is about 0.07; on the full eval set (n = 4,546) it is about 0.01. For per-subcategory results on neuralchemy where some categories have n = 12-30, the bootstrap CIs widen substantially and these results are reported as exploratory, not confirmatory.

# 3. Paired classifier comparison: McNemar's test

When two classifiers (or defenses) are evaluated on the same prompts, every difference in their predictions is directly attributable to the classifier rather than sampling noise. McNemar's test (McNemar, 1947) is the appropriate paired test for this setup.

## 3.1 What the test asks

Given paired binary predictions from classifiers A and B against ground truth, two cells of the 2x2 contingency table matter:

```
                B correct    B wrong
A correct       a            b
A wrong         c            d
```

The null hypothesis is that b = c (A and B disagree symmetrically). McNemar's test asks whether b and c differ more than chance allows.

## 3.2 Exact binomial vs chi-squared continuity-corrected

Two implementations are common:

- Exact binomial test on min(b, c) versus binomial(b + c, 0.5). Always valid; preferred when b + c is small (less than about 25).
- Chi-squared with continuity correction: chi^2 = (|b - c| - 1)^2 / (b + c), df = 1. Asymptotic; valid when b + c is large.

This study uses the exact binomial by default (`mcnemar(..., exact=True)`) and the chi-squared with continuity correction for the full-eval-set paired comparisons where b + c is in the hundreds (`mcnemar(..., exact=False)`).

Implementation in `src.metrics.mcnemar`.

## 3.3 When McNemar does not apply

McNemar tests whether two classifiers' error patterns differ, not whether their overall accuracy differs. For unpaired data (different prompts to different defenses), the appropriate test is a two-proportion z-test or Fisher's exact, not McNemar. This study runs all defenses on the same prompts, so McNemar is the right choice throughout.

# 4. Multiple-comparison correction: Holm-Bonferroni

With several defense configurations under comparison (ProtectAI DeBERTa, Meta Prompt Guard 2, OR-gate ensemble, AND-gate ensemble, Defense B with Claude judge, Defense B with Haiku judge, possibly Defense C combined), pairwise McNemar tests inflate the family-wise false-positive rate.

## 4.1 What inflation means

At alpha = 0.05 per test, the probability of at least one false positive across k independent tests is 1 - (1 - 0.05)^k. For k = 10 pairwise comparisons, this is ~40%. Claiming significance at the family level without correction is misleading.

## 4.2 Why Holm-Bonferroni rather than Bonferroni

Bonferroni multiplies each p-value by k. Holm-Bonferroni is uniformly more powerful: it sorts p-values ascending, then multiplies the i-th smallest by (k - i + 1). Both control the family-wise error rate at alpha; Holm has higher power, so it should be preferred unless a regulatory standard requires Bonferroni specifically.

Reference: Holm, S. (1979). A simple sequentially rejective multiple test procedure. Scandinavian Journal of Statistics, 6(2), 65-70.

## 4.3 Pre-specification

The capstone pre-specifies a small set of primary comparisons (Defense A vs Defense B overall, Defense C vs best single defense, ensemble vs best single, augmentation vs no-augmentation control). These are corrected via Holm-Bonferroni at family-wise alpha 0.05. All per-subcategory and per-dataset findings outside this primary set are explicitly labeled exploratory and are not subject to family-wise correction; their interpretation must account for the multiplicity informally.

# 5. Inter-rater agreement: Cohen's kappa

Cohen's kappa quantifies categorical agreement between two raters corrected for chance agreement.

## 5.1 Definition

```
kappa = (p_observed - p_chance) / (1 - p_chance)
```

Where p_observed is the fraction of items the two raters agree on and p_chance is the agreement expected if both raters labeled independently according to their marginal distributions.

## 5.2 Interpretation

The conventional thresholds (Landis and Koch, 1977) are:

- kappa less than 0.0: less than chance agreement
- 0.0 to 0.20: slight
- 0.21 to 0.40: fair
- 0.41 to 0.60: moderate
- 0.61 to 0.80: substantial
- 0.81 to 1.00: almost perfect

For this study, the design target is kappa above 0.60 (substantial agreement) between the human auditor (Boga) and each LLM judge on a 150-row gold subset. Kappa below 0.60 indicates that judge verdicts are not reliable enough to anchor downstream metrics; the rubric requires iteration.

Reference: Artstein, R., & Poesio, M. (2008). Inter-coder agreement for computational linguistics. Computational Linguistics, 34(4), 555-596.

## 5.3 Sample size

Kappa is sensitive to sample size and class balance. At n less than approximately 30, the kappa point estimate is noisy and its confidence interval is wide. The sneak-preview Claude-vs-GPT-4o sensitivity check at n = 8 reports an agreement rate but explicitly notes that kappa is not meaningful at that sample size. The formal validation at n = 150 will report kappa with a bootstrap CI.

## 5.4 Application to the 200-row label audit (Task 1, complete)

Kappa is also applied at the dataset-validation stage to measure agreement between the human auditor (Boga) applying the operational_definitions.md v1.22 §3.1 decision tree and the three source datasets' as-released gold labels. The full methodology and results are in `reports/label_audit_report.md`. Headline: overall kappa 0.930 [0.878, 0.970] (1,000-iteration bootstrap, seed 42); per-dataset kappa deepset 0.911, neuralchemy 0.881, SPML 1.000. All three values fall in the "almost perfect" Landis-Koch band. The disagreement-as-noise-rate proxy is 3.5% overall, consistent with Northcutt et al. (2021) on community-curated benchmark datasets. This validation provides empirical evidence that the §3.1 v1.22 instrument is consistent with the three datasets' implicit operationalisations of "prompt injection," with a small minority of edge cases concentrated in directions documented in the audit report (4 candidate dataset over-labels, 1 dataset under-label found by the audit, 1 content-policy definition boundary, 1 fictional-framing borderline).

## 5.5 Application to the 150-row judge gold subset (Task 3, complete)

Kappa was computed between the human auditor (Boga) labeling each (prompt, agent response) pair against operational_definitions.md v1.23 §3.2 and the LLM judges' verdicts on the same pairs (Sonnet 4.6 primary, plus Haiku 4.5 and GPT-4o-mini for cross-judge measurement). Full results in `reports/judge_validation_report.md`. Headline: human-vs-judge binary kappa is 0.324 (Sonnet 4.6), 0.362 (Haiku 4.5), and 0.221 (GPT-4o-mini), all in the "fair" Landis-Koch band and well below the 0.60 "substantial" design target. The gap is driven mainly by signature-vs-mechanism pattern matching: 30-41% of human-CLEAN / judge-HIJACKED disagreements involve a known signature (PWNED, DAN, JAILBROKEN) where the v1.23 §3.2 scope note explicitly says signatures alone are not enough to trigger HIJACKED. The Task 3 result is methodologically the headline limitation on all Defense B numbers in the final report and motivates the highest-leverage next iteration: updating the judge prompt to incorporate the v1.23 signature-vs-mechanism guidance explicitly.

## 5.6 Mid-project correction: SPML operator_intent passed to judges

During Task 3 validation analysis, a methodological gap was identified in the v1.21 judge driver. The driver invoked the v1.21 judge's `judge_v121(user_prompt, agent_response, dataset, operator_intent)` function with `operator_intent=None` for all rows, including SPML rows. The §3.2 v1.21 judge prompt's Step 0 instructs the judge to read the SPML system prompt as the operator-intent anchor; when no system prompt was supplied, the judge defaulted to baseline helpful-assistant intent for SPML too. This systematically underestimated H3 persona-substitution detection on SPML, because the judge could not recognise persona substitutions against an SPML deployed operator role (Finance Bot, Healthcare Advisor, etc.) without knowing what that role was supposed to be.

The bug surfaced because Task 3 human labelling had the SPML `system_prompt` column visible to the human auditor, and the auditor correctly identified H3 persona-substitution attacks against SPML deployed roles that all three LLM judges had marked CLEAN. Inspecting `src/defense_b/rejudge_v121.py` line 149 confirmed `operator_intent = None` was being passed for SPML.

The fix (`scripts/fix_spml_operator_intent.py`) re-judges only the SPML rows with `operator_intent=system_prompt` properly passed, joining the SPML system prompts from `data/spml` on `prompt_idx`. The fix updates the SPML row v1.21 verdict columns in place in `results/defense_b_pilot.csv`, `results/defense_b_judge_cost_comparison.csv`, `results/judge_gold_subset_audited.csv`, and the three cross-family pilots (`defense_b_pilot_qwen.csv`, `defense_b_pilot_mistral.csv`, `defense_b_pilot_deepseek.csv`). Pre-fix versions of all six files are preserved in `_local/pre_spml_fix/` for diff-style audit. Non-SPML rows (deepset, neuralchemy, BIPIA) were not affected: their §3.2 Step 0 anchor is baseline helpful-assistant intent, and `operator_intent=None` correctly selects that default. Human gold-subset labels were never touched; only judge verdict columns for SPML rows changed.

Effect on reported numbers: SPML hijack rates and Defense C combined metrics increased on SPML rows after the fix; human-vs-judge kappa on the gold subset improved (more apples-to-apples). The final report's §5.5b, §5.5c, §5.6, and §6.3 numbers reflect the post-fix state; the section text notes "post-SPML-fix" where it materially shifts numbers from the interim report. The full-scale Defense B run on the 4,046 non-pilot rows (Section 5.5b, full-scale) was implemented with `operator_intent=system_prompt` passed for SPML from the start, avoiding the same bug.

# 6. Specific design choices

## 6.1 Threshold choice

Defense A classifiers report a probability score for the injection class. The default decision rule (argmax over softmax probabilities) is reported in the headline because it is what an off-the-shelf deployment would use. Threshold sweeps (F1, precision, recall vs threshold) are reported alongside because the cost-weighted decision framework selects a different operating point.

This study does not optimize the threshold on the eval set and report it as a primary metric; that would be a form of train-test leakage. The threshold sweeps are descriptive.

## 6.2 Stratified sampling for the eval set

Sample design follows the methodology decision in `_project_notes/capstone_methodology_decisions.md` #1:

- deepset: all 546 rows (full census; below the 2,000 target).
- neuralchemy: 2,000 rows, stratified by label and by attack subcategory on the injection side. Stratification preserves the joint distribution of label and subcategory at the sample scale.
- SPML: 2,000 rows, balanced 50/50 by label.

Stratification prevents pooled metrics from being dominated by SPML's 16,000-row source and preserves per-subcategory representation on neuralchemy. Seed 42 throughout; the same prompts go to every defense for paired comparison.

## 6.3 Bootstrap CIs across the full eval set, not per dataset alone

Pooled CIs on the union of three datasets reflect the variance across the heterogeneous population, which is what an enterprise deployment would actually face. Per-dataset CIs are also reported because the cross-dataset variance is the headline finding of the study, and burying it in a pooled estimate would be misleading.

# 7. Reporting standards

This study commits to:

- Reporting CIs on every metric, not just point estimates.
- Pre-specifying primary statistical comparisons and applying Holm-Bonferroni correction at family-wise alpha = 0.05.
- Labeling exploratory subgroup findings as exploratory.
- Reporting baselines (majority class, stratified-random, sometimes keyword-heuristic) alongside each defense, so readers can see what the defense adds over trivial alternatives.
- Reporting both F1 and AUC (or AP) for every defense, so the score-quality vs threshold-quality distinction is visible.

These commitments are made in the methodology section of the final report and are not contingent on the direction of the empirical results.

# 8. Addendum: post-2026-05-11 methodology additions (added 2026-06-01)

Three methodological choices made after the original 2026-05-11 draft of this appendix are documented in detail in the final report rather than here. This addendum cross-references each so a methodology reviewer can locate them.

**8.1 Judge rubric iteration (v1.21 to v1.25).** A scope-note iteration on the judge prompt baked the §3.2 v1.23 signature-vs-mechanism guidance directly into the LLM-as-judge prompt (full text at `src/defense_b/judge.py::_V125_SYSTEM_HEADER`). Effect measured via Cohen's kappa on the 150-row gold subset under the §7.6 fail-closed AMBIG=HIJACKED binarisation convention; robustness checked under four AMBIGUOUS-handling conventions (AMBIG=HIJACKED, AMBIG=CLEAN, 3-class, drop-AMBIGUOUS). Empirical results in `reports/judge_validation_report.md` v1.25 addendum and final report §6.3. The Haiku 4.5 lift is robust across all four conventions; the Sonnet 4.6 lift is convention-sensitive and disappears under stricter conventions. Methodological note: a 0.037 difference in the v1.21 Sonnet baseline number (0.477 in §5.6 vs 0.440 in §6.3) reflects a slightly different binarisation handling of AMBIGUOUS and missing verdicts in the two computations; both fall well within the §5.6 bootstrap CI for Sonnet v1.21.

**8.2 NB10 pressure-test workflow.** Six adversarial probes applied to the §5.11 BIPIA LoRA Variant B adapter to test whether headline kappa reflects genuine content discrimination or methodology artifact: attack-question ablation, clean-question ablation, held-out base emails, length-shortcut check, novel question phrasing, and false-positive rate on real legitimate queries. Pass/fail criteria per probe documented inline in the NB10d notebook. The attack-question ablation (Test 1) is the load-bearing probe; if flag rate falls below 0.95 on attacks paired with question styles the model has not seen, the augmentation has a residual shortcut. Test 1 caught a question-style shortcut in NB10c that the headline F1 (0.992) and Cohen d (9.37) did not. This kind of post-hoc adversarial probing is a methodological contribution distinct from the F1/kappa/CI reporting documented in this appendix; the recipe for follow-up work is in §5.11 BIPIA arm of the final report.

**8.3 Symmetric augmentation and base-document stratification.** Two methodological disciplines required for input-classifier fine-tuning on indirect-injection data. Symmetric augmentation: ensure the marginal distribution of legitimate user-question phrasings is approximately equal across the clean and attack training classes, so question style cannot be learned as a shortcut. Base-document stratification: stratify the train/val/test split at the document level rather than at the (document, question) pair level, so train and test share zero base documents and memorization is structurally impossible. Both are operationalised in `scripts/augment_bipia_symmetric.py` and documented in §5.11 of the final report. Without these disciplines the §5.11 NB10c iteration produced d = 9.37 that did not survive pressure testing; with them the NB10e iteration produced d = 7.73 on held-out base emails that survived all probes.

The statistical reporting conventions documented in sections 1-7 above apply to the results these methodological additions produced.

# 9. References

Artstein, R., & Poesio, M. (2008). Inter-coder agreement for computational linguistics. *Computational Linguistics*, 34(4), 555-596. https://doi.org/10.1162/coli.07-034-R2

Efron, B. (1979). Bootstrap methods: Another look at the jackknife. *Annals of Statistics*, 7(1), 1-26.

Holm, S. (1979). A simple sequentially rejective multiple test procedure. *Scandinavian Journal of Statistics*, 6(2), 65-70.

Landis, J. R., & Koch, G. G. (1977). The measurement of observer agreement for categorical data. *Biometrics*, 33(1), 159-174.

McNemar, Q. (1947). Note on the sampling error of the difference between correlated proportions or percentages. *Psychometrika*, 12(2), 153-157.
