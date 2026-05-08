# Defense A pilot: ProtectAI DeBERTa on deepset, neuralchemy, and SPML

- Run date: 2026-05-08
- Model: `ProtectAI/deberta-v3-base-prompt-injection-v2`
- Datasets: deepset/prompt-injections train (n = 546), neuralchemy/Prompt-injection-dataset train (n = 4,391), SPML train subsample (n = 2,000)
- Threshold: model default (argmax over softmax)
- Notebooks: `notebooks/05_defense_a_pilot.ipynb` (deepset), `notebooks/06_defense_a_neuralchemy.ipynb` (neuralchemy), `notebooks/07_defense_a_spml.ipynb` (SPML)

## Purpose and scope

Three-dataset pilot run intended to (a) exercise the inference and caching pipeline end-to-end before scaling to the full eval set, (b) generate a first directional measurement of Defense A across three independent benchmarks, and (c) produce showable artifacts for the 2026-05-08 Hiflylabs sponsor check-in.

Out of scope for this pilot: Meta Prompt Guard 2 (gated behind a Llama license agreement; deferred to the formal eval-set run), full Defense B and Defense C comparisons (an 8-case sneak preview against the hardest deepset misses is reported separately at `results/defense_b_sneak_preview.md`), and the frozen formal evaluation set.

## Headline metrics, side by side

Point estimates with 1,000-iteration bootstrap 95% confidence intervals.

| Dataset | n | Accuracy [95% CI] | Precision [95% CI] | Recall [95% CI] | F1 [95% CI] | ROC AUC [95% CI] |
|---|---|---|---|---|---|---|
| deepset | 546 | 0.780 [0.745, 0.813] | 0.956 [0.910, 0.990] | 0.429 [0.362, 0.500] | 0.592 [0.524, 0.657] | 0.881 [0.846, 0.915] |
| neuralchemy | 4,391 | 0.904 [0.895, 0.912] | 0.983 [0.977, 0.988] | 0.856 [0.841, 0.870] | 0.915 [0.906, 0.923] | 0.971 [0.966, 0.976] |
| SPML (balanced 2k) | 2,000 | 0.952 [0.942, 0.960] | 0.915 [0.898, 0.931] | 0.995 [0.990, 0.999] | 0.954 [0.944, 0.962] | 0.998 [0.996, 0.999] |

Cross-dataset variance is the headline finding. The same model and threshold yield F1 = 0.59 on deepset and F1 = 0.91 on neuralchemy. The 95% CIs for F1 do not overlap (deepset [0.52, 0.66] vs neuralchemy [0.91, 0.92]), so the 32-point gap is statistically robust, not a sampling artifact. Recall moves from 0.43 to 0.86; AUC from 0.88 to 0.97. This points to a property of the data, not the classifier: deepset and neuralchemy ask Defense A to handle very different distributions, and the deployment-relevant question is which more closely resembles enterprise traffic.

## Per-subcategory recall on neuralchemy

Neuralchemy labels each injection with one of 29 attack subcategories. Decomposing recall by subcategory exposes Defense A's blind spots clearly. Selected subcategories with at least 20 injection rows:

| Subcategory | n | Recall |
|---|---|---|
| direct_injection | 1,397 | 0.976 |
| token_smuggling | 27 | 1.000 |
| instruction_override | 21 | 1.000 |
| rag_poisoning | 26 | 1.000 |
| training_extraction | 68 | 0.853 |
| system_manipulation | 29 | 0.862 |
| adversarial | 383 | 0.773 |
| persona_replacement | 25 | 0.720 |
| agent_manipulation | 25 | 0.720 |
| encoding | 177 | 0.633 |
| jailbreak | 291 | 0.553 |

The classifier handles bulk attack patterns (direct injection, instruction override, token smuggling, RAG poisoning) at near-perfect recall. It substantially underperforms on jailbreaks (55%) and encoding-based attacks (63%), which are exactly the more sophisticated patterns enterprise threat models tend to weight heavily. Full breakdown including small-n categories is in `results/defense_a_neuralchemy_by_subcategory.csv` and the figure at `results/figures/defense_a_neuralchemy_subcategory_recall.png`.

## Reading

On neuralchemy the conservative-classifier story from deepset weakens: only 7% of injections are scored 0.000 (vs ~40% on deepset). The bulk of neuralchemy attacks fall into patterns DeBERTa was effectively trained on, and the model performs strongly on them. The tail of harder subcategories carries the residual error.

On deepset the picture is different. Recall caps at 0.59 even when the threshold is dropped to zero, and 40.9% of true injections are assigned a softmax injection-class probability of 0.000. The threshold sweep yields only a +0.13 F1 lift (0.59 to 0.72 at the optimal threshold). DeBERTa's residual error on deepset is not a calibration problem; it is a coverage problem.

The score-distribution figure (`results/figures/defense_a_score_distributions.png`) makes the contrast visible at a glance. On deepset, the true-injection histogram is bimodal: most are scored very near 1.0 and a hard spike sits at 0.0. There is no smooth mid-range: the model is either fully right or fully wrong. On neuralchemy, by contrast, the injection histogram has a fully populated mid-range and a much smaller spike at zero (6.8% vs 40.9%), so the threshold-tuning intuition that AUC suggests does work as expected.

SPML sits at the high end of the performance range, alongside neuralchemy but with even higher recall (0.995 vs 0.856) and a near-perfect AUC of 0.998. The recall-by-Degree breakdown is flat across all severity levels (1 through 10), with recall above 0.985 at every level, indicating the classifier does not struggle even with the lowest-severity SPML attacks. SPML's contamination rate was 0.4% (the lowest of the three datasets), so this is not a contamination story. The more likely explanation is that SPML's injection examples fall predominantly into the direct-instruction-override pattern space that DeBERTa handles well; the dataset's structure (system prompt plus user-turn injection) maps cleanly onto DeBERTa's training distribution. SPML is therefore closer to neuralchemy than to deepset on the F1 spectrum, which further isolates deepset as the harder benchmark and the more conservative estimate of real-world performance.

Two readings of the cross-dataset gap are consistent with this evidence:
1. Deepset includes attack patterns that resemble real-world adversarial behaviour but were not well-represented in DeBERTa's training mix; neuralchemy's distribution is closer to that mix. Under this reading, the deepset numbers are more honest as an estimate of in-the-wild performance.
2. Neuralchemy has 1.96% exact-match overlap with the V2 training set (per `results/contamination_report.md`), the highest of the three eval datasets. While 1.96% is too low to mechanically explain a 32-point F1 gap, the broader near-duplicate or paraphrase rate could be higher and is not measured in the contamination check. Under this reading, neuralchemy's numbers are partially inflated.

Both readings reinforce the layered-defense thesis. A single input classifier will leave attack categories uncovered, the specific categories depend on training-data choices a downstream user cannot inspect, and the gap between datasets within the same benchmark family is itself a deployment risk.

## Vs baselines

All three datasets show Defense A meaningfully above majority-class and stratified-random baselines on F1. On neuralchemy, the majority class is INJECTION (60% prevalence) and the trivial "always-INJECTION" baseline reaches F1 = 0.75 by definition; DeBERTa's 0.91 is a +0.16 lift. On deepset the majority class is SAFE (63%) so the trivial baseline gets F1 = 0.00 on the injection-positive metric.

## Contamination note

`results/contamination_report.md` documents named-source contamination of 0.92% on deepset and 1.96% on neuralchemy. Both are below the level at which contamination would mechanically inflate results in a load-bearing way at the headline level, though near-duplicate / paraphrase contamination is not measured. Numbers above are reported as-is and the limitation is documented.

## Artifacts

Per-dataset:
- `results/defense_a_deepset.csv`, `results/defense_a_neuralchemy.csv`, `results/defense_a_spml.csv`
- `results/defense_a_deepset_metrics.csv`, `results/defense_a_neuralchemy_metrics.csv`, `results/defense_a_spml_metrics.csv`
- `results/defense_a_neuralchemy_by_subcategory.csv`
- `results/defense_a_spml_by_degree.csv`
- `results/spml_sample_2k.parquet`
- `results/defense_a_cross_dataset.csv`
- `cache/defense_a_deberta_deepset.jsonl`, `cache/defense_a_deberta_neuralchemy.jsonl`, `cache/defense_a_deberta_spml.jsonl`

Figures:
- `results/figures/defense_a_deepset_confusion.png`
- `results/figures/defense_a_deepset_roc_pr.png`
- `results/figures/defense_a_deepset_threshold_sweep.png`
- `results/figures/defense_a_neuralchemy_confusion.png`
- `results/figures/defense_a_neuralchemy_subcategory_recall.png`
- `results/figures/defense_a_neuralchemy_threshold_sweep.png`
- `results/figures/defense_a_score_distributions.png` (cross-dataset bimodality contrast)
- `results/figures/defense_a_spml_confusion.png`
- `results/figures/defense_a_spml_roc_pr.png`
- `results/figures/defense_a_spml_threshold_sweep.png`
- `results/figures/defense_a_spml_degree_recall.png`

## Limitations

- Single classifier (no Meta Prompt Guard 2 yet), single threshold, single softmax operating point.
- No bootstrap CIs; cross-dataset variance reported as point estimates. Bootstrap CIs are a Phase 1 deliverable on the frozen eval set.
- Default-threshold metrics confound model quality with deployment configuration; the per-subcategory and AUC views are the more transferable signals.
- Contamination measurement only covers exact matches against the named V2 training sources; neuralchemy's higher overlap warrants caution but cannot mechanically explain the 32-point F1 gap.

## Next steps

1. Add Meta Prompt Guard 2 once Llama license access is granted; rerun all three datasets.
2. Build the frozen 4,546-row eval set (`src/eval_set.py`, `notebooks/02`); rerun Defense A on the formal pool with bootstrap CIs.
3. Per-subcategory analysis on the frozen eval set; tie blind-spot recall to the threat-vector taxonomy in the operational definitions document (Phase 0 deliverable, in progress).
