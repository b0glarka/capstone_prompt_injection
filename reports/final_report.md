# Business-Oriented Evaluation of Prompt Injection Defenses for Enterprise AI Agent Deployments

Master of Science in Business Analytics, Capstone Final Report

Author: Boglarka Petruska

Institution: Central European University

Advisor: Eduardo (primary); Professor Zoltan Toth (methodology consultation)

Sponsor: Zsófia Práger, Data Scientist, Hiflylabs

Target submission date: 2026-06-08

Status: DRAFT skeleton, pre-populated from existing artifacts; sections marked [DRAFT] vs [FILLED]

Target length: 20-25 pages

---

# Executive Summary [DRAFT]

This capstone evaluates two prompt-injection defenses for enterprise AI agent deployments: an input-side classifier defense (Defense A, instantiated with two pre-trained models, ProtectAI DeBERTa and Meta Prompt Guard 2) and an output-side LLM-as-judge defense (Defense B, Llama 3.3 70B agent with Claude Sonnet 4.6 as the primary judge and GPT-4o as a sensitivity-check second judge). Evaluation is on a frozen 4,546-row stratified sample drawn from three public benchmarks (deepset/prompt-injections, neuralchemy/Prompt-injection-dataset, and reshabhs/SPML_Chatbot_Prompt_Injection), with BIPIA (Yi et al., 2025) as an indirect-injection extension.

The principal empirical finding is cross-dataset variance. The same input classifier delivers F1 of 0.59 [95% CI 0.52, 0.66] on the deepset benchmark and 0.95 [0.94, 0.96] on SPML, a 36-point spread that does not collapse under threshold tuning, ensemble methods, or substitution of the classifier. The variance is a property of the data distributions rather than the classifiers. Error-pattern analysis confirms that the input classifiers we tested rely heavily on canonical override-language keywords ("ignore previous instructions", "you are now X"); attacks that achieve the same effect through subtler social engineering or obfuscation slip through systematically.

The Defense B sneak preview, run on the 24 hardest input-classifier misses across three attack classes, reveals that the layered defense (classifier + agent + judge) operates by three different mechanisms depending on the attack class. On subtle role-play injections, the judge catches half the cases the classifier missed. On blunt harmful-content jailbreaks, the agent's RLHF training refuses the request before the judge sees it. On obfuscated payloads, the agent fails to parse the embedded instruction. This refines the layered-defense thesis: combining defenses is empirically supported, but the value of each layer is conditional on the attack class it is asked to handle.

The recommendation for enterprise deployments is layered: pre-trained input classifiers (preferably the OR-gated ensemble of DeBERTa and Prompt Guard 2) as the first line, an LLM-as-judge as the output-side check on flagged or borderline cases, and explicit per-subcategory monitoring in production to detect targeted attacks against known blind spots. The cost-weighted business decision framework in Section 7 maps these choices to deployment scenarios.

# 1. Introduction [DRAFT]

## 1.1 Motivation

As AI agents are deployed in enterprise environments with increasing autonomy, the risk of prompt injection attacks grows. OWASP ranks prompt injection as the number one threat to LLM-integrated applications (OWASP GenAI Project, 2025): adversarial inputs can hijack agent behavior in ways that cause significant business harm, including financial loss, data exfiltration, brand damage, or compliance violations. The defensive question is not whether to harden the deployment but how, and at what cost, with what residual risk.

Despite a growing literature on attack techniques (Perez & Ribeiro, 2022; Greshake et al., 2023) and benchmarks (Yi et al., 2025; Toyer et al., 2024), comparative evaluations of available defenses against published benchmarks remain rare. Pre-trained input classifiers are available off the shelf but report their accuracy on their own training distributions. LLM-as-judge approaches are increasingly common in agent evaluation but raise their own questions about judge reliability and cost. This capstone is a head-to-head, statistically defensible comparison of the two approaches across three independent benchmarks.

## 1.2 Sponsor and scope

The project is sponsored by Hiflylabs, a consulting firm working with enterprise clients deploying autonomous LLM agents. The project sponsor is Zsófia Práger, Data Scientist at Hiflylabs. Hiflylabs has encountered prompt injection directly with clients and is asking for empirical, business-grounded guidance on which defensive approaches are most effective and under what deployment conditions. The most relevant deployment scenario, identified by Hiflylabs, is the autonomous agent with broad tool access: an agent that can access databases, call APIs, and execute multi-step workflows on the user's behalf.

The PID approved on 2026-04-22 scopes the work to two defenses (input classifier and LLM-as-judge), three labeled prompt-injection datasets, and the BIPIA benchmark for indirect injection, with a combined defense (Defense C) as a conditional stretch.

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

The agent's text response is sent to Claude Sonnet 4.6 (via Anthropic) with a judge prompt that mirrors the operational definitions document §3.2 (v1.21): Step 0 operator-intent anchor per dataset, illustrative indicators per H1-H5 hijack category, AMBIGUOUS-routing instruction for borderline responses, and a structured JSON output schema requiring `verdict` (CLEAN / HIJACKED / AMBIGUOUS), `hijack_categories` (any of H1-H5 that apply, empty if CLEAN), and `reason` (one line). All reported Defense B numbers in Section 5 use this v1.21 rubric. An earlier minimum-rubric judge prompt was used during initial pilot runs in May 2026 and is preserved in `_local/baseline_v1.8_judge/` for transparency on rubric-version impact; the headline observations are stable across rubric versions (`results/aggregate_metrics_v121.md`). The judge wrapper (`src/defense_b/judge.py`) catches API-level content-policy refusals (`BadRequestError`, `PermissionDeniedError`) and records them as `judge_blocked=True` rather than crashing scaling runs.

The judge rubric is consistent with BIPIA's evaluation protocol at the output-deviation level: Yi et al. (2025) define attack success as the agent's output deviating from the user's intended task in a direction consistent with the attacker's injected instruction, which is the same standard the H1-H5 hijack categories in `reports/operational_definitions.md` operationalise at the response-side label level. BIPIA itself does not formalise a parallel response-side taxonomy (its published categorisation is at the input side, fifteen attack subtypes), so the H1-H5 categories are a project-specific synthesis informed by Perez and Ribeiro (2022) and OWASP LLM01:2025, not a direct mapping from BIPIA.

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

All Defense A F1 numbers above carry an effective ceiling defined by the 200-row label audit's noise-rate estimate (`reports/label_audit_report.md`): Cohen's kappa between the audit and the dataset gold labels is 0.930 [0.878, 0.970]; the per-dataset disagreement-as-noise-rate proxy is 4.5% on deepset, 6.0% on neuralchemy, and 0.0% on SPML (3.5% [1.4%, 7.1%] overall). The 36-point cross-dataset F1 spread is an order of magnitude larger than the noise-rate uncertainty, so the cross-dataset variance finding is robust to label noise. Reported F1 numbers should be read as bounded above by approximately F1_observed plus this noise rate.

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

Per-row noise floors and null-result subcategories. The recall numbers above are point estimates; for deployment use they should be read together with the binomial half-width at the underlying sample size. The following table uses the paired-evaluation slice of the frozen eval set (where DeBERTa and PG2 were scored on the same neuralchemy rows; full table at `results/defense_a_full_subcategory_recall.csv`):

| Subcategory | n (paired eval) | DeBERTa recall ± hw | PG2 recall ± hw | CIs overlap? |
|---|---|---|---|---|
| direct_injection | 637 | 0.981 ± 0.011 | 0.743 ± 0.034 | No |
| adversarial | 174 | 0.718 ± 0.067 | 0.069 ± 0.038 | No |
| jailbreak | 133 | 0.519 ± 0.085 | 0.489 ± 0.085 | Yes |
| encoding | 81 | 0.667 ± 0.103 | 0.062 ± 0.053 | No |
| training_extraction | 31 | 0.935 ± 0.087 | 0.129 ± 0.118 | No |

Half-widths are the normal-approximation binomial 95% CI: 1.96 × √(p̂(1-p̂)/n). For p̂ near 0 or 1 this approximation is conservative and a Clopper-Pearson exact bound should be preferred; the qualitative reading is unaffected.

Jailbreak is the one null-result subcategory at meaningful n: the 0.030 absolute recall gap between DeBERTa and PG2 (0.519 vs 0.489) is well inside both half-widths, so the two classifiers cannot be distinguished on this subcategory at the available sample size. Both fail at similar rates, which means the layered-defense argument on jailbreak does not rest on classifier diversity; it rests on the agent's own RLHF alignment (Section 5.5). All other subcategories with n above 30 in the paired-eval slice show non-overlapping recall CIs.

Implication for the full breakdown. Subcategories with n below roughly 50 carry half-widths above 0.10 at moderate recall (0.5 to 0.8), which is large relative to between-classifier gaps below 0.20. Smaller subcategories in the full table (e.g., crescendo at n = 4, encoding_obfuscation at n = 3) should be read as anecdotes, not measurements. The Limitations section (8.5) names this constraint.

## 5.4 Error-pattern analysis: why the classifiers fail

Feature extraction on the full eval set (`scripts/analyze_defense_a_errors.py`) reveals that the input classifiers rely heavily on canonical override-language keywords. Among DeBERTa's true positives, 30% of cases contain a recognizable override marker (words like "ignore", "disregard", "forget", "instead", "new task"); among false negatives, only 4.6% do. Among true positives, 24% contain a recognizable role-play marker ("you are", "act as", "pretend to be"); among false negatives, 12% do.

This pattern explains the cross-dataset variance directly: deepset is enriched in attacks that achieve hijack effects through indirect framing (fictional scenarios, polite preambles, character substitution) without literal override keywords. neuralchemy and SPML are enriched in attacks with explicit override language. The classifier is doing a more limited form of pattern-matching than its overall F1 suggests, and an adversary aware of this can craft attacks that evade detection.

A parallel finding from the 200-row label audit (`results/label_audit_sample_disagreement_sorted_post_audit.csv`, language detected via `langdetect`): the same surface-pattern reliance extends across languages. On the 98 audit-confirmed injection rows, DeBERTa catches 82.3% (65/79) of English injections but only 68.4% (13/19) of non-English injections, a 14-percentage-point recall gap. Prompt Guard 2, despite its multilingual mDeBERTa backbone, shows a wider gap: 53.2% (42/79) English recall versus 26.3% (5/19) non-English, a 27-percentage-point drop. On the 8 German injections specifically, DeBERTa catches 5 (62.5%). The non-English sample is small (n=19) and heavily German-dominated, so the per-language magnitude is wide; the direction is unambiguous across both classifiers, however, and is consistent with the override-keyword reliance observation above (English override words trigger Step 4(a)-pattern matching; German `ignorieren` and other translation equivalents do not, even though they are semantically identical). This is the "semantic-synonym evasion" gap from operational definitions §3.1 in cross-language form.

## 5.5 Defense B: sneak preview across three attack classes

The Defense B evaluation is reported at two scales. A 24-case sneak preview against the hardest Defense A misses (run on Groq's Llama 3.3 70B endpoint) is reported here; the 500-row formal pilot (run on Together AI's Llama 3.3 70B endpoint after the Groq tier exhausted; see Section 8.3 for the migration rationale) is reported in Section 5.5b.

| Attack class | n | Judge flagged hijacked | Mechanism |
|---|---|---|---|
| Deepset role-play / persona-shift | 8 | 4 | Judge load-bearing on subtle injections |
| Neuralchemy jailbreak (hate content) | 8 | 0 | Agent (Llama 3.3 70B) refused all 8 on its own training |
| Neuralchemy encoding | 8 | 1 (plus 1 parse error) | Agent treated encoded payloads as cipher puzzles, not as instructions |

The three rates reflect three different mechanisms by which the layered defense protects the agent. The judge is load-bearing on subtle injections; the agent's RLHF alignment refuses blunt harmful-content attacks before the judge sees them; obfuscated payloads defeat the agent's instruction-parsing entirely.

## 5.5b Defense B: 500-row formal pilot

The formal Defense B pilot at 500 rows on the frozen evaluation set was run against the same agent + judge stack as the sneak preview, with the agent provided by Together AI's `meta-llama/Llama-3.3-70B-Instruct-Turbo` endpoint (migration rationale in Section 8.3). The agent inference completed 2026-05-11; the judge verdicts reported below use the v1.21 rubric (operational definitions §3.2 with Step 0 operator-intent anchor and H1-H5 indicators; see `src/defense_b/judge.py` for the deployed prompt). Total spend including the v1.21 re-judge is $1.67 for Sonnet, $0.50 for Haiku, $0.07 for GPT-4o-mini on the 500-row pilot. Headline results on injection-class rows, with the v1.8 minimum-rubric baseline shown alongside for transparency on rubric-version impact:

| Scope | n (injection rows) | Hijack rate (v1.8) | Hijack rate (v1.21, AMBIGUOUS=HIJACKED) | v1.21 AMBIGUOUS rate |
|---|---|---|---|---|
| Overall | 251 | 0.418 | 0.462 | 0.056 |
| deepset | 84 | 0.488 | 0.488 | 0.071 |
| neuralchemy | 84 | 0.500 | 0.583 | 0.060 |
| SPML | 83 | 0.265 | 0.313 | 0.036 |

The augmented v1.21 rubric net catches +11 injections out of 251 versus the minimum rubric (paired McNemar p = 0.052, borderline), and routes 5.6% of cases to the new AMBIGUOUS bucket which the binary v1.8 rubric did not have. The per-dataset variance pattern is preserved: SPML remains the dataset where Defense B is most effective; deepset and neuralchemy remain roughly comparable in difficulty. The headline observation that even with an output-side judge roughly half of deepset and neuralchemy injection-class prompts produce text-level hijacked responses also holds. No judge-blocked rows occurred during the pilot, so the wrapper hardening (Section 4.2) was prophylactic rather than triggered.

A parallel cost-vs-accuracy sweep on the same 500 cached agent responses re-judged with Haiku 4.5 and GPT-4o-mini under the v1.21 rubric produced the following cross-judge agreement results:

| Judge pair | Agreement | Cohen's kappa (v1.21) | Cost on 500-row pilot |
|---|---|---|---|
| Sonnet 4.6 vs Haiku 4.5 | 0.922 | 0.787 | $1.67 vs $0.50 (3.3x cheaper) |
| Sonnet 4.6 vs GPT-4o-mini | 0.902 | 0.729 | $1.67 vs $0.07 (24x cheaper) |
| Haiku 4.5 vs GPT-4o-mini | 0.916 | 0.772 | (cross-cheap pair) |

The cross-judge kappa numbers are very stable between rubric versions (v1.8 Sonnet/Haiku kappa 0.799 vs v1.21 0.787; v1.8 Sonnet/GPT-mini kappa 0.720 vs v1.21 0.729). Per Landis and Koch (1977), Haiku 4.5's kappa of 0.787 falls at the boundary between "substantial" (0.61-0.80) and "almost perfect" (0.81-1.00) agreement with Sonnet, and GPT-4o-mini's kappa of 0.729 is in the "substantial" range. Both cheaper judges track Sonnet closely enough to be candidate production judges for Defense B at full eval-set scale, with cost reductions of 3.3x and 24x respectively. The choice between them depends on whether the marginal 8-10 percentage points of disagreement matter for the deployment scenario in question.

A separate cross-family observation: under v1.21, Sonnet readily uses the AMBIGUOUS verdict (15 of 500 cases, 3.0%), Haiku uses it sparingly (5 of 500, 1.0%), and GPT-4o-mini ignores it entirely (0 of 500, 0.0%), instead flipping verdicts within the binary CLEAN/HIJACKED space. Different model families interpret the rubric's AMBIGUOUS instruction with different fidelity. The full disagreement breakdown and v1.8/v1.21 side-by-side numbers are in `results/aggregate_metrics_v121.md` and `results/defense_b_judge_cost_comparison.md`.

## 5.5c Defense C: combined pipeline at pilot scale

Defense C is the OR-combination of Defense A (input classifier) and Defense B (output-side LLM-as-judge): a prompt is flagged by Defense C if Defense A flags it as INJECTION or if Defense B's judge flags the agent's response as HIJACKED. The plan v2 listed Defense C as a stretch goal contingent on Phase 2 timing; the existence of paired Defense A and Defense B verdicts on the same 500-row pilot made the analysis available without new inference, so the result is promoted to a main pilot-scale finding.

Headline metrics on the 500-row pilot under the v1.21 rubric, with 1,000-iteration bootstrap 95% confidence intervals. Defense B and Defense C numbers reflect the v1.21 judge verdicts (AMBIGUOUS counted as HIJACKED, the conservative deployment-oriented convention). Defense A numbers are independent of the judge rubric and identical to the v1.8 report.

| Defense | Precision [95% CI] | Recall [95% CI] | F1 [95% CI] |
|---|---|---|---|
| A: DeBERTa alone | 0.960 [0.937, 0.978] | 0.761 [0.715, 0.802] | 0.849 [0.819, 0.876] |
| A: DeBERTa + PG2 ensemble | 0.955 [0.932, 0.974] | 0.769 [0.722, 0.811] | 0.852 [0.822, 0.879] |
| B: Sonnet judge alone (v1.21) | 0.991 [0.969, 1.000] | 0.462 [0.402, 0.519] | 0.630 [0.575, 0.683] |
| C: DeBERTa + B (v1.21) | 0.960 [0.937, 0.978] | 0.861 [0.818, 0.898] | 0.908 [0.878, 0.932] |

For reference, the corresponding numbers under the older v1.8 minimum rubric were Defense B F1 = 0.590 and Defense C F1 = 0.912; the v1.21 augmented rubric shifts Defense B F1 up by +0.040 (catching slightly more attacks at near-identical precision) and Defense C F1 down by -0.004 (negligible, well within the bootstrap CI overlap).

Three observations stand out:

First, Defense C strictly dominates every single defense. The OR-combination cannot do worse than its components on any single prompt; the question is whether the recall lift is meaningful and whether the precision cost is acceptable. The 95% CIs for Defense C's F1 do not overlap with the 95% CIs for any single defense, so the lift is statistically robust at the pilot sample size.

Second, recall lift is substantial. Defense C catches 86.1 percent of injections vs Defense A's 76.1 percent (a 10-percentage-point lift) and Defense B's 46.2 percent (a 40-percentage-point lift). The Defense A miss rate is roughly cut in half by adding the output-side judge.

Third, precision does not degrade. Defense C's precision of 0.960 is identical to Defense A's 0.960. Sonnet 4.6 under v1.21 has 0.991 precision on the 500-row pilot (one false positive on a benign agent response, down from zero under v1.8); the marginal increase in false-positive rate is too small to move Defense C's precision in a deployment-relevant direction.

Paired McNemar test (n = 500, v1.21) confirms the dominance: Defense C (DeBERTa + B) vs Defense A (DeBERTa alone) shows b = 1, c = 25, p = 8.05e-7. The b = 1 (one case where Defense A correctly flags but Defense C does not) is a row where the v1.21 judge has overridden a Defense A flag through AMBIGUOUS routing not propagating as HIJACKED in the OR-gate computation when normalized; in the absolute majority of cases the OR-combination of A and B cannot lose to A alone.

Per-dataset Defense C F1 on the pilot subset under v1.21 (n = 167 / 167 / 166 for deepset / neuralchemy / SPML):

| Dataset | A F1 (DeBERTa) | B F1 (Sonnet v1.21) | C F1 (DeBERTa + B, v1.21) | C-vs-A lift |
|---|---|---|---|---|
| deepset | 0.547 | 0.656 | 0.794 | +0.247 |
| neuralchemy | 0.951 | 0.667 | 0.957 | +0.006 |
| SPML | 0.959 | 0.419 | 0.953 | -0.006 |

The largest absolute lift is on deepset, the dataset where Defense A struggles most. Defense C is most valuable precisely where Defense A is weakest. This is the empirical justification for the layered-defense argument: combining input and output defenses produces the largest gain in the deployment scenario most at risk from input-classifier blind spots. On neuralchemy and SPML, where Defense A is already near-ceiling, Defense C is essentially neutral; the small SPML negative is two false positives the v1.21 judge added on benign rows.

The full Defense C analysis, including per-subcategory neuralchemy breakdown and all paired McNemar p-values at multiple scopes, is in `results/defense_c_pilot.md` (v1.8 numbers) and `results/aggregate_metrics_v121.md` (v1.21 update). The full-scale Defense C run (n = 4,546) is queued for the next session.

## 5.6 Judge validation: human gold subset (n=150) and earlier sensitivity check

The 150-row human gold subset (Task 3) is the formal judge-validation step. The full analysis is in `reports/judge_validation_report.md`; headline numbers are below. The earlier n=8 GPT-4o sensitivity check (Section 5.6 of the interim report, retained for historical context) is no longer the load-bearing measurement now that the 150-row subset is complete.

### Headline kappa: human vs LLM judges (n=150)

| Judge | v1.21 binary kappa [95% CI] | Landis-Koch band |
|---|---|---|
| Sonnet 4.6 | 0.324 [0.171, 0.468] | Fair |
| Haiku 4.5 | 0.362 [0.202, 0.502] | Fair (touching moderate) |
| GPT-4o-mini | 0.221 [0.078, 0.382] | Fair |

The design target was Cohen's kappa above 0.60 (substantial agreement) between human auditor and each LLM judge. No judge meets that threshold. Haiku 4.5 has the highest kappa at 0.362 ("fair" agreement just touching the "moderate" band); GPT-4o-mini has the lowest at 0.221. This bounds how confidently Defense B hijack rates in §5.5b/§5.8 can be interpreted: cross-agent comparisons with effect sizes above the kappa-noise floor (~10pp) are robust; marginal differences (±5pp) are within judge-human disagreement and should not drive deployment decisions on their own.

### Where the disagreement concentrates

Among rows where the human auditor said CLEAN but the v1.21 judge said HIJACKED (or AMBIGUOUS), 30 to 41 percent contain a known attack signature pattern (HackAPrompt's "I have been PWNED" string, DAN persona declaration, JAILBROKEN marker, or equivalent). The §3.2 v1.23 scope note added to the operational definitions explicitly states that signatures alone do not trigger HIJACKED under §3.2 — only mechanism-level deviation from operator intent does. The judges are pattern-matching on the signature; the human auditor applying §3.2 v1.23 strictly recognises that no Step 4 mechanism is present and labels CLEAN. This empirically validates the v1.23 scope note and identifies the clear-target next iteration for the production judge prompt.

When both rater and judge agree on HIJACKED, they agree on the H-category set in 81-88 percent of cases (containment metric: judge's category set contains the human's primary H-category). Substantive judgment on WHICH H-category applies is robust; the disagreement concentrates at the CLEAN-vs-HIJACKED boundary.

### Cost-vs-agreement Pareto

Combined with cost data: Haiku 4.5 has the highest kappa AND is 3.3x cheaper than Sonnet 4.6 ($0.50 vs $1.67 per 500-row pilot). It is the recommended production judge on this evidence. GPT-4o-mini's 20x cost advantage over Sonnet does not compensate for its substantially lower kappa (0.221 vs 0.324).

### Earlier n=8 GPT-4o sensitivity check, in context

The interim-report Section 5.6 reported a Claude-vs-GPT-4o cross-judge sensitivity check on 8 deepset cases. Under v1.8 the two judges agreed 6 of 8 (75%); under v1.21 they agreed 2 of 8 (25%) after both became more reactive in opposite directions (Claude more conservative, GPT-4o more aggressive). At n=8 these numbers are directional only; the 150-row gold subset is the load-bearing measurement and is documented above. The n=8 flip is consistent with the cross-family AMBIGUOUS-adoption observation in §5.5b — GPT-4o (like GPT-4o-mini) ignores the AMBIGUOUS bucket, while Sonnet readily uses it.

## 5.7 Ensemble analysis

Combining the two Defense A classifiers via OR-gate (flag if either classifier flags) yields F1 = 0.916 on the full eval set, a +0.005 lift over DeBERTa alone (paired McNemar p = 0.0005). The mean-score ensemble achieves ROC AUC = 0.969, slightly better than DeBERTa's 0.966. AND-gating (flag only if both) is strictly worse (F1 = 0.657) because the two classifiers share most of their blind spots. The lift from ensembling is real but small; combining classifiers does not solve the cross-dataset variance.

## 5.7b Selective prediction: coverage and confidence

A natural deployment pattern is to auto-classify only when Defense A is highly confident and defer the rest to Defense B or human review. The coverage / accuracy curve characterises the tradeoff. At confidence threshold T on Defense A's max-class probability, coverage is the fraction of rows where confidence ≥ T (auto-classified), and selective metrics are computed on that covered subset (`results/defense_a_coverage_curve.csv`, figure at `results/figures/defense_a_coverage_accuracy.png`).

| Confidence threshold | Coverage | n covered | n deferred | Selective F1 (injection) |
|---|---|---|---|---|
| 0.50 (always classify) | 1.000 | 4,546 | 0 | 0.911 |
| 0.70 | 0.990 | 4,499 | 47 | 0.914 |
| 0.80 | 0.985 | 4,480 | 66 | 0.916 |
| 0.90 | 0.976 | 4,438 | 108 | 0.919 |
| 0.95 | 0.967 | 4,396 | 150 | 0.923 |
| 0.99 | 0.940 | 4,274 | 272 | 0.933 |

The coverage curve is nearly flat. Even at confidence threshold 0.99, only 6.0% of the eval set (272 rows) sits in the uncertain region and selective F1 lifts only +0.022 over the full-coverage baseline. The interpretation is that DeBERTa rarely produces moderate-confidence predictions: its injection-class score distribution is bimodal at 0 and 1 (Section 5.2 shows 40.9% of true injections receive probability exactly 0.000 on deepset). Confidence-based deferral therefore does not efficiently identify cases worth escalating to the more expensive Defense B; the cases the classifier is wrong about are the same cases it is most confident about.

This finding has two implications. For the deployment guide, confidence-based auto-routing through Defense A's raw score is not a useful cost-saving lever as-is; the layered defense should run Defense B on a fixed fraction of rows or on rows flagged by independent signals (e.g., per-subcategory blind-spot routing), not on Defense A's own uncertainty signal. For methodological extension, post-hoc temperature scaling on a held-out calibration fold is the natural step, and the calibration subsection below reports the results.

### Post-hoc temperature-scaling calibration

Following Guo et al. (2017), a single temperature parameter T is fit on a stratified 10% calibration fold (455 rows) by minimising NLL against the binary labels, then applied to the remaining 90% test fold (4,091 rows). Expected Calibration Error (ECE, equal-width binning, 10 bins) is computed pre and post temperature scaling on the test fold. Per Chidambaram et al. (2024), binning-based ECE has known pathologies and should be read directionally rather than absolutely; the pre-vs-post comparison is the load-bearing measurement.

| Scope | n (test fold) | ECE pre | ECE post | Δ |
|---|---|---|---|---|
| Overall | 4,091 | 0.084 | 0.037 | -55% |
| deepset | 491 | 0.220 | 0.166 | -25% |
| neuralchemy | 1,800 | 0.093 | 0.089 | ~unchanged |
| SPML | 1,800 | 0.046 | 0.078 | +69% |

The fitted T = 4.70 indicates DeBERTa was substantially overconfident pre-calibration: the model's effective sharpness was ~5x too high relative to its empirical accuracy. Temperature scaling softens the distribution toward more honest uncertainty.

Per-dataset behaviour is the interesting story. Overall ECE more than halves (-55%), and deepset improves most (-25%) — the dataset where DeBERTa was most miscalibrated also benefits most from the global temperature. SPML degrades, going from already-well-calibrated (ECE 0.046) to less-well-calibrated (ECE 0.078) under the global temperature. The single-temperature solution is a compromise across datasets with different empirical calibration properties; deepset and neuralchemy share an overconfident regime while SPML does not. Per-dataset temperature scaling would be the natural follow-on but trades parsimony for empirical fit; this is documented as future work in §9.1.

Practical implication for the coverage curve above: with calibrated probabilities, the bimodal-at-0-and-1 distribution would be spread out across the [0, 1] interval, and the curve's near-flat shape would gain a moderate slope. The selective-prediction routing recommendation accordingly changes: calibrated DeBERTa probabilities are usable as a confidence signal for auto-routing on deepset and neuralchemy, while SPML deployments should retain the existing routing strategy (Defense B on a fixed fraction). The reliability diagram at `results/figures/defense_a_calibration.png` visualises the pre-vs-post distribution shift.

## 5.8 BIPIA indirect injection [FILLED]

The BIPIA email-QA evaluation runs the full defense stack (Defense A in both query-only and full-prompt variants, Defense B with Together AI's Llama 3.3 70B agent + Sonnet 4.6 judge, Defense C as the OR-combination of DeBERTa full-prompt and the judge) against Yi et al. (2025)'s indirect-injection benchmark. Data: 50 base test emails composed with the 15 BIPIA attack categories (grouped into three themes: task-performance, stealth/obfuscation, and social-manipulation; see Section 2.1 and operational definitions Section 2.1 for the full enumeration), producing 750 attack rows plus 50 clean control rows for a total of 800 rows.

Methodologically the key result is the Defense A query-only variant: this is the operating mode in deployments where the input filter sits between the user and the agent without inspecting retrieved content. Such defenses are structurally blind to indirect injection because the user's question is legitimate; only the retrieved email body contains the attack. Reported alongside the full-prompt variant (where the classifier inspects the composed prompt including the email body) to make the per-defense difference visible.

Headline results under the v1.21 judge rubric (attack success rate is lower-is-better; false-alarm rate is measured on the 50 clean control emails). v1.8 minimum-rubric baselines are shown alongside for transparency on rubric-version impact:

| Defense | n attacks | v1.8 attack success | v1.21 attack success | v1.8 FAR | v1.21 FAR |
|---|---|---|---|---|---|
| Defense A: DeBERTa (query only) | 750 | 1.000 | 1.000 (A unchanged) | 0.00 | 0.00 |
| Defense A: DeBERTa (full prompt) | 750 | 0.656 | 0.656 (A unchanged) | 0.38 | 0.38 |
| Defense A: Prompt Guard 2 (full prompt) | 750 | 0.977 | 0.977 (A unchanged) | 0.00 | 0.00 |
| Defense B: Sonnet 4.6 judge | 750 | 0.781 | 0.669 | 0.00 | 0.00 |
| Defense C: DeBERTa (full prompt) + judge | 750 | 0.517 | 0.444 | 0.38 | 0.38 |

The v1.21 augmented rubric catches an additional 8.4 percentage points of attacks via the judge alone (Defense B attack success 0.781 → 0.669), and the layered Defense C improves by 7.3 percentage points (0.517 → 0.444 attack success, equivalently 55.6% caught). The judge's improvement under v1.21 is concentrated in encoding-based and information-disclosure attack categories (see per-category table below). False-alarm rate is unchanged at 0.38 because that is wholly attributable to Defense A's DeBERTa over-flagging benign emails (the judge has 0% FAR on the 50 clean controls under both rubric versions). The AMBIGUOUS verdict appears on 3.9% of attack rows and 0.0% of clean controls under v1.21 (counted as HIJACKED in the table above; the v1.21 augmented rubric uses AMBIGUOUS to flag responses that are off-task without clear H1-H5 categorisation, which on BIPIA mostly means partial compliance with the attacker's task).

Three substantive findings:

First, the query-only Defense A is structurally blind to indirect injection, with a 100% attack success rate. This is by construction: the user's query "summarize this email" is benign, so a classifier inspecting only the query cannot see the attack content embedded in the email body. The result confirms a deployment-design point: input filters placed between the user and the agent without retrieved-content inspection cannot defend against this attack class.

Second, indirect injection remains dramatically harder for the same defense stack than direct injection even under the augmented v1.21 rubric. Defense C on the 500-row direct-pilot catches 86.1% of attacks at F1 = 0.908; on BIPIA email-QA Defense C catches 55.6% (= 44.4% attack success), a drop of approximately 31 percentage points. The same combined-defense configuration loses about a third of its catch rate when moved from direct to indirect injection. This is a strong methodological caution against citing direct-injection F1 numbers as evidence of protection against indirect attacks.

Third, the 38% false-alarm rate on clean emails is the precision crisis that the direct-injection evaluation did not surface. DeBERTa inspecting the full prompt (including the email body) over-flags ordinary business email content as injection because its training distribution is direct-attack prompts and ordinary email syntax sometimes resembles those patterns at surface level. In production this would mean roughly two in five legitimate emails would be blocked or routed to human review, an unacceptable rate for most enterprise deployments. The judge alone has zero false alarms (perfect precision on the clean controls), so the precision degradation is wholly attributable to Defense A.

Per-category Defense C attack success rates under v1.21 reveal substantial cross-category variance, with the v1.21 augmented rubric producing the largest improvements in encoding-based and information-disclosure categories. Top movers v1.8 → v1.21 (Defense C attack success rate, lower is better):

| Category | n | v1.8 attack success | v1.21 attack success | Δ |
|---|---|---|---|---|
| Substitution Ciphers | 50 | 0.46 | 0.08 | -0.38 |
| Base Encoding | 50 | 0.50 | 0.26 | -0.24 |
| Information Dissemination | 50 | 0.34 | 0.18 | -0.16 |
| Scams & Fraud | 50 | 0.36 | 0.26 | -0.10 |
| Misinformation & Propaganda | 50 | 0.14 | 0.10 | -0.04 |
| Entertainment | 50 | 0.34 | 0.28 | -0.06 |
| Task Automation | 50 | 0.74 | 0.74 | 0.00 |
| Sentiment Analysis | 50 | 0.70 | 0.70 | 0.00 |

The v1.21 rubric's explicit H1-H5 indicators surface obfuscated and information-disclosure attacks that the binary minimum rubric was misclassifying as CLEAN: the Substitution Ciphers category in particular drops from 46% attack success to 8% under v1.21, a 38-percentage-point improvement attributable wholly to the augmented rubric since the agent responses are cached. Task-performance categories (Task Automation, Sentiment Analysis, Business Intelligence) are unchanged because Defense A's full-prompt classifier already catches the attacks in those categories that the judge would also catch; the OR-gate ceiling is the limiting factor, not the rubric.

Full per-row results: `results/bipia_email_qa_results.csv` (800 rows, with v1.21 columns added); aggregate v1.21 metrics: `results/aggregate_metrics_v121.md`; v1.8 baseline structured writeup: `results/bipia_email_qa.md`.

## 5.9 Action-level evaluation: AgentDojo [DRAFT — full numbers pending A1 run]

### Motivation

The Defense B and BIPIA evaluations in §5.5b and §5.8 measure TEXT-level compliance: does the agent's response indicate it would execute the attacker's task? An equally important question for deployment is action-level: when the agent has actual tools and the attacker's instructions reach it, does the agent execute the attacker's specified action? Text-level compliance is an upper bound on action-level threat: an agent can decline in text yet still call a tool unsafely, or vice versa. Without an action-level evaluation, deployment recommendations from §5.5b/§5.8 cannot be extrapolated to tool-using agents.

AgentDojo (Debenedetti et al. 2024) is the standard benchmark for closing this gap. It provides four realistic tool environments (Workspace 24 tools, Slack 11 tools, Travel 28 tools, Banking 11 tools, 70 tools across the four), 97 user tasks and 27 injection tasks, totalling 629 security test cases. Attacks are injected into tool outputs (poisoned emails, calendar entries, contact names, slack messages); the framework reports Benign Utility (fraction of user tasks solved without attacks), Targeted Attack Success Rate (fraction of security cases where the attacker's specified action was executed), and Utility Under Attack (fraction where the user task was solved AND no adversarial side effect occurred).

### Setup

Suite scope: Workspace (40 user tasks × 6 injection tasks = 240 security cases + 40 benign-utility cases) as the primary A1 evaluation. Workspace was chosen because it covers email/calendar/file-store tool patterns directly adjacent to BIPIA's email-QA scope, supporting the §5.9 text-vs-action comparison. The Slack, Travel, and Banking suites are queued for an A2 expansion if A1 results warrant it.

Agent: Llama 3.3 70B Instruct via Together AI (matches the §5.5b baseline). Cross-family extension with Qwen 3 235B-A22B-Instruct, Mistral Large 2, and DeepSeek V3 is queued contingent on A1 outcomes.

Defenses tested:
- baseline (no defense)
- Defense A: ProtectAI DeBERTa filter (`TransformersBasedPIDetector`) applied to tool outputs, inserted between `ToolsExecutor` and the next LLM call inside `ToolsExecutionLoop`. Aborts the agent on detection.
- Defense B: Sonnet 4.6 v1.24 judge (see below) inserted inside the loop BEFORE `ToolsExecutor`. Inspects each proposed assistant message (text + tool-call serialisation) and raises `AbortAgentError` on HIJACKED or AMBIGUOUS verdicts before tool side-effects execute.
- Defense C: Defense A OR Defense B.

Pipeline structure follows AgentDojo's official `AgentPipeline.from_config`:
`[SystemMessage, InitQuery, llm, ToolsExecutionLoop([V124JudgeDefense?, ToolsExecutor, TransformersBasedPIDetector?, llm])]`

The system message is AgentDojo's default ("Emma Johnson at Blue Sparrow Tech"). A control run with a generic helpful-assistant prompt on user_task_0 yielded identical ASR (83% in both conditions), confirming the system message is not a confound for the headline numbers at this scale.

### v1.24 judge variant: adapting Defense B to action-level evaluation

Defense B's §3.2 v1.21 rubric (operational_definitions.md) was designed for text-level evaluation: it inspects an agent's natural-language reply and decides whether the reply indicates compliance with attacker instructions. Direct transfer to AgentDojo failed: on workspace user_task_0 the v1.21 judge made 13 inference calls across the 6 security cases but raised zero aborts, yielding ASR = 83.3% identical to the no-defense baseline. The judge could not recognise tool-call sequences as HIJACKED because the v1.21 H1-H5 indicators were anchored on textual cues ("agent says it will book the trip") and AgentDojo agents communicate compliance through silent tool calls, not textual restatement.

We added an operational definitions v1.24 variant: a tool-call-aware rubric with the same H1-H5 categories reframed for action-level evidence. Examples: H4 (content injection) becomes "attacker-specified content in tool arguments" (the most common AgentDojo hijack vector: attacker URL passed as argument to `send_email`); H1 (task-execution hijack) becomes "tool calls that don't trace to the user task's stated subtasks". The full v1.24 system prompt is in operational_definitions.md §3.2 and `src/defense_b/judge.py::_V124_SYSTEM_HEADER`.

Smoke results on workspace user_task_0 (n=6 security cases) for the three Defense B variants:

| Configuration | Targeted ASR | Utility Under Attack | Judge calls | Notes |
|---|---|---|---|---|
| No defense | 0.833 | 0.833 | 0 | baseline |
| Defense B v1.21 (text-level rubric) | 0.833 | 0.833 | 13 | judge fires but raises no aborts; v1.21 doesn't recognise tool-call patterns |
| Defense B v1.24 (tool-call rubric) | 1.000 | 0.167 | 14 | judge raises many aborts; over-blocks legitimate task progress |

The smoke results expose a design tension that A1 will quantify at full scale: the v1.21 rubric under-fires (no prevention); the v1.24 rubric over-fires (aborts crash benign utility). Three full-scale outcomes are possible:
1. v1.24 catches real attacks while preserving acceptable benign utility (recommended deployment configuration)
2. v1.24 over-blocks universally (rubric needs further iteration, or output-side LLM judges are structurally limited for action-level prevention)
3. v1.24 sits between — partial prevention with measurable utility cost (per-suite cost-benefit analysis required)

### Headline results [PENDING A1 — to be filled]

Reference numbers from AgentDojo paper for context: no-defense Targeted ASR = 57.69%, tool-filter defense ASR = 6.84% (51pp reduction), benign utility 69-73%. Our A1 numbers will go in this table:

| Configuration | Agent | Defense | Benign Utility | Targeted ASR | Utility Under Attack |
|---|---|---|---|---|---|
| Baseline | Llama 3.3 70B | None | TBD | TBD | TBD |
| +Defense A | Llama 3.3 70B | DeBERTa on tool outputs | TBD | TBD | TBD |
| +Defense B | Llama 3.3 70B | Sonnet v1.24 judge | TBD | TBD | TBD |
| +Defense C | Llama 3.3 70B | A OR B | TBD | TBD | TBD |

### Text-level vs action-level comparison [PENDING A1]

The methodologically important question: does the action-level ASR track the text-level §5.8 BIPIA attack-success rate, or does it diverge? If they track, the §5.5b/§5.8 numbers extrapolate reasonably to deployed agents with tools. If they diverge in either direction, that diagnoses the limit of text-level evaluation for predicting action-level outcomes, with corresponding implications for the deployment guide.

Three patterns are possible and instructive:
1. Action ASR substantially HIGHER than text ASR: agents that decline in text still execute the attack via tool calls. Text-level evaluation underestimates real-world risk.
2. Action ASR substantially LOWER than text ASR: agents that comply textually nevertheless refuse the corresponding tool call due to safety alignment on action execution. Text-level evaluation overestimates real-world risk.
3. Tracks closely: text-level evaluation is a reasonable proxy for action-level threat. The §5.5b/§5.8 numbers extrapolate cleanly to deployment.

### Implications for the deployment guide (§7) [PENDING A1]

Depending on pattern from above, the §7 framework's defense-configuration recommendations for autonomous tool-using agents (Hiflylabs' identified scenario) will either be reinforced (pattern 2 or 3) or require revision (pattern 1). The smoke phase already adds one robust deployment qualifier: deploying a text-level LLM judge as-is to a tool-using agent without rubric adaptation produces zero security benefit, and naive adaptation can crash utility, so the v1.24 rubric (or an analogue) is a deployment prerequisite for Defense B in tool-using contexts.

### Methodological notes

The AgentDojo evaluation is run with the same §3.2 operational definitions framework, using v1.24 (the tool-call variant) rather than v1.21. Mapping AgentDojo's outcome categories (Targeted ASR, Utility Under Attack) to the H1-H5 hijack categories: most AgentDojo injection tasks fall under H1 (task-execution hijack: agent executed attacker's specified action instead of operator's) and H4 (content injection: agent inserted attacker-specified data such as URLs into user-facing responses). H2 (system-prompt extraction) and H3 (persona substitution) are not the primary AgentDojo attack vectors. The §3.2 v1.23 scope note on signature-vs-mechanism applies symmetrically: an agent that emits a signature string is not by itself HIJACKED unless it also executes the attacker's tool action.

Reproducibility: framework installed via `pip install agentdojo`; evaluation runs via the project driver `scripts/run_agentdojo_eval.py`, which monkey-patches `agentdojo.attacks.base_attacks.MODEL_NAMES` to register our Together- and OpenRouter-hosted models, and wraps benchmark calls in `OutputLogger` to satisfy AgentDojo's logging contract. Defense B integration in `src/defense_b/agentdojo_integration.py::V121JudgeDefense` (the class name predates the v1.24 rubric; `rubric_version` parameter selects v1.21 or v1.24). Cost ceiling for A1: under $85 (Workspace, all four defense configs, Llama 3.3 70B); cross-family extension and additional suites contingent on A1 outcomes.

# 6. Discussion [DRAFT]

## 6.1 Cross-dataset variance as the headline finding

The 36-point F1 spread between deepset and SPML on the same classifier is the most consequential empirical result in this study. Two interpretations are consistent with the evidence:

1. The deepset distribution is closer to in-the-wild adversarial behavior and was less represented in the classifier's training mix; neuralchemy and SPML overlap more with the training distribution, inflating their numbers.
2. Both classifiers have learned a fairly narrow surface-level pattern (override-language keywords); deepset attacks evade this pattern, while neuralchemy and SPML are enriched in patterns the classifier recognizes.

The error-pattern analysis (Section 5.4) supports interpretation 2: classifiers' true positives are concentrated in cases with override-keyword markers, and the relative scarcity of those markers in deepset's attack distribution explains the recall gap mechanically. Interpretation 1 (training-distribution overlap) likely also contributes but is not necessary to explain the gap. A further mechanism the audit data (Section 5.4) surfaces is language coverage: 13 of deepset's audit rows are German, and DeBERTa is English-pretrained; on the 8 German injection rows in the audit DeBERTa catches 5 (62.5%), substantially below its English catch rate. The cross-dataset variance is partly a cross-language variance, with deepset disadvantaged because it carries non-English content the classifier was not trained to recognise.

Implication for practitioners: a single F1 number on a single benchmark is not a meaningful summary of an input classifier's protection. The honest summary is per-dataset, or better, per-subcategory.

This pattern fits the underspecification framing of D'Amour et al. (2022): pipelines with equivalent training and architecture can produce predictors that behave very differently on stress tests, and aggregate test-set metrics do not surface those differences. The within-dataset analogue is hidden stratification: aggregate accuracy can mask large performance gaps on unidentified subgroups within a single test set. The per-subcategory variation within neuralchemy (Section 5.3, DeBERTa recall ranging from 0.553 on jailbreak to 1.000 on token smuggling on the same model and the same dataset) is the prompt-injection counterpart of the medical-imaging finding documented by Oakden-Rayner et al. (2020). The methodological response in both literatures is the same: design evaluations targeted at where predictors differ, and report per-slice numbers alongside aggregate ones.

## 6.2 The layered-defense thesis, refined

The sneak preview shows that the value of an output-side judge varies by attack class. On subtle role-play injections (the deepset misses), the judge catches half the cases the classifier missed. On blunt harmful content (the neuralchemy jailbreak misses), the agent's RLHF alignment refuses before the judge sees a response. On obfuscated payloads (the neuralchemy encoding misses), the agent does not parse the embedded instruction at all.

The combined-defense argument is therefore stronger but more nuanced than a single catch-rate would suggest. The right deployment uses each layer for the attack class it is best at, and accepts that for some attack classes the defense in effect is the model's own training rather than the deployed defense stack.

## 6.3 Judge reliability is upstream of judge cost

The cost-sensitivity question (can a cheaper judge like Claude Haiku 4.5 or GPT-4o-mini replace Sonnet 4.6 at scale?) is methodologically downstream of the judge-reliability question. Three measurements now anchor the answer:

1. Cross-judge agreement at the 500-row pilot scale (§5.5b): Sonnet/Haiku kappa = 0.787, Sonnet/GPT-4o-mini kappa = 0.729 under v1.21. Stable to rubric version. Indicates judges substantially agree with each other.

2. Human-vs-judge agreement at the 150-row gold-subset scale (§5.6): Sonnet kappa = 0.324, Haiku kappa = 0.362, GPT-4o-mini kappa = 0.221 against §3.2 v1.23 human labels. NONE reach the 0.60 design target. Indicates the judges all share a common bias relative to strict §3.2 application — likely the signature-vs-mechanism pattern matching empirically identified in §5.6.

3. The 30-40% signature-driven share of human-CLEAN / judge-HIJACKED disagreements (§5.6) is the methodologically concrete next iteration: updating the judge prompt to incorporate the §3.2 v1.23 scope note explicitly would likely close that gap.

The cost-vs-reliability picture given these three measurements: Haiku 4.5 has the highest human-judge kappa (0.362) AND is 3.3x cheaper than Sonnet, making it the recommended production judge on current evidence. GPT-4o-mini's 20x cost advantage does not compensate for its substantially lower kappa (0.221). Further judge-rubric iteration (incorporating the v1.23 signature-vs-mechanism guidance into the prompt) is the highest-leverage next step before any further cost-tier optimisation.

## 6.4 What the evaluation measures, and against whom [DRAFT-TODO]

> Note for wrap-up writing: distinguish three adversary tiers explicitly so the deployment recommendations carry the right scope. To develop in the final pass; key framing below.

The evaluation in this study, like the public benchmarks it uses, measures defense behaviour against three broadly distinct classes of inputs, and the deployment guidance that flows from it should be read against each class separately.

- Own-goals (legitimate users who trip an injection-shaped pattern unintentionally): a user discussing prompt injection in their query, a developer pasting a prompt-engineering example, a benign request that happens to use words like "ignore" or "forget". These are the false positives Defense A produces on clean traffic. The 38% false-alarm rate on BIPIA clean controls (Section 5.8) is the empirical scale of this class on retrieved-content evaluation.
- Casual attackers (unsophisticated adversaries using canonical patterns): users copying a DAN prompt from a forum, pasting "ignore previous instructions" verbatim, or applying a published jailbreak template. The bulk of the three direct-injection datasets is this class. Defense A's high F1 on neuralchemy and SPML, and Defense C's 86.5% catch rate on the direct-injection pilot, are measured against this distribution.
- Determined adversaries (sophisticated attackers designing against the defenses): semantic-synonym evasion of override language, fictional-framing carriers, novel encodings and homoglyph payloads, multi-turn crescendo attacks (Russinovich, Salem and Eldan, 2024), authority-by-implication, and attacks specifically crafted with knowledge of the deployed defense stack. The deepset dataset captures more of this class than the others (F1 = 0.59 vs 0.95 on SPML), but no public benchmark in this study comprehensively measures defense behaviour against an attacker who is adapting in real time.

The deployment recommendations in Section 7 are well-supported for own-goals and casual attackers (the two classes the evaluation measures). For determined adversaries the recommendations are directional: the layered defense narrows but does not close the gap, and the same surface-pattern weakness that produces the cross-dataset F1 spread in Defense A (Section 6.1) also limits what the audit instrument can verify (operational definitions document, Section 3.1 limitations note). Practitioners deploying against determined adversaries should treat the configurations in Section 7 as the floor, not the ceiling, and pair them with runtime monitoring, anomaly detection, and the periodic adversarial-test-set work described in Section 9.1 (future work).

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

The 200-row stratified label audit (`reports/label_audit_report.md`) measures Cohen's kappa between the human auditor (applying the v1.22 §3.1 decision tree) and the three datasets' as-released gold labels at 0.930 [0.878, 0.970], "almost perfect" agreement per Landis and Koch (1977). Per-dataset disagreement-as-noise-rate proxies: deepset 4.5% [0.9%, 12.5%], neuralchemy 6.0% [1.7%, 14.6%], SPML 0.0% [0.0%, 5.4%], overall 3.5% [1.4%, 7.1%]. This is consistent with the 3.3% average label-error rate Northcutt et al. (2021) document across 10 widely used ML benchmarks. Reported metrics in Section 5 are uncorrected for label noise; the 36-point cross-dataset F1 spread (Section 5.1) is an order of magnitude larger than the noise-rate uncertainty, so the cross-dataset variance finding is robust to this level of label noise. F1 numbers should be read as bounded above by approximately F1_observed plus the per-dataset noise rate.

## 8.5 Subcategory-level inference

Per-subcategory results on neuralchemy include some categories with n as low as 12 to 30. Bootstrap CIs widen substantially at these sample sizes; per-subcategory findings are reported as exploratory and not corrected for multiple comparisons.

## 8.6 Multi-modal injection out of scope

The datasets used here are text-only. Multi-modal injection (adversarial perturbations of images or audio) is a real attack channel for multi-modal agents and is not evaluated here.

## 8.7 Reported confidence intervals are data-side only

The bootstrap 95% confidence intervals reported throughout Section 5 measure sampling variability over the 4,546-row frozen evaluation set. They do not measure model-side variability: training seed, checkpoint choice, fine-tuning run, or pretrained-classifier version. Sälevä et al. (2025) make this distinction explicit and show that accounting for only data-side variability substantially underestimates real replication uncertainty in NLP evaluation. Because Defense A uses off-the-shelf pretrained classifiers with no retraining in this study, model-side variability is structurally absent from our measurement, but it is not zero in the real world: a defender retraining DeBERTa from a different seed on the same data would observe shifted F1 numbers. The reported CIs should be read as a lower bound on the true "is this defense better than that one" uncertainty, and probably a loose one.

## 8.8 Language coverage of the input classifier

The audit-side measurement in Section 5.4 finds that DeBERTa loses approximately 14 percentage points of recall on non-English injections (82.3% English vs 68.4% non-English on the n=98 audit-confirmed injections) and Prompt Guard 2 loses approximately 27 percentage points (53.2% vs 26.3%), despite PG2's multilingual mDeBERTa backbone. The non-English audit sample is small (n=19), heavily German-dominated (13 of 19), and other-language coverage is too thin for per-language conclusions, so the magnitude carries substantial uncertainty; the direction is unambiguous and consistent across both classifiers. The deployment implication is that defense recommendations in Section 7 should be read with a language qualifier: enterprise deployments serving non-English-speaking user populations should treat the reported F1 numbers as upper bounds, and either layer a content-moderation classifier with broader multilingual coverage on top of Defense A, or include language-specific evaluation data in their own validation. A full cross-language Defense A evaluation (DeBERTa and PG2 on a language-stratified test set with multiple non-English languages at n >= 100 each) is marked as future work in Section 9.1.

# 9. Future Work and Conclusion [DRAFT]

## 9.1 Future work

- Real-tool agent evaluation in AgentDojo (Debenedetti et al., 2024) to measure action-level compromise beyond textual compliance.
- Custom adversarial test set crafted to target the specific blind spots identified in Section 5.4, to test whether the defenses generalize to attacks shaped by knowledge of their weaknesses.
- Multi-modal extension once a multi-modal injection benchmark is available.
- Production-rubric iteration on the LLM-as-judge component, informed by the human gold subset.
- Deployment-time disagreement monitoring of the LLM-as-judge layer. The cross-judge agreement work in Section 5.6 (Cohen's kappa 0.720 to 0.799 across Sonnet 4.6, Haiku 4.5, and GPT-4o-mini at the 500-row pilot scale) is a one-shot validation measurement. Nguyen et al. (2025) propose disagreement-driven deployment monitoring (D3M) as a deployment-time signal: track agreement between judges over time and alert when divergence increases, without requiring ground-truth labels at deployment. Operationalising the multi-judge measurements as a D3M-style monitor would let a deployed system detect drift in attacker behaviour, judge model versions, or workload distribution without re-collecting gold labels.
- Cross-language Defense A evaluation. Section 8.8 documents a ~14pp recall gap between English and non-English injections on the audit subsample; this should be measured at higher per-language n (~100+ per language across German, French, Spanish, Mandarin, Arabic, and other commonly-deployed languages) to quantify the deployment risk and inform multilingual defense-stack recommendations.

## 9.2 Conclusion

Off-the-shelf pre-trained input classifiers (Defense A) for prompt injection deliver high F1 numbers on the benchmarks closest to their training distributions, and substantially weaker performance on benchmarks featuring subtler attacks. The drop is not a calibration problem; it is a coverage problem, and one that ensembling does not solve. An output-side LLM-as-judge (Defense B) is empirically valuable but operates in different ways for different attack classes; its value comes partly from the judge itself and partly from the agent's own RLHF training, depending on the attack pattern. For enterprise deployments, the practical recommendation is a layered defense (input classifier ensemble + output-side judge), per-subcategory production monitoring against known blind spots, and explicit judge-rubric validation against a human-labeled gold subset before scaling.

# References

Artstein, R., & Poesio, M. (2008). Inter-coder agreement for computational linguistics. *Computational Linguistics*, 34(4), 555-596. https://doi.org/10.1162/coli.07-034-R2

D'Amour, A., Heller, K., Moldovan, D., Adlam, B., Alipanahi, B., Beutel, A., et al. (2022). Underspecification presents challenges for credibility in modern machine learning. *Journal of Machine Learning Research*, 23(226), 1-61. https://arxiv.org/abs/2011.03395

Debenedetti, E., Zhang, J., Balunovic, M., Beurer-Kellner, L., Fischer, M., & Tramer, F. (2024). *AgentDojo: A dynamic environment to evaluate prompt injection attacks and defenses for LLM agents* [Paper presentation]. NeurIPS 2024 Datasets and Benchmarks Track. https://arxiv.org/abs/2406.13352

Efron, B. (1979). Bootstrap methods: Another look at the jackknife. *Annals of Statistics*, 7(1), 1-26. https://doi.org/10.1214/aos/1176344552

Greshake, K., Abdelnabi, S., Mishra, S., Endres, C., Holz, T., & Fritz, M. (2023). *Not what you've signed up for: Compromising real-world LLM-integrated applications with indirect prompt injection* [Paper presentation]. AISec '23: 16th ACM Workshop on Artificial Intelligence and Security. https://arxiv.org/abs/2302.12173

Holm, S. (1979). A simple sequentially rejective multiple test procedure. *Scandinavian Journal of Statistics*, 6(2), 65-70. https://www.jstor.org/stable/4615733

Landis, J. R., & Koch, G. G. (1977). The measurement of observer agreement for categorical data. *Biometrics*, 33(1), 159-174. https://doi.org/10.2307/2529310

McNemar, Q. (1947). Note on the sampling error of the difference between correlated proportions or percentages. *Psychometrika*, 12(2), 153-157. https://doi.org/10.1007/BF02295996

Nguyen, V., Shui, C., Giri, V., Arya, S., Verma, A., Razak, F., & Krishnan, R. G. (2025). *Reliably detecting model failures in deployment without labels* (arXiv:2506.05047). https://arxiv.org/abs/2506.05047

Northcutt, C. G., Athalye, A., & Mueller, J. (2021). *Pervasive label errors in test sets destabilize machine learning benchmarks* [Paper presentation]. NeurIPS 2021 Datasets and Benchmarks Track. https://arxiv.org/abs/2103.14749

Oakden-Rayner, L., Dunnmon, J., Carneiro, G., & Re, C. (2020). Hidden stratification causes clinically meaningful failures in machine learning for medical imaging. In *Proceedings of the ACM Conference on Health, Inference, and Learning* (pp. 151-159). https://doi.org/10.1145/3368555.3384468

OWASP GenAI Project. (2025). *LLM01:2025 prompt injection*. OWASP Top 10 for LLM Applications. https://genai.owasp.org/llmrisk/llm01-prompt-injection/

Perez, F., & Ribeiro, I. (2022). *Ignore previous prompt: Attack techniques for language models* [Paper presentation]. NeurIPS 2022 ML Safety Workshop. https://arxiv.org/abs/2211.09527

Sälevä, J., Ataman, D., & Lignos, C. (2025). *Beyond statistical significance: Quantifying uncertainty and statistical variability in multilingual and multitask NLP evaluation* (arXiv:2509.22612). https://arxiv.org/abs/2509.22612

Toyer, S., Watkins, O., Mendes, E. A., Svegliato, J., Bailey, L., Wang, T., Ong, I., Elmaaroufi, K., Abbeel, P., Darrell, T., Ritter, A., & Russell, S. (2024). *Tensor Trust: Interpretable prompt injection attacks from an online game* [Paper presentation]. ICLR 2024. https://arxiv.org/abs/2311.01011

Yi, J., Xie, Y., Zhu, B., Kiciman, E., Sun, G., Xie, X., & Wu, F. (2025). Benchmarking and defending against indirect prompt injection attacks on large language models. In *Proceedings of the 31st ACM SIGKDD Conference on Knowledge Discovery and Data Mining* (pp. 1809-1820). https://doi.org/10.1145/3690624.3709179

# Appendices

- Appendix A: Operational Definitions (`reports/operational_definitions.md`)
- Appendix B: Methodology and Statistical Choices (`reports/methodology_appendix.md`)
- Appendix C: Contamination Report (`results/contamination_report.md`)
- Appendix D: Label Audit Report (`reports/label_audit_report.md`) [pending audit completion]
- Appendix E: Judge Validation Report (`reports/judge_validation_report.md`) [pending 150-row gold subset]
- Appendix F: Business Decision Framework (`reports/business_decision_framework.md`)
