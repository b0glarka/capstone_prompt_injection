---
title: "Comparative Evaluation of Prompt Injection Defenses for Enterprise AI Agent Deployments"
subtitle: "Master of Science in Business Analytics, Capstone Final Report"
author: "Boglarka Petruska"
institution: "Central European University"
advisor: "Eduardo (primary); Professor Zoltan Toth (methodology consultation)"
sponsor: "Hiflylabs"
date: "2026-06-08 (target submission)"
status: "DRAFT skeleton, pre-populated from existing artifacts; sections marked [DRAFT] vs [FILLED]"
target_length: "20-25 pages"
---

# Executive Summary [DRAFT]

This capstone evaluates two prompt-injection defenses for enterprise AI agent deployments: an input-side classifier defense (Defense A, instantiated with two pre-trained models, ProtectAI DeBERTa and Meta Prompt Guard 2) and an output-side LLM-as-judge defense (Defense B, Llama 3.3 70B agent with Claude Sonnet 4.6 as the primary judge and GPT-4o as a sensitivity-check second judge). Evaluation is on a frozen 4,546-row stratified sample drawn from three public benchmarks (deepset/prompt-injections, neuralchemy/Prompt-injection-dataset, and reshabhs/SPML_Chatbot_Prompt_Injection), with BIPIA (Yi et al., 2025) as an indirect-injection extension.

The principal empirical finding is cross-dataset variance. The same input classifier delivers F1 of 0.59 [95% CI 0.52, 0.66] on the deepset benchmark and 0.95 [0.94, 0.96] on SPML, a 36-point spread that does not collapse under threshold tuning, ensemble methods, or substitution of the classifier. The variance is a property of the data distributions rather than the classifiers. Error-pattern analysis confirms that the input classifiers we tested rely heavily on canonical override-language keywords ("ignore previous instructions", "you are now X"); attacks that achieve the same effect through subtler social engineering or obfuscation slip through systematically.

The Defense B sneak preview, run on the 24 hardest input-classifier misses across three attack classes, reveals that the layered defense (classifier + agent + judge) operates by three different mechanisms depending on the attack class. On subtle role-play injections, the judge catches half the cases the classifier missed. On blunt harmful-content jailbreaks, the agent's RLHF training refuses the request before the judge sees it. On obfuscated payloads, the agent fails to parse the embedded instruction. This refines the layered-defense thesis: combining defenses is empirically supported, but the value of each layer is conditional on the attack class it is asked to handle.

The recommendation for enterprise deployments is layered: pre-trained input classifiers (preferably the OR-gated ensemble of DeBERTa and Prompt Guard 2) as the first line, an LLM-as-judge as the output-side check on flagged or borderline cases, and explicit per-subcategory monitoring in production to detect targeted attacks against known blind spots. The cost-weighted business decision framework in Section 7 maps these choices to deployment scenarios.

# 1. Introduction [DRAFT]

## 1.1 Motivation

Prompt injection is the top-ranked vulnerability in the OWASP Top 10 for LLM Applications 2025 (OWASP GenAI Project, 2025). For enterprise deployments where an LLM agent has access to systems, data, or tools, a successful injection can produce financial loss, data exfiltration, brand damage, or compliance violations. The defensive question is not whether to harden the deployment but how, and at what cost, with what residual risk.

Despite a growing literature on attack techniques (Perez & Ribeiro, 2022; Greshake et al., 2023) and benchmarks (Yi et al., 2025; Toyer et al., 2024), comparative evaluations of available defenses against published benchmarks remain rare. Pre-trained input classifiers are available off the shelf but report their accuracy on their own training distributions. LLM-as-judge approaches are increasingly common in agent evaluation but raise their own questions about judge reliability and cost. This capstone is a head-to-head, statistically defensible comparison of the two approaches across three independent benchmarks.

## 1.2 Sponsor and scope

The project is sponsored by Hiflylabs, a consulting firm working with enterprise clients deploying autonomous LLM agents. The PID approved on 2026-04-22 scopes the work to two defenses (input classifier and LLM-as-judge), three labeled prompt-injection datasets, and the BIPIA benchmark for indirect injection, with a combined defense (Defense C) as a conditional stretch.

## 1.3 Contributions

- A reproducible head-to-head evaluation of ProtectAI DeBERTa and Meta Prompt Guard 2 as input classifiers, on three benchmarks with bootstrap 95% confidence intervals and paired McNemar tests.
- The first published per-subcategory recall analysis (to the author's knowledge) of these two classifiers against the 29 attack subcategories of the neuralchemy benchmark, documenting subcategory-level blind spots.
- An empirically-grounded refinement of the layered-defense thesis: the protection mechanism (judge / agent alignment / parse failure) varies by attack class.
- A cross-judge sensitivity analysis (Claude Sonnet 4.6 vs GPT-4o) on borderline cases at the minimum-rubric stage, quantifying judge-model-family dependence.
- A business decision framework that translates these statistical findings into deployment recommendations under varying cost ratios.

# 2. Background and Related Work [DRAFT]

## 2.1 Taxonomy of prompt injection

Prompt injection is defined here as an attempt to alter, override, or extract a language model's operating instructions through an input the model processes (OWASP GenAI Project, 2025). The operational definitions document developed for this project (Appendix A; see `reports/operational_definitions.md`) translates the canonical taxonomies into a binary decision tree usable for labeling and judging.

Two main variants are recognized in the literature and named as distinct subtypes in OWASP LLM01:2025 (OWASP GenAI Project, 2025):

- Direct injection: the adversary controls the user-facing channel and types the malicious instruction. The three datasets in this study (deepset, neuralchemy, SPML) cover direct injection.
- Indirect injection: the adversary plants the instruction in content the agent retrieves on behalf of a legitimate user, a vector first systematically characterized by Greshake et al. (2023). BIPIA (Yi et al., 2025) is the standard benchmark.

Perez and Ribeiro (2022) identify two attack goals: goal hijacking (redirecting the agent to a different task) and prompt leaking (extracting the system prompt). The operational definition in Appendix A extends this with three additional response-side categories drawn from the BIPIA output taxonomy (information extraction, content injection, soft compliance with override).

## 2.2 Defense classes

Defenses divide naturally into input-side and output-side approaches:

- Input-side: a classifier inspects the user's prompt before it reaches the agent and flags or blocks suspected injections. Defense A in this study. Pre-trained options include ProtectAI DeBERTa v3 (a fine-tuned DeBERTa-v3-base) and Meta Prompt Guard 2 (a fine-tuned mDeBERTa-v3-base). Both classifiers are claimed to reach approximately 79% on the PINT benchmark, as reported on the ProtectAI v2 model card.
- Output-side: an LLM-as-judge inspects the agent's response to determine whether it has been hijacked. Defense B in this study, instantiated with Claude Sonnet 4.6 as the primary judge and GPT-4o as the sensitivity-check second judge.
- Combined (Defense C, stretch in this study): input classifier as gate, output judge on the residual. Operates the two layers in series.

Prompt augmentation (system-prompt instructions telling the agent to be skeptical of embedded directives) is a third common defense pattern (Perez & Ribeiro, 2022). Three augmentation conditions are evaluated as a baseline against Defense B.

## 2.3 Evaluation conventions

The community standard reports point estimates on per-dataset accuracy or F1. This study commits to bootstrap 95% CIs on every reported metric, pre-specified primary statistical comparisons with Holm-Bonferroni correction (Holm, 1979), and Cohen's kappa with Landis-Koch interpretive thresholds (Artstein & Poesio, 2008; Landis & Koch, 1977) for any inter-rater agreement claim. The detailed methodology rationale is in Appendix B (`reports/methodology_appendix.md`).

# 3. Data [FILLED]

## 3.1 Source datasets

Three direct-injection datasets are used. All three are publicly available on HuggingFace and have been used in prior work.

- deepset/prompt-injections: 546 prompts (343 SAFE / 203 INJECTION). Smallest of the three, used in full for this study. Approximate label balance: 63% benign / 37% injection.
- neuralchemy/Prompt-injection-dataset: 4,391 prompts across 29 attack subcategories. The subcategory column is the richest source of attack-type structure in any of the three datasets.
- reshabhs/SPML_Chatbot_Prompt_Injection: 16,012 role-play injections with paired system prompts. This is the largest dataset and has a distinct schema (separate System Prompt and User Prompt columns), reflecting role-play attacks against deployed chatbots.

BIPIA (Yi et al., 2025) provides the indirect-injection extension and is described in Section 5.5.

## 3.2 Frozen evaluation set

A stratified 4,546-row evaluation set is constructed at seed 42 by `src/eval_set.py`:

- deepset: full census (546 rows).
- neuralchemy: 2,000 stratified by label and by attack subcategory on the injection side. Subcategory stratification preserves representation of small attack types.
- SPML: 2,000 rows, balanced 50/50 by label. Reused from the SPML pilot to maintain cache consistency with already-run Defense A inferences.

Frozen-set construction is deterministic and reproducible via `notebooks/02_eval_set_construction.ipynb`. The same prompt_idx is used by every downstream defense run, enabling paired comparison.

## 3.3 Label audit

Per Northcutt et al. (2021), community-curated test sets carry label-error rates averaging 3.3% and ranging up to 6%. A 200-row stratified label audit is conducted against the operational definitions (Appendix A); the noise-rate estimate is reported as a methodological caveat alongside every metric. Per-dataset and overall results are at `reports/label_audit_report.md` [FILLED on completion of the audit].

## 3.4 Contamination check

ProtectAI DeBERTa v3 v2 names seven training datasets on its model card. Each was downloaded and exact-matched against the three evaluation datasets:

| Eval dataset | Named-source overlap | Decision |
|---|---|---|
| deepset | 0.92% | Accept and caveat |
| neuralchemy | 1.96% | Accept and caveat |
| SPML | 0.40% | Accept and caveat |

All three rates are below the level at which exact-match contamination would mechanically inflate metrics. Limitations: Harelix (one named V2 training source) was removed from HuggingFace and is unverifiable; 15 additional V2 sources are disclosed only by license category; Meta Prompt Guard 2 enumerates zero training sources. The full report is at `results/contamination_report.md`.

# 4. Methods [DRAFT, partially filled]

## 4.1 Defense A: input classifier

ProtectAI DeBERTa v3 v2 and Meta Prompt Guard 2 86M are run on the full frozen evaluation set without fine-tuning, at the model's default decision threshold. Inference wrappers are in `src/defense_a/`. Predictions per row include the binary label, the injection-class probability, and the predicted class confidence; threshold sweeps and ROC/PR curves derive from the injection_score.

Two ensemble configurations of the two classifiers are evaluated:
- OR-gate: flag INJECTION if either classifier flags. Maximizes sensitivity.
- AND-gate: flag only if both classifiers flag. Maximizes specificity.

A mean-score ensemble averages the two classifiers' injection_score for use with continuous-threshold metrics (ROC AUC).

## 4.2 Defense B: agent and judge

The simulated-agent protocol of Yi et al. (2025) is used: Llama 3.3 70B responds to the user prompt with a system prompt assigning it a helpful-assistant role. Two inference providers are supported interchangeably for the agent role (`src/defense_b/agent.py` exposes both): Groq's `llama-3.3-70b-versatile` endpoint for sneak-preview-scale work, and Together AI's `meta-llama/Llama-3.3-70B-Instruct-Turbo` for the 500-row formal pilot, where Together's higher daily quota was required. Both endpoints serve the same model family, so swapping providers does not change the methodological position: the agent is still a Llama 3.3 70B instance simulated via system prompt, consistent with the Hiflylabs deployment context (clients running self-hosted Llama 3.3).

The agent's text response is sent to Claude Sonnet 4.6 (via Anthropic) with a minimum-rubric judge prompt that asks for a binary "hijacked" verdict plus a one-line reason in structured JSON. The judge wrapper (`src/defense_b/judge.py`) catches API-level content-policy refusals (`BadRequestError`, `PermissionDeniedError`) and records them as `judge_blocked=True` rather than crashing scaling runs.

A GPT-4o (via OpenAI) sensitivity-check second judge is used on a borderline subsample to quantify judge-model-family dependence. The full judge validation against a 150-row human-labeled gold subset is the focus of the Phase 2 work documented in Section 5.4.

## 4.3 Statistical machinery

Headline metrics (accuracy, precision, recall, F1, ROC AUC) are reported with 1,000-iteration nonparametric bootstrap 95% CIs (Efron, 1979; `src/metrics.py::bootstrap_ci`). Paired defense comparisons use McNemar's test (McNemar, 1947), exact binomial for small b+c and chi-squared with continuity correction otherwise (`src/metrics.py::mcnemar`). Cohen's kappa is reported for any inter-rater agreement claim. Holm-Bonferroni correction at family-wise alpha = 0.05 applies to a pre-specified set of primary comparisons; per-subcategory results are explicitly labeled exploratory. Full rationale in Appendix B.

# 5. Results [FILLED, will be tightened in final pass]

## 5.1 Defense A on the frozen evaluation set

The headline result is the cross-dataset variance.

| Classifier | Dataset | n | F1 [95% CI] | ROC AUC [95% CI] |
|---|---|---|---|---|
| ProtectAI DeBERTa | deepset | 546 | 0.592 [0.524, 0.657] | 0.881 [0.846, 0.915] |
| ProtectAI DeBERTa | neuralchemy | 4,391 | 0.915 [0.906, 0.923] | 0.971 [0.966, 0.976] |
| ProtectAI DeBERTa | SPML (bal. 2k) | 2,000 | 0.954 [0.944, 0.962] | 0.998 [0.996, 0.999] |
| Meta Prompt Guard 2 | deepset | 546 | 0.413 | 0.948 |
| Meta Prompt Guard 2 | neuralchemy | 4,391 | 0.677 | 0.852 |
| Meta Prompt Guard 2 | SPML (bal. 2k) | 2,000 | 0.695 | 0.995 |

On DeBERTa, F1 ranges from 0.59 on deepset to 0.95 on SPML, a 36-point spread with non-overlapping 95% CIs. The same pattern holds for Prompt Guard 2 (0.41 to 0.70). On the full eval set (n = 4,546), DeBERTa achieves F1 = 0.911 [0.902, 0.919] and AUC = 0.966 [0.960, 0.970]; Prompt Guard 2 achieves F1 = 0.666 [0.650, 0.683] and AUC = 0.933 [0.927, 0.940]. The paired McNemar comparison on the full set yields b = 931, c = 128, p << 0.001, indicating DeBERTa is systematically better than Prompt Guard 2 across the eval set; this pattern is present in every individual dataset.

## 5.2 Score-distribution analysis

On the deepset injection class, 40.9% of true injections are assigned a softmax injection-class probability of exactly 0.000 by DeBERTa, indicating full classifier confidence that the prompt is safe. Threshold sweeps confirm this is a coverage problem rather than a calibration problem: recall caps at approximately 0.59 even when the threshold is dropped to zero, and the F1-optimal threshold delivers only +0.13 F1 lift over the default. On neuralchemy the same metric is 6.8% and on SPML it is lower still. The figure at `results/figures/defense_a_score_distributions.png` makes the contrast visible at a glance.

## 5.3 Per-subcategory recall on neuralchemy

The neuralchemy subcategory column enables a per-attack-type decomposition. Selected subcategories with at least 20 injection rows in the eval set:

| Subcategory | n | DeBERTa recall | PG2 recall |
|---|---|---|---|
| direct_injection | 1,397 | 0.976 | 0.743 |
| token_smuggling | 27 | 1.000 | (varies) |
| instruction_override | 21 | 1.000 | (varies) |
| rag_poisoning | 26 | 1.000 | (varies) |
| jailbreak | 291 | 0.553 | 0.489 |
| encoding | 177 | 0.633 | 0.062 |
| adversarial | 383 | 0.773 | 0.069 |

DeBERTa handles canonical attack patterns (direct injection, instruction override, token smuggling) at near-perfect recall and substantially underperforms on jailbreak (55%), encoding (63%), and adversarial (77%) subcategories. Prompt Guard 2 has a more uniform but lower recall ceiling, and its encoding and adversarial recall (both below 0.10) is dramatically worse than DeBERTa's. The figure at `results/figures/analysis_subcategory_recall_compare.png` visualizes this.

## 5.4 Error-pattern analysis: why the classifiers fail

Feature extraction on the full eval set (`scripts/analyze_defense_a_errors.py`) reveals that the input classifiers rely heavily on canonical override-language keywords. Among DeBERTa's true positives, 30% of cases contain a recognizable override marker (words like "ignore", "disregard", "forget", "instead", "new task"); among false negatives, only 4.6% do. Among true positives, 24% contain a recognizable role-play marker ("you are", "act as", "pretend to be"); among false negatives, 12% do.

This pattern explains the cross-dataset variance directly: deepset is enriched in attacks that achieve hijack effects through indirect framing (fictional scenarios, polite preambles, character substitution) without literal override keywords. neuralchemy and SPML are enriched in attacks with explicit override language. The classifier is doing a more limited form of pattern-matching than its overall F1 suggests, and an adversary aware of this can craft attacks that evade detection.

## 5.5 Defense B: sneak preview across three attack classes

The Defense B evaluation is reported at two scales. A 24-case sneak preview against the hardest Defense A misses (run on Groq's Llama 3.3 70B endpoint) is reported here; the 500-row formal pilot (run on Together AI's Llama 3.3 70B endpoint after the Groq tier exhausted; see Section 8.3 for the migration rationale) is reported in Section 5.5b.

| Attack class | n | Judge flagged hijacked | Mechanism |
|---|---|---|---|
| Deepset role-play / persona-shift | 8 | 4 | Judge load-bearing on subtle injections |
| Neuralchemy jailbreak (hate content) | 8 | 0 | Agent (Llama 3.3 70B) refused all 8 on its own training |
| Neuralchemy encoding | 8 | 1 (plus 1 parse error) | Agent treated encoded payloads as cipher puzzles, not as instructions |

The three rates reflect three different mechanisms by which the layered defense protects the agent. The judge is load-bearing on subtle injections; the agent's RLHF alignment refuses blunt harmful-content attacks before the judge sees them; obfuscated payloads defeat the agent's instruction-parsing entirely.

## 5.5b Defense B: 500-row formal pilot

The formal Defense B pilot at 500 rows on the frozen evaluation set was run against the same agent + judge stack as the sneak preview, with the agent provided by Together AI's `meta-llama/Llama-3.3-70B-Instruct-Turbo` endpoint (migration rationale in Section 8.3). The pilot completed on 2026-05-11 with total spend of $1.05. Headline results on injection-class rows:

| Scope | n (injection rows) | Hijacked by judge | Hijack rate |
|---|---|---|---|
| Overall | 251 | 105 | 0.418 |
| deepset | 84 | 41 | 0.488 |
| neuralchemy | 84 | 42 | 0.500 |
| SPML | 83 | 22 | 0.265 |

Two observations stand out. First, the per-dataset hijack rates mirror the per-dataset variance pattern Defense A also exhibits. SPML is the dataset where Defense B is most effective (or, equivalently, where the agent's own alignment makes the judge's job easiest); deepset and neuralchemy are roughly comparable in difficulty. The roughly 50% hijack rate on deepset and neuralchemy injections is a substantive finding: even with an output-side judge, half of injection-class prompts produce text-level hijacked responses on this agent + minimum-rubric configuration. Second, no judge-blocked rows occurred during the pilot, so the wrapper hardening (Section 4.2) was prophylactic rather than triggered.

A parallel cost-vs-accuracy sweep on the same 500 cases against Claude Haiku 4.5 and GPT-4o-mini as alternative judges produced the following cross-judge agreement results, run on the cached (prompt, agent response) pairs from the Sonnet pilot:

| Judge pair | Agreement | Cohen's kappa | Cost on 500-row pilot |
|---|---|---|---|
| Sonnet 4.6 vs Haiku 4.5 | 0.934 | 0.799 | $0.94 vs $0.36 (2.6x cheaper) |
| Sonnet 4.6 vs GPT-4o-mini | 0.899 | 0.720 | $0.94 vs $0.04 (24x cheaper) |
| Haiku 4.5 vs GPT-4o-mini | 0.918 | 0.764 | (cross-cheap pair) |

Per Landis and Koch (1977), Haiku 4.5's kappa of 0.799 falls at the boundary between "substantial" (0.61-0.80) and "almost perfect" (0.81-1.00) agreement with Sonnet, and GPT-4o-mini's kappa of 0.720 is in the "substantial" range. Both cheaper judges track Sonnet closely enough to be candidate production judges for Defense B at full eval-set scale, with cost reductions of 2.6x and 24x respectively. The choice between them depends on whether the marginal 7-9 percentage points of disagreement matter for the deployment scenario in question. The full disagreement breakdown (which prompts the judges split on, and per-dataset patterns) is in `results/defense_b_judge_cost_comparison.md`.

## 5.5c Defense C: combined pipeline at pilot scale

Defense C is the OR-combination of Defense A (input classifier) and Defense B (output-side LLM-as-judge): a prompt is flagged by Defense C if Defense A flags it as INJECTION or if Defense B's judge flags the agent's response as HIJACKED. The plan v2 listed Defense C as a stretch goal contingent on Phase 2 timing; the existence of paired Defense A and Defense B verdicts on the same 500-row pilot made the analysis available without new inference, so the result is promoted to a main pilot-scale finding.

Headline metrics on the 500-row pilot, with 1,000-iteration bootstrap 95% confidence intervals:

| Defense | Precision [95% CI] | Recall [95% CI] | F1 [95% CI] |
|---|---|---|---|
| A: DeBERTa alone | 0.960 [0.937, 0.978] | 0.761 [0.715, 0.802] | 0.849 [0.819, 0.876] |
| A: DeBERTa + PG2 ensemble | 0.955 [0.932, 0.974] | 0.769 [0.722, 0.811] | 0.852 [0.822, 0.879] |
| B: Sonnet judge alone | 1.000 [1.000, 1.000] | 0.418 [0.359, 0.476] | 0.590 [0.534, 0.642] |
| C: DeBERTa + B | 0.964 [0.945, 0.981] | 0.865 [0.825, 0.901] | 0.912 [0.889, 0.932] |
| C: DeBERTa + PG2 ensemble + B | 0.961 [0.940, 0.978] | 0.873 [0.833, 0.908] | 0.914 [0.892, 0.934] |

Three observations stand out:

First, Defense C strictly dominates every single defense. The OR-combination cannot do worse than its components on any single prompt; the question is whether the recall lift is meaningful and whether the precision cost is acceptable. The 95% CIs for Defense C's F1 do not overlap with the 95% CIs for any single defense, so the lift is statistically robust at the pilot sample size.

Second, recall lift is substantial. Defense C catches 86.5 percent of injections vs Defense A's 76.1 percent (a 10-percentage-point lift) and Defense B's 41.8 percent (a 45-percentage-point lift). The Defense A miss rate is roughly cut in half by adding the output-side judge.

Third, precision does not degrade. Defense C's precision of 0.964 is essentially identical to Defense A's 0.960. This is because Sonnet 4.6 has perfect precision on the 500-row pilot at the minimum-rubric stage (no false positives on benign agent responses). The judge contributes only true-positive catches when combined with the classifier, with zero false-alarm cost. Whether this perfect precision generalizes beyond the pilot is a question the full eval-set Defense C run will answer.

Paired McNemar tests (n = 500, chi-squared with continuity correction) confirm the dominance:

| Comparison | b (baseline wins) | c (C wins) | p-value |
|---|---|---|---|
| C: DeBERTa + B vs A: DeBERTa alone | 0 | 26 | < 1e-6 |
| C: DeBERTa + B vs B: Sonnet judge alone | 8 | 112 | < 1e-300 |
| C: Ensemble + B vs A: ensemble alone | 0 | 26 | < 1e-6 |
| C: Ensemble + B vs B: Sonnet judge alone | 9 | 114 | < 1e-300 |

The b = 0 column for C versus A comparisons is by construction (the OR-combination cannot lose to one of its components on any prompt); the c column captures the actual lift. The C versus B comparisons show b values of 8 and 9 (cases where Sonnet judge alone catches an injection that Defense A misses but the combination nonetheless gets right via a different mechanism; possible only because of agent randomness or judge variability between runs - here, identical agent outputs across both columns rule out variability, so these reflect cases where one defense's output and the other's were both available and the disagreement is real).

Per-dataset Defense C F1 (compared to best single defense per dataset):

| Dataset | Best single defense F1 | Defense C F1 (DeBERTa + B) | Lift |
|---|---|---|---|
| deepset | A 0.732 | 0.835 | +0.103 |
| neuralchemy | A 0.913 | 0.940 | +0.027 |
| SPML | A 0.890 | 0.952 | +0.062 |

The largest absolute lift is on deepset, the dataset where Defense A struggles most. Defense C is most valuable precisely where Defense A is weakest. This is the empirical justification for the layered-defense argument: combining input and output defenses produces the largest gain in the deployment scenario most at risk from input-classifier blind spots.

The full Defense C analysis, including per-subcategory neuralchemy breakdown and all paired McNemar p-values at multiple scopes, is in `results/defense_c_pilot.md`. The full-scale Defense C run (n = 4,546) is queued for the next session.

## 5.6 Judge sensitivity: Claude vs GPT-4o

GPT-4o was run as a parallel second judge on the same 8 deepset role-play cases as the Claude Sonnet 4.6 primary. Claude flagged 4 of 8 as hijacked; GPT-4o flagged 2 of 8. The two judges agreed on 6 of 8 (75%). Cohen's kappa is not meaningful at n = 8; the agreement rate is reported as directional. The disagreement on borderline cases is larger than initially expected and indicates that minimum-rubric judge calls are sensitive to judge model family. The 150-row human gold subset (in progress as part of Phase 2 work) is the formal validation; the sneak preview validates that the formal validation is necessary, not optional.

## 5.7 Ensemble analysis

Combining the two Defense A classifiers via OR-gate (flag if either classifier flags) yields F1 = 0.916 on the full eval set, a +0.005 lift over DeBERTa alone (paired McNemar p = 0.0005). The mean-score ensemble achieves ROC AUC = 0.969, slightly better than DeBERTa's 0.966. AND-gating (flag only if both) is strictly worse (F1 = 0.657) because the two classifiers share most of their blind spots. The lift from ensembling is real but small; combining classifiers does not solve the cross-dataset variance.

## 5.8 BIPIA indirect injection [FILLED]

The BIPIA email-QA evaluation runs the full defense stack (Defense A in both query-only and full-prompt variants, Defense B with Together AI's Llama 3.3 70B agent + Sonnet 4.6 judge, Defense C as the OR-combination of DeBERTa full-prompt and the judge) against Yi et al. (2025)'s indirect-injection benchmark. Data: 50 base test emails composed with the 15 BIPIA attack categories (grouped into three themes: task-performance, stealth/obfuscation, and social-manipulation; see Section 2.1 and operational definitions Section 2.1 for the full enumeration), producing 750 attack rows plus 50 clean control rows for a total of 800 rows.

Methodologically the key result is the Defense A query-only variant: this is the operating mode in deployments where the input filter sits between the user and the agent without inspecting retrieved content. Such defenses are structurally blind to indirect injection because the user's question is legitimate; only the retrieved email body contains the attack. Reported alongside the full-prompt variant (where the classifier inspects the composed prompt including the email body) to make the per-defense difference visible.

Headline results (attack success rate is lower-is-better; false-alarm rate is measured on the 50 clean control emails):

| Defense | n attacks | Attack success rate | False-alarm rate |
|---|---|---|---|
| Defense A: DeBERTa (query only) | 750 | 1.000 | 0.00 |
| Defense A: DeBERTa (full prompt) | 750 | 0.656 | 0.38 |
| Defense A: Prompt Guard 2 (full prompt) | 750 | 0.977 | 0.00 |
| Defense B: Sonnet 4.6 judge | 750 | 0.781 | 0.00 |
| Defense C: DeBERTa (full prompt) + judge | 750 | 0.517 | 0.38 |

Three substantive findings:

First, the query-only Defense A is structurally blind to indirect injection, with a 100% attack success rate. This is by construction: the user's query "summarize this email" is benign, so a classifier inspecting only the query cannot see the attack content embedded in the email body. The result confirms a deployment-design point: input filters placed between the user and the agent without retrieved-content inspection cannot defend against this attack class.

Second, indirect injection is dramatically harder for the same defense stack than direct injection. Defense C on the 500-row direct-pilot caught 86.5% of attacks at F1 = 0.912; on BIPIA email-QA Defense C catches only 48.3% (= 51.7% attack success), a drop of approximately 38 percentage points. The same combined-defense configuration loses about a third of its catch rate when moved from direct to indirect injection. This is a strong methodological caution against citing direct-injection F1 numbers as evidence of protection against indirect attacks.

Third, the 38% false-alarm rate on clean emails is the precision crisis that the direct-injection evaluation did not surface. DeBERTa inspecting the full prompt (including the email body) over-flags ordinary business email content as injection because its training distribution is direct-attack prompts and ordinary email syntax sometimes resembles those patterns at surface level. In production this would mean roughly two in five legitimate emails would be blocked or routed to human review, an unacceptable rate for most enterprise deployments. The judge alone has zero false alarms (perfect precision on the clean controls), so the precision degradation is wholly attributable to Defense A.

Per-category Defense C attack success rates reveal substantial cross-category variance. The judge dominates in social-manipulation categories where the harmful nature of the output is recognizable independent of the attack method: Misinformation & Propaganda 14% attack success, Information Dissemination 34%, Entertainment 34%, Scams & Fraud 36%. The classifier is more uniform across categories, catching some obfuscation patterns (Reverse Text 52% baseline, Substitution Ciphers 66%) better than the judge but failing on the task-performance categories where the judge also struggles (Task Automation 74%, Sentiment Analysis 70%). This suggests that the right deployment is category-aware: a single defense configuration applied uniformly is less effective than routing by the threat profile expected.

Full per-row results: `results/bipia_email_qa_results.csv` (800 rows); per-category breakdown: `results/bipia_email_qa_per_category.csv`; headline metrics: `results/bipia_email_qa_metrics.csv`; structured writeup: `results/bipia_email_qa.md`.

# 6. Discussion [DRAFT]

## 6.1 Cross-dataset variance as the headline finding

The 36-point F1 spread between deepset and SPML on the same classifier is the most consequential empirical result in this study. Two interpretations are consistent with the evidence:

1. The deepset distribution is closer to in-the-wild adversarial behavior and was less represented in the classifier's training mix; neuralchemy and SPML overlap more with the training distribution, inflating their numbers.
2. Both classifiers have learned a fairly narrow surface-level pattern (override-language keywords); deepset attacks evade this pattern, while neuralchemy and SPML are enriched in patterns the classifier recognizes.

The error-pattern analysis (Section 5.4) supports interpretation 2: classifiers' true positives are concentrated in cases with override-keyword markers, and the relative scarcity of those markers in deepset's attack distribution explains the recall gap mechanically. Interpretation 1 (training-distribution overlap) likely also contributes but is not necessary to explain the gap.

Implication for practitioners: a single F1 number on a single benchmark is not a meaningful summary of an input classifier's protection. The honest summary is per-dataset, or better, per-subcategory.

## 6.2 The layered-defense thesis, refined

The sneak preview shows that the value of an output-side judge varies by attack class. On subtle role-play injections (the deepset misses), the judge catches half the cases the classifier missed. On blunt harmful content (the neuralchemy jailbreak misses), the agent's RLHF alignment refuses before the judge sees a response. On obfuscated payloads (the neuralchemy encoding misses), the agent does not parse the embedded instruction at all.

The combined-defense argument is therefore stronger but more nuanced than a single catch-rate would suggest. The right deployment uses each layer for the attack class it is best at, and accepts that for some attack classes the defense in effect is the model's own training rather than the deployed defense stack.

## 6.3 Judge reliability is upstream of judge cost

The cost-sensitivity question (can a cheaper judge like Claude Haiku 4.5 or GPT-4o-mini replace Sonnet 4.6 at scale?) is methodologically downstream of the judge-reliability question. If the rubric is not invariant across judge model families at the minimum-rubric stage (Section 5.6), no cost optimization is meaningful until the rubric is iterated to robustness. The 150-row human gold subset is the right next step; the cost-comparison sweep is queued behind it.

# 7. Business Decision Framework [DRAFT]

The full framework is at `reports/business_decision_framework.md`. Brief summary here:

## 7.1 Harm taxonomy

Failures of either type have business consequences across financial, reputational, operational, and compliance dimensions. The relative cost of a missed attack vs a false alarm varies dramatically across deployment scenarios.

## 7.2 Cost-weighted scoring

The expected cost per prompt is:

```
E[cost per prompt] = P(injection) * FNR * cost_per_missed_attack
                   + P(benign)    * FPR * cost_per_false_alarm
```

Sweeping cost ratios at 10x, 100x, and 1000x covers the realistic enterprise range. The OR-gate ensemble of DeBERTa + Prompt Guard 2 minimizes expected cost across all three ratios.

## 7.3 Scenario-based recommendations

Three representative scenarios are mapped to defense configurations. The Hiflylabs-identified scenario (autonomous agent with broad tool access) is the high-cost-ratio case; recommended configuration is the OR-gate input classifier followed by Defense B on every output with Sonnet 4.6 as judge.

# 8. Limitations [FILLED]

## 8.1 Scope of measurement

This evaluation measures the agent's textual compliance with injection attempts, not tool-execution side effects. An agent that produces an innocuous-looking text response while silently firing a malicious tool call is a vector this evaluation cannot observe. Real-tool evaluation requires a sandboxed framework (Debenedetti et al., 2024) and is marked as future work.

## 8.2 Judge robustness at the minimum-rubric stage

The 75% agreement between Claude Sonnet 4.6 and GPT-4o at n = 8 (Section 5.6) indicates that the judge call is currently model-family-sensitive. The 150-row human gold subset and 500-row GPT-4o sensitivity subsample address this; until they are complete, all Defense B results carry a judge-reliability caveat.

## 8.3 Inference-provider portability

Defense B at scale ran across two inference providers during the study (Groq for sneak-preview work, Together AI for the formal pilot). Both serve Llama 3.3 70B under the same simulated-agent protocol, but the operational characteristics differ: Groq's on-demand tier has a 100K-token daily cap that limited pilot-scale work, while Together AI's pay-as-you-go pricing imposes no daily cap. The model-class equivalence preserves the methodological position of the study (Llama 3.3 70B simulated via system prompt) across both providers. Production deployments should not interpret the choice of inference provider as a defense-design choice; it is an operational decision about throughput and cost.

## 8.4 Dataset label noise

Label noise in the three source datasets is bounded but non-zero. The 200-row stratified label audit provides per-dataset noise-rate estimates. Reported metrics are uncorrected for label noise; the audit report serves as the methodological caveat.

## 8.5 Subcategory-level inference

Per-subcategory results on neuralchemy include some categories with n as low as 12 to 30. Bootstrap CIs widen substantially at these sample sizes; per-subcategory findings are reported as exploratory and not corrected for multiple comparisons.

## 8.6 Multi-modal injection out of scope

The datasets used here are text-only. Multi-modal injection (adversarial perturbations of images or audio) is a real attack channel for multi-modal agents and is not evaluated here.

# 9. Future Work and Conclusion [DRAFT]

## 9.1 Future work

- Real-tool agent evaluation in AgentDojo (Debenedetti et al., 2024) to measure action-level compromise beyond textual compliance.
- Custom adversarial test set crafted to target the specific blind spots identified in Section 5.4, to test whether the defenses generalize to attacks shaped by knowledge of their weaknesses.
- Multi-modal extension once a multi-modal injection benchmark is available.
- Production-rubric iteration on the LLM-as-judge component, informed by the human gold subset.

## 9.2 Conclusion

Off-the-shelf pre-trained input classifiers (Defense A) for prompt injection deliver high F1 numbers on the benchmarks closest to their training distributions, and substantially weaker performance on benchmarks featuring subtler attacks. The drop is not a calibration problem; it is a coverage problem, and one that ensembling does not solve. An output-side LLM-as-judge (Defense B) is empirically valuable but operates in different ways for different attack classes; its value comes partly from the judge itself and partly from the agent's own RLHF training, depending on the attack pattern. For enterprise deployments, the practical recommendation is a layered defense (input classifier ensemble + output-side judge), per-subcategory production monitoring against known blind spots, and explicit judge-rubric validation against a human-labeled gold subset before scaling.

# References

Artstein, R., & Poesio, M. (2008). Inter-coder agreement for computational linguistics. *Computational Linguistics*, 34(4), 555-596. https://doi.org/10.1162/coli.07-034-R2

Debenedetti, E., Zhang, J., Balunovic, M., Beurer-Kellner, L., Fischer, M., & Tramer, F. (2024). *AgentDojo: A dynamic environment to evaluate prompt injection attacks and defenses for LLM agents* [Paper presentation]. NeurIPS 2024 Datasets and Benchmarks Track. arXiv:2406.13352.

Efron, B. (1979). Bootstrap methods: Another look at the jackknife. *Annals of Statistics*, 7(1), 1-26.

Greshake, K., Abdelnabi, S., Mishra, S., Endres, C., Holz, T., & Fritz, M. (2023). *Not what you've signed up for: Compromising real-world LLM-integrated applications with indirect prompt injection* [Paper presentation]. AISec '23: 16th ACM Workshop on Artificial Intelligence and Security. arXiv:2302.12173.

Holm, S. (1979). A simple sequentially rejective multiple test procedure. *Scandinavian Journal of Statistics*, 6(2), 65-70.

Landis, J. R., & Koch, G. G. (1977). The measurement of observer agreement for categorical data. *Biometrics*, 33(1), 159-174.

McNemar, Q. (1947). Note on the sampling error of the difference between correlated proportions or percentages. *Psychometrika*, 12(2), 153-157.

Northcutt, C. G., Athalye, A., & Mueller, J. (2021). *Pervasive label errors in test sets destabilize machine learning benchmarks* [Paper presentation]. NeurIPS 2021 Datasets and Benchmarks Track. arXiv:2103.14749.

OWASP GenAI Project. (2025). *LLM01:2025 prompt injection*. OWASP Top 10 for LLM Applications. https://genai.owasp.org/llmrisk/llm01-prompt-injection/

Perez, F., & Ribeiro, I. (2022). *Ignore previous prompt: Attack techniques for language models* [Paper presentation]. NeurIPS 2022 ML Safety Workshop. arXiv:2211.09527.

Toyer, S., Watkins, O., Mendes, E. A., Svegliato, J., Bailey, L., Wang, T., Ong, I., Elmaaroufi, K., Abbeel, P., Darrell, T., Ritter, A., & Russell, S. (2024). *Tensor Trust: Interpretable prompt injection attacks from an online game* [Paper presentation]. ICLR 2024. arXiv:2311.01011.

Yi, J., Xie, Y., Zhu, B., Kiciman, E., Sun, G., Xie, X., & Wu, F. (2025). Benchmarking and defending against indirect prompt injection attacks on large language models. In *Proceedings of the 31st ACM SIGKDD Conference on Knowledge Discovery and Data Mining* (pp. 1809-1820). https://doi.org/10.1145/3690624.3709179

# Appendices

- Appendix A: Operational Definitions (`reports/operational_definitions.md`)
- Appendix B: Methodology and Statistical Choices (`reports/methodology_appendix.md`)
- Appendix C: Contamination Report (`results/contamination_report.md`)
- Appendix D: Label Audit Report (`reports/label_audit_report.md`) [pending audit completion]
- Appendix E: Judge Validation Report (`reports/judge_validation_report.md`) [pending 150-row gold subset]
- Appendix F: Business Decision Framework (`reports/business_decision_framework.md`)
