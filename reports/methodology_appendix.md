---
title: "Methodology Appendix: Statistical Choices and Inference"
subtitle: "Companion document to the capstone final report"
author: "Boglarka Petruska"
date: "2026-05-11"
status: "Draft, anchored on published references; for inclusion as an appendix in the final report"
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

# 8. References

Artstein, R., & Poesio, M. (2008). Inter-coder agreement for computational linguistics. *Computational Linguistics*, 34(4), 555-596. https://doi.org/10.1162/coli.07-034-R2

Efron, B. (1979). Bootstrap methods: Another look at the jackknife. *Annals of Statistics*, 7(1), 1-26.

Holm, S. (1979). A simple sequentially rejective multiple test procedure. *Scandinavian Journal of Statistics*, 6(2), 65-70.

Landis, J. R., & Koch, G. G. (1977). The measurement of observer agreement for categorical data. *Biometrics*, 33(1), 159-174.

McNemar, Q. (1947). Note on the sampling error of the difference between correlated proportions or percentages. *Psychometrika*, 12(2), 153-157.
