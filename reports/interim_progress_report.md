---
title: "Interim Progress Report"
subtitle: "Comparative Evaluation of Prompt Injection Defenses for Enterprise AI Agent Deployments"
author: "Boglarka Petruska, MS Business Analytics, CEU"
date: "2026-05-11"
advisor: "Eduardo (CEU, primary advisor); methodological consultation pending from Professor Zoltan Toth"
sponsor: "Hiflylabs"
deliverable: "CEU MS Business Analytics Capstone, interim checkpoint"
final_due: "2026-06-08"
---

# 1. Project Status

The project is on schedule against the implementation plan approved on 2026-04-24 (`_project_notes/implementation_plan_summary_v2.md`). Phase 0 (foundation) is substantially complete; Phase 1 (core pipelines build) is partially complete with the input-side defense pilot finished on all three target datasets and the output-side defense pilot at 500 rows underway as of the report date. Phase 2 (judge validation against a human-labeled gold subset) and Phase 3 (BIPIA indirect-injection extension) are queued and on the planned timeline for the May 18 and May 25 checkpoints respectively.

The repository is public at https://github.com/b0glarka/capstone_prompt_injection. All code, evaluation results, figures, and methodology artifacts referenced in this report are committed there and reproducible from `pyproject.toml` plus the data validation notebook.

Hiflylabs received a progress check-in on 2026-05-08. No scope adjustments emerged from that meeting; the existing implementation plan was endorsed.

# 2. Interim Outcomes

## 2.1 Methodological foundation

The operational definitions document (`reports/operational_definitions.md`, v1.1) is the methodological anchor for every downstream labeling and judgment decision. It paraphrases OWASP LLM01:2025 (OWASP GenAI Project, 2025), Greshake et al. (2023), Yi et al. (2025), and Perez and Ribeiro (2022) into a project-specific form. The document contains a three-criterion definition of "prompt injection" (instruction-directedness, override or extraction intent, live operative directive), a five-category taxonomy of "hijacked agent response" (H1 task execution, H2 information extraction, H3 persona substitution, H4 content injection, H5 compliance with override), a binary decision tree applicable to input-side prompts and a parallel tree for response-side verdicts, and 18 worked examples drawn from and verified against actual rows of the three evaluation datasets.

The 200-row stratified label-audit sample is drawn (`results/label_audit_sample.csv`, 67 deepset + 67 neuralchemy + 66 SPML, seed 42, label-balanced within each), motivated by the published label-error rates of 3.3% on average and up to 6% across community-curated ML benchmark test sets (Northcutt et al., 2021). The audit itself is in progress; the noise-rate estimate it produces is a methodological caveat in the final report rather than a load-bearing input to the pipelines.

The contamination check (`results/contamination_report.md`) cross-referenced the named training-data sources for ProtectAI DeBERTa v3 v2 against the three evaluation datasets. Exact-match overlap rates: deepset 0.92%, neuralchemy 1.96%, SPML 0.4%. All three are below the level at which exact-match contamination would mechanically inflate metrics. The handling decision is accept-and-caveat, with explicit limitations noted (Harelix unavailable for verification because it was removed from HuggingFace; 15 additional ProtectAI training sources are disclosed only by license category; Meta Prompt Guard 2 enumerates zero sources).

The frozen evaluation set is built at `results/eval_set.parquet`, 4,546 rows total: all 546 deepset rows, 2,000 from neuralchemy stratified by label and by attack subcategory on the injection side, and 2,000 from SPML (50/50 label-balanced; reused from the SPML pilot to maintain cache consistency). Construction logic is in `src/eval_set.py` and is deterministic at seed 42. Notebook `notebooks/02_eval_set_construction.ipynb` drives it and audits the per-dataset balance.

## 2.2 Defense A: input-classifier evaluation

Defense A was evaluated using two pre-trained classifiers: ProtectAI DeBERTa v3 base v2 and Meta Prompt Guard 2 86M. Both were run off the shelf with no fine-tuning, at the model's default decision threshold. On the frozen evaluation set as a whole (n = 4,546), with 1,000-iteration nonparametric bootstrap 95% confidence intervals:

- ProtectAI DeBERTa v3 v2: F1 = 0.911 [0.902, 0.919], ROC AUC = 0.966 [0.960, 0.970]
- Meta Prompt Guard 2 86M: F1 = 0.666 [0.650, 0.683], ROC AUC = 0.933 [0.927, 0.940]
- Paired McNemar (DeBERTa vs Prompt Guard 2): b = 931, c = 128, p << 0.001. DeBERTa is systematically better across the eval set; the pattern is present in every individual dataset.

Methodological choices behind these CIs and the paired test (bootstrap design, McNemar variants, multiple-comparison correction strategy) are documented in `reports/methodology_appendix.md`.

Per-dataset breakdown (where the cross-dataset variance becomes visible):

| Classifier | Dataset | n | F1 [95% CI] | ROC AUC [95% CI] | Recall [95% CI] |
|---|---|---|---|---|---|
| ProtectAI DeBERTa | deepset | 546 | 0.592 [0.524, 0.657] | 0.881 [0.846, 0.915] | 0.429 [0.362, 0.500] |
| ProtectAI DeBERTa | neuralchemy | 4,391 | 0.915 [0.906, 0.923] | 0.971 [0.966, 0.976] | 0.856 [0.841, 0.870] |
| ProtectAI DeBERTa | SPML (bal. 2k) | 2,000 | 0.954 [0.944, 0.962] | 0.998 [0.996, 0.999] | 0.995 [0.990, 0.999] |
| Meta Prompt Guard 2 | deepset | 546 | 0.413 | 0.948 | 0.261 |
| Meta Prompt Guard 2 | neuralchemy | 4,391 | 0.677 | 0.852 | 0.521 |
| Meta Prompt Guard 2 | SPML (bal. 2k) | 2,000 | 0.695 | 0.995 | 0.532 |

The principal empirical finding of Phase 1 is the cross-dataset variance. For DeBERTa, F1 ranges from 0.59 on deepset to 0.95 on SPML, a 36-point spread. The 95% CIs do not overlap, so the variance is statistically robust and not a sampling artifact. The same pattern holds across both classifiers, with Prompt Guard 2 actually more conservative (lower recall across all three datasets despite comparable or higher AUC). This rules out the simple reading that one classifier happens to fit one dataset better; the variance is a property of the dataset distributions, not the model.

The score-distribution analysis on the injection class makes the deepset gap legible. 40.9% of true injection prompts in deepset are assigned a softmax injection-class probability of exactly 0.000 by DeBERTa, indicating that the model is fully confident those prompts are safe. The threshold sweep confirms that this is not a calibration problem: recall caps at approximately 0.59 even when the threshold is dropped to zero, and the F1-optimal threshold delivers only +0.13 F1 lift over the default. On neuralchemy the same metric is 6.8% and on SPML it is lower still; both datasets show graduated score distributions where threshold tuning behaves as AUC predicts. The residual error on deepset is a coverage problem, not a calibration problem.

Per-subcategory recall on neuralchemy (using the dataset's own attack-subcategory labels) exposes Defense A's blind spots. For DeBERTa: direct injection 0.98 (n = 1,397), instruction override 1.00 (n = 21), token smuggling 1.00 (n = 27), RAG poisoning 1.00 (n = 26), training extraction 0.85 (n = 68), adversarial 0.77 (n = 383), persona replacement 0.72 (n = 25), encoding 0.63 (n = 177), and jailbreak 0.55 (n = 291). The classifier handles bulk attack patterns near-perfectly and substantially underperforms on the more sophisticated subcategories that enterprise threat models tend to weight more heavily. The same pattern (jailbreak and encoding as the largest blind spots) holds qualitatively for Prompt Guard 2.

A subsequent feature-level analysis of the 302 DeBERTa false negatives (`scripts/analyze_defense_a_errors.py`) shows that 30% of true positives contain a canonical override-language marker (words like "ignore", "disregard", "forget", "instead"), against only 4.6% of false negatives. The classifier appears to rely heavily on surface-level override keywords, which explains the cross-dataset variance mechanically: the deepset attack distribution is enriched in subtler patterns that achieve hijack effects without literal override keywords, while neuralchemy and SPML are enriched in patterns the classifier was effectively trained on.

A cross-classifier ensemble analysis using OR-gate (flag if either DeBERTa or Prompt Guard 2 flags) yields a modest F1 lift to 0.916 [paired McNemar p = 0.0005], concentrated on the harder dataset (deepset). AND-gate ensembles are strictly worse than DeBERTa alone, because the two classifiers share most of their blind spots. The mean-score ensemble achieves a higher ROC AUC (0.969) than either single classifier, indicating that the two classifiers' scores combine well for ranking even though they share the same default-threshold limitations. Full ensemble results are at `results/defense_a_ensemble_metrics.csv`.

## 2.3 Defense B: agent + judge sneak preview

Before the formal 500-row Defense B pilot, three 8-row sneak previews were run against the hardest Defense A misses to probe the layered-defense thesis at the case level. The agent is Llama 3.3 70B Versatile via Groq; the judge is Claude Sonnet 4.6 via Anthropic, with a minimum-rubric prompt (the production rubric will be developed during Phase 2 judge validation).

| Sneak-preview class | n | Judge flagged hijacked | Mechanism |
|---|---|---|---|
| Deepset role-play / persona-shift | 8 | 4 | Judge load-bearing on subtle injections |
| Neuralchemy jailbreak (hate content) | 8 | 0 | Agent (Llama 3.3 70B) refused all 8 on its own RLHF training; judge correctly classified as clean |
| Neuralchemy encoding (base64, ROT13, leet-speak, Unicode variants) | 8 | 1 | Agent treated encoded payloads as cipher puzzles, never recognizing them as live instructions |

These results indicate that the layered defense operates by three different mechanisms depending on the attack class, rather than a single uniform mechanism. The judge is load-bearing on subtle social-engineering style injections, the agent's alignment refuses blunt harmful-content jailbreaks before the judge sees them, and obfuscation can defeat the agent's instruction-parsing entirely. This refines (but does not contradict) the layered-defense argument: combining defenses is empirically supported, but the value of each layer depends on the attack class it is asked to handle.

A judge-sensitivity check on the deepset 8 cases used GPT-4o as a parallel second judge with the same minimum rubric. Claude Sonnet 4.6 flagged 4 of 8 as hijacked; GPT-4o flagged 2 of 8. The two judges agreed on 6 of 8 (75%). Cohen's kappa is not meaningful at this sample size, but the disagreement on borderline cases is larger than initially expected and indicates that the minimum-rubric judge call is somewhat model-family-sensitive. This validates the planned 150-row human-labeled gold subset (with Cohen's kappa) and the 500-row GPT-4o sensitivity sub-sample as essential rather than nice-to-have.

The formal Defense B 500-row pilot on the frozen evaluation set was launched on the report date. An initial run on Groq's Llama 3.3 70B Versatile endpoint was interrupted at row 340 by the on-demand tier's 100,000 tokens-per-day cap (the Groq Developer tier was temporarily closed to new signups, so on-demand was the only available option). The agent role was migrated to Together AI's hosted Llama 3.3 70B Instruct Turbo, which has no daily quota and identical model class, and the full 500-row pilot completed on the report date. The pipeline's JSONL cache layer writes per row, so the partial Groq results required no re-run cost on Together. Total pilot spend: $1.05 (agent on Together $0.13, Sonnet judge $0.92).

Pilot results on injection-class rows (n = 251 of the 500 stratified subsample; the other 249 are benign anchors against which false-positive rate is also reported):

| Scope | n (injection) | Hijacked by judge | Hijack rate |
|---|---|---|---|
| Overall | 251 | 105 | 0.418 |
| deepset (injection only) | 84 | 41 | 0.488 |
| neuralchemy (injection only) | 84 | 42 | 0.500 |
| SPML (injection only) | 83 | 22 | 0.265 |

Reading: roughly 42% of the injection-class prompts in the pilot produced a hijacked agent response that the judge flagged. SPML's lower rate (27%) is consistent with the sneak-preview pattern: SPML attacks lean blunt and Llama 3.3 70B refuses many of them on its own RLHF training, leaving the judge with cleanly clean responses. Deepset and neuralchemy injections produce hijacked outputs at roughly 1-in-2 rates on the agent + judge stack.

The parallel cost-vs-accuracy sweep against Claude Haiku 4.5 and GPT-4o-mini as alternative judges, run on the cached (prompt, agent response) pairs, completed on the report date. Agreement results at n = 500: Sonnet vs Haiku 4.5 = 0.934 (Cohen's kappa 0.799), Sonnet vs GPT-4o-mini = 0.899 (kappa 0.720). Cost for the 500-row sweep: Haiku $0.36 (2.6x cheaper than Sonnet's $0.94), GPT-4o-mini $0.04 (24x cheaper). Haiku 4.5's kappa is at the boundary between substantial and almost-perfect agreement per Landis and Koch (1977); GPT-4o-mini is in the substantial range. Both are candidate production judges if cost optimization becomes load-bearing for the full eval-set Defense B run. Full disagreement breakdown is in `results/defense_b_judge_cost_comparison.md`.

## 2.4 Defense C: combined pipeline (pilot-scale)

The plan's stretch goal of evaluating a combined input-then-output defense (Defense C) was promoted to a main result after the 500-row pilot data was sufficient to compute it without further inference. Defense C is defined as the OR-combination of Defense A (input classifier) and Defense B (output-side judge): a prompt is flagged if Defense A says INJECTION or if Defense B says the agent's response is HIJACKED. On the same 500-row pilot subset, headline F1 results (with bootstrap 95% CIs):

| Defense | F1 [95% CI] | Precision [95% CI] | Recall [95% CI] |
|---|---|---|---|
| A: DeBERTa alone | 0.849 [0.819, 0.876] | 0.960 [0.937, 0.978] | 0.761 [0.715, 0.802] |
| B: Sonnet judge alone | 0.590 [0.534, 0.642] | 1.000 [1.000, 1.000] | 0.418 [0.359, 0.476] |
| C: DeBERTa + B | 0.912 [0.889, 0.932] | 0.964 [0.945, 0.981] | 0.865 [0.825, 0.901] |
| C: DeBERTa+PG2 ensemble + B | 0.914 [0.892, 0.934] | 0.961 [0.940, 0.978] | 0.873 [0.833, 0.908] |

Paired McNemar tests, run on the 500 same-prompt outcomes: C vs DeBERTa alone produces b = 0 and c = 26 (p < 1e-6); C vs Sonnet judge alone produces b = 8 and c = 112 (p effectively zero). C strictly dominates either component on every paired comparison, by construction (the OR-combination cannot lose on any prompt) and substantially in practice (~10 percentage points of recall lift over the best single defense at essentially no precision cost, because Sonnet judge has perfect precision on the pilot at minimum-rubric stage).

This finding closes the central project question of whether layered defenses add real value over single defenses, with statistically robust evidence at pilot scale. Full-scale Defense C (n = 4,546) is a follow-up run scheduled for the next session and is expected to tighten the confidence intervals without changing the qualitative conclusion. Defense C pilot writeup at `results/defense_c_pilot.md`.

## 2.4 Pipeline and reproducibility infrastructure

The repository is structured into reusable modules (`src/`), notebook-driven analysis (`notebooks/`), runnable scripts (`scripts/`), and gitignored caches (`cache/`). Defense A wrappers `src/defense_a/deberta.py` and `src/defense_a/prompt_guard.py` produce uniform per-prompt records (label, label_id, injection_score, score). Defense B wrappers `src/defense_b/agent.py` and `src/defense_b/judge.py` mirror the same schema and include both `ClaudeJudge` and `GPT4oJudge` classes. The judge wrapper catches BadRequestError and PermissionDeniedError from the API and records the case as `judge_blocked=True` rather than crashing scaling runs.

The cache layer `src/cache.py` implements a JSONL append-log with existing-keys lookup, making every API-driven run resumable mid-process. All API calls are at temperature 0, making cache semantics deterministic for binary classification. `src/metrics.py` consolidates the bootstrap-CI, Cohen's kappa, and McNemar's test routines that were initially inlined in the pilot notebooks.

Total spend across all API work to date is approximately $0.20 (Anthropic Claude judging dominates). The projected full-project spend remains in the $500-$800 envelope originally communicated to Hiflylabs.

# 3. Work to Be Done

The remaining work to the June 8 final deadline is captured in `_project_notes/capstone_plan.md`. The path from this interim to final is:

Phase 1 (in progress through May 18): formal Defense B 500-row pilot at scale (currently running); judge cost-vs-accuracy sweep on the same 500 cases against Claude Haiku 4.5 and GPT-4o-mini to inform the production-judge choice; iteration on the judge rubric after reviewing pilot verdicts; full-eval-set Defense A run consolidated to a unified output; Colab Pro GPU adapter for the formal Defense A scale-up.

Phase 2 (May 19 - 25, judge validation and gold subset): I label 150 agent-output cases against the operational definitions decision tree, producing a human ground-truth set. Cohen's kappa is computed between my labels and each LLM judge. A 500-row GPT-4o subsample provides the cross-judge robustness check that is currently only sketched at n = 8.

Phase 3 (May 26 - June 1, BIPIA indirect injection): implement the BIPIA email-QA task adapter (Yi et al., 2025), run all three defense configurations through it, and analyze. The go/no-go decision on expanding to a second BIPIA task type is at the end of this week.

Phase 4 (June 2 - 8, writing and submission): statistical analysis notebook (`notebooks/09_analysis_and_plots.ipynb`) consolidates per-defense metrics with bootstrap CIs, paired McNemar comparisons (with Holm-Bonferroni correction across pre-specified primary comparisons), per-subcategory breakdowns, and threshold analysis. The business decision framework (Section 6a of the plan) maps these statistical results to deployment recommendations under different cost ratios. Final 20-25 page report, 10-20 slide deck, and 3-page public CEU summary are due June 8.

# 4. Problems and Issues

## 4.1 Judge-model-family sensitivity at the minimum-rubric stage

The Claude vs GPT-4o judge disagreement on the deepset 8 sneak preview (75% agreement at n = 8) is larger than the implementation plan anticipated. The plan addresses this through the 500-row GPT-4o sensitivity sub-sample (Phase 2) and the 150-row human gold subset, both of which remain on the schedule. The cost-vs-accuracy judge sweep being run on the 500-row pilot will quantify this at meaningful scale; if Cohen's kappa between Sonnet 4.6 and the cheaper alternatives is above 0.8, the production-judge cost-optimization question is answered with real data. If kappa is lower, the production rubric needs more iteration than originally scoped; that iteration is within the Phase 2 budget but pushes against the buffer.

## 4.2 Methodological complexity beyond original scope

Two statistical questions surfaced during execution that warrant outside review and have been raised with Professor Zoltan Toth: defensible comparisons across imbalanced attack subcategories (some neuralchemy subcategories have as few as 12 rows), and rubric robustness across judge model families. The first influences how per-subcategory findings can be presented in the final report; the second influences whether the cheap-judge cost-optimization is a real path or a false economy. Professor Toth is currently out of town; a written primer with both questions has been prepared (`_local/zoltan_primer.md`) and the email sent. These consultations are intended for the June 8 final report quality and are not on the critical path to the May 11 interim.

## 4.3 Scope of measurement limitation

As stated in the implementation plan (Section 3 of v2), this evaluation measures the agent's textual compliance with injection attempts, not tool-execution side effects. An agent producing an innocuous-looking text response while silently firing a malicious tool call is a vector this evaluation cannot observe. Real-tool evaluation requires a sandboxed framework such as AgentDojo (Debenedetti et al., 2024) and is marked as future work. This is an existing, documented limitation and is not a new problem; it is restated here because reviewer questions in this area are anticipated.

## 4.4 Meta Prompt Guard 2 license

License access for Meta Prompt Guard 2 86M was approved on 2026-05-08, mid-execution. The classifier has now been run on all three datasets at pilot scale. No remaining blockers on this front.

## 4.5 Inference-provider migration during Defense B pilot

The Groq on-demand tier's 100,000 tokens-per-day cap was reached partway through the 500-row pilot launched on 2026-05-11. The Groq Developer tier (pay-as-you-go, sufficient throughput) was temporarily closed to new signups. The agent role was migrated to Together AI's hosted `meta-llama/Llama-3.3-70B-Instruct-Turbo` endpoint, which has the same model class and no daily quota. Pricing is comparable (~$0.88/M tokens vs Groq's $0.59/$0.79 in/out per million). The migration preserves the methodological position of the study: the agent is still a Llama 3.3 70B instance simulated via system prompt, consistent with the Hiflylabs deployment context (their clients run self-hosted Llama 3.3). No experimental scope change is required.

# 5. References

Debenedetti, E., Zhang, J., Balunovic, M., Beurer-Kellner, L., Fischer, M., & Tramer, F. (2024). *AgentDojo: A dynamic environment to evaluate prompt injection attacks and defenses for LLM agents* [Paper presentation]. NeurIPS 2024 Datasets and Benchmarks Track. arXiv:2406.13352.

Greshake, K., Abdelnabi, S., Mishra, S., Endres, C., Holz, T., & Fritz, M. (2023). *Not what you've signed up for: Compromising real-world LLM-integrated applications with indirect prompt injection* [Paper presentation]. AISec '23: 16th ACM Workshop on Artificial Intelligence and Security. arXiv:2302.12173.

Landis, J. R., & Koch, G. G. (1977). The measurement of observer agreement for categorical data. *Biometrics*, 33(1), 159-174.

Northcutt, C. G., Athalye, A., & Mueller, J. (2021). *Pervasive label errors in test sets destabilize machine learning benchmarks* [Paper presentation]. NeurIPS 2021 Datasets and Benchmarks Track. arXiv:2103.14749.

OWASP GenAI Project. (2025). *LLM01:2025 prompt injection*. OWASP Top 10 for LLM Applications. https://genai.owasp.org/llmrisk/llm01-prompt-injection/

Perez, F., & Ribeiro, I. (2022). *Ignore previous prompt: Attack techniques for language models* [Paper presentation]. NeurIPS 2022 ML Safety Workshop. arXiv:2211.09527.

Yi, J., Xie, Y., Zhu, B., Kiciman, E., Sun, G., Xie, X., & Wu, F. (2025). Benchmarking and defending against indirect prompt injection attacks on large language models. In *Proceedings of the 31st ACM SIGKDD Conference on Knowledge Discovery and Data Mining* (pp. 1809-1820). https://doi.org/10.1145/3690624.3709179
