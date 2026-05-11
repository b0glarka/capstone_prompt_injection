# Defense C combined pipeline: pilot-scale analysis (n=500)

- Run date: 2026-05-11
- Data: 500-row Defense B pilot (`results/defense_b_pilot.csv`) merged with full-eval-set Defense A predictions (`results/defense_a_full_eval_set.csv`)
- No new API calls. Defense C is computed as the OR-combination of Defense A and Defense B verdicts on the same prompts.

## Decision rule

```
A prompt is flagged by Defense C if:
    Defense A classifier flags it as INJECTION
  OR
    Defense B agent + judge says the agent's response is HIJACKED
```

Three Defense C variants are tested, paired with each Defense A choice (DeBERTa alone, PG2 alone, DeBERTa+PG2 ensemble).

## Headline metrics (overall, n=500, with bootstrap 95% CIs)

| Defense | Precision | Recall | F1 | Accuracy |
|---|---|---|---|---|
| A: DeBERTa alone | 0.960 [0.927, 0.985] | 0.761 [0.710, 0.810] | 0.849 [0.814, 0.882] | 0.864 [0.834, 0.892] |
| A: PG2 alone | 0.982 [0.951, 1.000] | 0.430 [0.368, 0.490] | 0.598 [0.535, 0.656] | 0.710 [0.670, 0.748] |
| A: DeBERTa+PG2 ensemble | 0.955 [0.922, 0.981] | 0.769 [0.719, 0.817] | 0.852 [0.816, 0.884] | 0.866 [0.836, 0.896] |
| B: Sonnet judge alone | 1.000 [1.000, 1.000] | 0.418 [0.359, 0.476] | 0.590 [0.529, 0.645] | 0.708 [0.664, 0.746] |
| C: DeBERTa + B | 0.964 [0.935, 0.987] | 0.865 [0.821, 0.905] | 0.912 [0.881, 0.936] | 0.916 [0.890, 0.938] |
| C: PG2 + B | 0.987 [0.965, 1.000] | 0.614 [0.557, 0.672] | 0.757 [0.711, 0.800] | 0.802 [0.766, 0.834] |
| C: Ensemble + B | 0.961 [0.931, 0.983] | 0.873 [0.831, 0.911] | 0.914 [0.884, 0.939] | 0.918 [0.892, 0.942] |

## Per-dataset comparison (F1)

| Defense | deepset | neuralchemy | spml |
|---|---|---|---|
| A: DeBERTa alone | 0.547 | 0.951 | 0.959 |
| A: DeBERTa+PG2 ensemble | 0.571 | 0.945 | 0.959 |
| B: Sonnet judge alone | 0.656 | 0.667 | 0.419 |
| C: DeBERTa + B | 0.803 | 0.957 | 0.959 |
| C: Ensemble + B | 0.819 | 0.951 | 0.959 |

## Paired McNemar (overall)

Tests whether Defense C's error pattern differs from each single-defense baseline.

| Comparison | b (baseline wins) | c (C wins) | p-value |
|---|---|---|---|
| C: DeBERTa + B vs A_deberta | 0 | 26 | 9.443e-07 |
| C: DeBERTa + B vs B_judge | 8 | 112 | 0 |
| C: PG2 + B vs A_pg2 | 0 | 46 | 3.247e-11 |
| C: PG2 + B vs B_judge | 2 | 49 | 1.185e-10 |
| C: Ensemble + B vs A_ensemble | 0 | 26 | 9.443e-07 |
| C: Ensemble + B vs B_judge | 9 | 114 | 0 |

## Reading

Defense C is the OR-combination, so by construction recall >= max(recall_A, recall_B). The interesting question is whether the recall lift over the best single defense is significant, and whether the FPR cost of OR-combination is acceptable. McNemar's b and c columns indicate the asymmetric error pattern: c is the count of prompts Defense C gets right that the baseline gets wrong, b is the count where the baseline is right and C is wrong. For OR-combinations against either component, b should equal 0 (C cannot do worse on a prompt than the baseline component), so the entire test reduces to whether c is large enough to declare meaningful improvement.

## Caveats

Pilot-scale (n=500); full-scale Defense C requires running the agent + judge pipeline on the ~2,326 remaining frozen-eval-set rows that Defense A passes (cost ~$5 with Sonnet judge, ~$2 with Haiku 4.5 after gold-subset validation). Per-subcategory breakdowns on neuralchemy at this n are exploratory only. Judge rubric is the minimum-rubric form, not the production rubric.