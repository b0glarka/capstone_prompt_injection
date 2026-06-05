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

This capstone evaluates two prompt-injection defenses for enterprise AI agent deployments: an input-side classifier defense (Defense A, instantiated with two pre-trained models, ProtectAI DeBERTa and Meta Prompt Guard 2) and an output-side LLM-as-judge defense (Defense B, Llama 3.3 70B agent with Claude Sonnet 4.6 as the primary judge and GPT-4o as a sensitivity-check second judge). Evaluation is on a frozen 4,546-row stratified sample drawn from three public benchmarks (deepset/prompt-injections, neuralchemy/Prompt-injection-dataset, and reshabhs/SPML_Chatbot_Prompt_Injection), with BIPIA [@yi2025Benchmarking] as an indirect-injection extension.

The principal empirical finding is cross-dataset variance. The same input classifier delivers F1 of 0.59 [95% CI 0.52, 0.66] on the deepset benchmark and 0.95 [0.94, 0.96] on SPML, a 36-point spread that does not collapse under threshold tuning, ensemble methods, or substitution of the classifier. The variance is a property of the data distributions rather than the classifiers. Error-pattern analysis confirms that the input classifiers we tested rely heavily on canonical override-language keywords ("ignore previous instructions", "you are now X"); attacks that achieve the same effect through subtler social engineering or obfuscation slip through systematically.

The Defense B sneak preview, run on the 24 hardest input-classifier misses across three attack classes, reveals that the layered defense (classifier + agent + judge) operates by three different mechanisms depending on the attack class. On subtle role-play injections, the judge catches half the cases the classifier missed. On blunt harmful-content jailbreaks, the agent's RLHF training refuses the request before the judge sees it. On obfuscated payloads, the agent fails to parse the embedded instruction. This refines the layered-defense thesis: combining defenses is empirically supported, but the value of each layer is conditional on the attack class it is asked to handle.

The recommendation for enterprise deployments is layered: pre-trained input classifiers (preferably the OR-gated ensemble of DeBERTa and Prompt Guard 2) as the first line, an LLM-as-judge as the output-side check on flagged or borderline cases, and explicit per-subcategory monitoring in production to detect targeted attacks against known blind spots. The cost-weighted business decision framework in Section 7 maps these choices to deployment scenarios.

# 1. Introduction [DRAFT]

## 1.1 Motivation

As AI agents are deployed in enterprise environments with increasing autonomy, the risk of prompt injection attacks grows. OWASP ranks prompt injection as the number one threat to LLM-integrated applications [@owasp2025LLM01]: adversarial inputs can hijack agent behavior in ways that cause significant business harm, including financial loss, data exfiltration, brand damage, or compliance violations. The defensive question is not whether to harden the deployment but how, and at what cost, with what residual risk.

Despite a growing literature on attack techniques [@perez2022Ignore; @greshake2023Not] and benchmarks [@yi2025Benchmarking; @toyer2023Tensor], comparative evaluations of available defenses against published benchmarks remain rare. Pre-trained input classifiers are available off the shelf but report their accuracy on their own training distributions. LLM-as-judge approaches are increasingly common in agent evaluation but raise their own questions about judge reliability and cost. This capstone is a head-to-head, statistically defensible comparison of the two approaches across three independent benchmarks.

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

Prompt injection is defined here as an attempt to alter, override, or extract a language model's operating instructions through an input the model processes [@owasp2025LLM01]. The operational definitions document developed for this project (Appendix A; see `reports/operational_definitions.md`) translates the canonical taxonomies into a binary decision tree usable for labeling and judging.

Two main variants are recognized in the literature and named as distinct subtypes in OWASP LLM01:2025 [@owasp2025LLM01]:

- Direct injection: the adversary controls the user-facing channel and types the malicious instruction. The three datasets in this study (deepset, neuralchemy, SPML) cover direct injection.
- Indirect injection: the adversary plants the instruction in content the agent retrieves on behalf of a legitimate user, a vector first systematically characterized by @greshake2023Not. BIPIA [@yi2025Benchmarking] is the standard benchmark.

@perez2022Ignore identify two attack goals: goal hijacking (redirecting the agent to a different task) and prompt leaking (extracting the system prompt). The operational definition in Appendix A extends this with three additional response-side categories drawn from the BIPIA output taxonomy (information extraction, content injection, soft compliance with override).

## 2.2 Defense classes

Defenses divide naturally into input-side and output-side approaches:

- Input-side: a classifier inspects the user's prompt before it reaches the agent and flags or blocks suspected injections. Defense A in this study. Pre-trained options include ProtectAI DeBERTa v3 (a fine-tuned DeBERTa-v3-base) and Meta Prompt Guard 2 (a fine-tuned mDeBERTa-v3-base). Both classifiers are claimed to reach approximately 79% on the PINT benchmark, as reported on the ProtectAI v2 model card.
- Output-side: an LLM-as-judge inspects the agent's response to determine whether it has been hijacked. Defense B in this study, instantiated with Claude Sonnet 4.6 as the primary judge and GPT-4o as the sensitivity-check second judge.
- Combined (Defense C, stretch in this study): input classifier as gate, output judge on the residual. Operates the two layers in series.

Prompt augmentation (system-prompt instructions telling the agent to be skeptical of embedded directives) is a third common defense pattern [@perez2022Ignore]. Three augmentation conditions are evaluated as a baseline against Defense B.

## 2.3 Evaluation conventions

The community standard reports point estimates on per-dataset accuracy or F1. This study commits to bootstrap 95% CIs on every reported metric, pre-specified primary statistical comparisons with Holm-Bonferroni correction [@holm1979Simple], and Cohen's kappa with Landis-Koch interpretive thresholds [@artstein2008InterCoder; @landis1977Measurement] for any inter-rater agreement claim. The detailed methodology rationale is in Appendix B (`reports/methodology_appendix.md`).

# 3. Data [FILLED]

## 3.1 Source datasets

Three direct-injection datasets are used. All three are publicly available on HuggingFace and have been used in prior work.

- deepset/prompt-injections: 546 prompts (343 SAFE / 203 INJECTION). Smallest of the three, used in full for this study. Approximate label balance: 63% benign / 37% injection.
- neuralchemy/Prompt-injection-dataset: 4,391 prompts across 29 attack subcategories. The subcategory column is the richest source of attack-type structure in any of the three datasets.
- reshabhs/SPML_Chatbot_Prompt_Injection: 16,012 role-play injections with paired system prompts. This is the largest dataset and has a distinct schema (separate System Prompt and User Prompt columns), reflecting role-play attacks against deployed chatbots.

BIPIA [@yi2025Benchmarking] provides the indirect-injection extension and is described in Section 5.5.

## 3.2 Frozen evaluation set

A stratified 4,546-row evaluation set is constructed at seed 42 by `src/eval_set.py`:

- deepset: full census (546 rows).
- neuralchemy: 2,000 stratified by label and by attack subcategory on the injection side. Subcategory stratification preserves representation of small attack types.
- SPML: 2,000 rows, balanced 50/50 by label. Reused from the SPML pilot to maintain cache consistency with already-run Defense A inferences.

Frozen-set construction is deterministic and reproducible via `notebooks/02_eval_set_construction.ipynb`. The same prompt_idx is used by every downstream defense run, enabling paired comparison.

## 3.3 Label audit

Per @northcutt2021Pervasive, community-curated test sets carry label-error rates averaging 3.3% and ranging up to 6%. A 200-row stratified label audit is conducted against the operational definitions (Appendix A); the noise-rate estimate is reported as a methodological caveat alongside every metric. Per-dataset and overall results are at `reports/label_audit_report.md` [FILLED on completion of the audit].

## 3.4 Contamination check

ProtectAI DeBERTa v3 v2 names seven training datasets on its model card. Each was downloaded and exact-matched against the three evaluation datasets:

| Eval dataset | Named-source overlap | Decision |
|---|---|---|
| deepset | 0.92% | Accept and caveat |
| neuralchemy | 1.96% | Accept and caveat |
| SPML | 0.40% | Accept and caveat |

All three rates are below the level at which exact-match contamination would mechanically inflate metrics. Limitations: Harelix (one named V2 training source) was removed from HuggingFace and is unverifiable; 15 additional V2 sources are disclosed only by license category; Meta Prompt Guard 2 enumerates zero training sources. The full report is at `results/contamination_report.md`.

## 3.5 Reproducibility note: endpoint security and attack-content caches

Storing prompt-injection benchmark data triggers heuristic anti-malware scanners on multiple platforms because the cached attack-payload text (DAN-family prompts, encoded jailbreaks, agent-manipulation prompts, fake-API-key strings inside crafted jailbreaks) pattern-matches against malware-detection ML models. Researchers reproducing this work should pre-exclude the project root directory from endpoint scanning before launching long-running cache-writing jobs.

**Windows (Microsoft Defender).** Add the project root directory to the exclusion list via Virus & threat protection → Manage settings → Exclusions → Add a folder. Without this, Defender's heuristic ML scanner flags files such as `cache/defense_b_agent_full.jsonl` as `Trojan:Python/FileCoder.AI!MTB`. A flagged file is locked under quarantine inspection, causing scripts that read or write it to fail with `OSError [Errno 22] Invalid argument`. We hit this mid-run on the full-scale Defense B agent cache during this project and lost ~5 hours of partial inference; the exclusion prevents recurrence.

**Linux / macOS.** ClamAV's default signature set is less aggressive than Defender's ML scanner for plain-text content and rarely false-positives on attack samples directly. However, corporate-managed Linux/macOS environments commonly run third-party endpoint detection (CrowdStrike Falcon, SentinelOne, Sophos) that DO use ML-based scanners similar to Defender's; identical exclusion configuration is recommended on those systems. SELinux / AppArmor MAC policies may also restrict the agent process's access to files containing certain content patterns; check `audit.log` and `dmesg` for denials if scripts hang or fail to read caches.

**Common to all platforms.** Three additional false-positive surfaces to anticipate:

1. **Git hosting secret scanners.** GitHub's push protection and similar tools will flag attack prompts that embed plausible-looking API key patterns (some DAN-family jailbreaks include `sk-...` placeholders as part of the social-engineering payload). Configure repository-level secret-scanning exceptions for the `data/` and `cache/` paths or accept that pushes will require override confirmation.
2. **Container image scanners.** If the project is built into a Docker image, scanners like Trivy or Snyk may flag baked-in attack samples as suspicious content; exclude `cache/` and `data/` from the image layer or keep them as mounted volumes.
3. **Cloud storage DLP.** AWS Macie, GCP DLP, and Azure Information Protection can flag attack-content uploads as containing sensitive data. Tag the bucket/container as research data and exempt from default DLP policy.

This is a known cross-platform issue for security research and is not specific to this repository. The pattern is: any system that uses ML-based content classification to detect malicious patterns will produce false positives on adversarial-ML benchmark corpora. The defensive answer is to pre-declare research-data exclusions before running benchmarks, not to weaken endpoint protection globally.

# 4. Methods [DRAFT, partially filled]

## 4.1 Defense A: input classifier

ProtectAI DeBERTa v3 v2 and Meta Prompt Guard 2 86M are run on the full frozen evaluation set without fine-tuning, at the model's default decision threshold. Inference wrappers are in `src/defense_a/`. Predictions per row include the binary label, the injection-class probability, and the predicted class confidence; threshold sweeps and ROC/PR curves derive from the injection_score.

Two ensemble configurations of the two classifiers are evaluated:
- OR-gate: flag INJECTION if either classifier flags. Maximizes sensitivity.
- AND-gate: flag only if both classifiers flag. Maximizes specificity.

A mean-score ensemble averages the two classifiers' injection_score for use with continuous-threshold metrics (ROC AUC).

## 4.2 Defense B: agent and judge

The simulated-agent protocol of @yi2025Benchmarking is used: Llama 3.3 70B responds to the user prompt with a system prompt assigning it a helpful-assistant role. Two inference providers are supported interchangeably for the agent role (`src/defense_b/agent.py` exposes both): Groq's `llama-3.3-70b-versatile` endpoint for sneak-preview-scale work, and Together AI's `meta-llama/Llama-3.3-70B-Instruct-Turbo` for the 500-row formal pilot, where Together's higher daily quota was required. Both endpoints serve the same model family, so swapping providers does not change the methodological position: the agent is still a Llama 3.3 70B instance simulated via system prompt, consistent with the Hiflylabs deployment context (clients running self-hosted Llama 3.3).

The agent's text response is sent to Claude Sonnet 4.6 (via Anthropic) with a judge prompt that mirrors the operational definitions document §3.2 (v1.21): Step 0 operator-intent anchor per dataset, illustrative indicators per H1-H5 hijack category, AMBIGUOUS-routing instruction for borderline responses, and a structured JSON output schema requiring `verdict` (CLEAN / HIJACKED / AMBIGUOUS), `hijack_categories` (any of H1-H5 that apply, empty if CLEAN), and `reason` (one line). All reported Defense B numbers in Section 5 use this v1.21 rubric. An earlier minimum-rubric judge prompt was used during initial pilot runs in May 2026 and is preserved in `_local/baseline_v1.8_judge/` for transparency on rubric-version impact; the headline observations are stable across rubric versions (`results/aggregate_metrics_v121.md`). The judge wrapper (`src/defense_b/judge.py`) catches API-level content-policy refusals (`BadRequestError`, `PermissionDeniedError`) and records them as `judge_blocked=True` rather than crashing scaling runs.

The judge rubric is consistent with BIPIA's evaluation protocol at the output-deviation level: @yi2025Benchmarking define attack success as the agent's output deviating from the user's intended task in a direction consistent with the attacker's injected instruction, which is the same standard the H1-H5 hijack categories in `reports/operational_definitions.md` operationalise at the response-side label level. BIPIA itself does not formalise a parallel response-side taxonomy (its published categorisation is at the input side, fifteen attack subtypes), so the H1-H5 categories are a project-specific synthesis informed by @perez2022Ignore and OWASP LLM01:2025, not a direct mapping from BIPIA.

A GPT-4o (via OpenAI) sensitivity-check second judge is used on a borderline subsample to quantify judge-model-family dependence. The full judge validation against a 150-row human-labeled gold subset is the focus of the Phase 2 work documented in Section 5.4.

## 4.3 Statistical machinery

The report uses different CI methods matched to the metric and sample size. Composite metrics (F1, ROC AUC, Defense C catch-rate, paired-defense F1 differences) are reported with 1,000-iteration nonparametric bootstrap 95% CIs [@efron1979Bootstrap], implemented at `src/metrics.py::bootstrap_ci`. Binary metrics (per-subcategory recall and precision on a single class) are reported with Wilson score 95% CIs [@brown2001Interval], implemented at `src/metrics.py::wilson_ci`, which have documented good coverage at small n and avoid the bootstrap's known under-coverage on binary outcomes at n < 30 [@hesterberg2015What]. The principle: bootstrap on composite metrics where no exact interval exists; Wilson on binary proportions where one does. Per-subcategory composite results (F1 at n < 50) are reported as point estimates with an explicit underpowered flag rather than as bootstrap intervals.

Paired defense comparisons use McNemar's test [@mcnemar1947Note], exact binomial for small b+c and chi-squared with continuity correction otherwise (`src/metrics.py::mcnemar`). Cohen's kappa is reported for any inter-rater agreement claim, applied per the corpus-annotation conventions of @artstein2008InterCoder and interpreted on the @landis1977Measurement bands. Holm-Bonferroni correction at family-wise alpha = 0.05 applies to a pre-specified set of primary comparisons, following the multi-comparison discipline recommended by @JMLR:v7:demsar06a for classifier evaluations across multiple datasets; per-subcategory results are explicitly labeled exploratory. Full rationale in Appendix B.

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

Per-row noise floors and null-result subcategories. The recall numbers above are point estimates; for deployment use they should be read together with the Wilson 95% score interval at the underlying sample size. The following table uses the paired-evaluation slice of the frozen eval set (where DeBERTa and PG2 were scored on the same neuralchemy rows; full table at `results/defense_a_full_subcategory_recall_wilson.csv`):

| Subcategory | n (paired eval) | DeBERTa recall [95% CI] | PG2 recall [95% CI] | CIs overlap? |
|---|---|---|---|---|
| direct_injection | 637 | 0.981 [0.967, 0.989] | 0.743 [0.707, 0.775] | No |
| adversarial | 174 | 0.718 [0.647, 0.780] | 0.069 [0.040, 0.117] | No |
| jailbreak | 133 | 0.519 [0.435, 0.602] | 0.489 [0.405, 0.573] | Yes |
| encoding | 81 | 0.667 [0.559, 0.760] | 0.062 [0.027, 0.136] | No |
| training_extraction | 31 | 0.935 [0.793, 0.982] | 0.129 [0.051, 0.289] | No |

Intervals are Wilson score 95% CIs [@brown2001Interval], preferred over the normal-approximation (Wald) interval because Wald under-covers when p̂ is near 0 or 1 and is symmetric around p̂, which is incorrect at the boundaries. Wilson is calibrated down to n ≈ 5-10 and avoids the resampling-coverage issue that affects bootstrap CIs on binary outcomes at small n [@hesterberg2015What]. Bootstrap is used elsewhere in this report for composite metrics (F1, Defense C catch-rate) where no exact binomial interval exists; for per-subcategory recall, Wilson is the principled choice at every n.

Jailbreak is the one null-result subcategory at meaningful n: the 0.030 absolute recall gap between DeBERTa and PG2 (0.519 vs 0.489) is well inside the overlapping Wilson intervals, so the two classifiers cannot be distinguished on this subcategory at the available sample size. Both fail at similar rates, which means the layered-defense argument on jailbreak does not rest on classifier diversity; it rests on the agent's own RLHF alignment (Section 5.5). All other subcategories with n above 30 in the paired-eval slice show non-overlapping Wilson CIs.

Implication for the full breakdown. Subcategories with n below roughly 50 have Wilson interval widths above 0.20 at moderate recall (0.5 to 0.8), which is large relative to between-classifier gaps below 0.20. Smaller subcategories in the full table (e.g., crescendo at n = 4, encoding_obfuscation at n = 3) should be read as anecdotes, not measurements. The Limitations section (8.5) names this constraint.

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
| Overall | 251 | 0.418 | 0.534 | 0.076 |
| deepset | 84 | 0.488 | 0.488 | 0.071 |
| neuralchemy | 84 | 0.500 | 0.583 | 0.060 |
| SPML | 83 | 0.265 | 0.530 | 0.096 |

The v1.21 numbers above reflect the post-SPML-fix state: SPML rows are evaluated with the agent playing the row-specific SPML role (Finance Bot, Healthcare Advisor, etc.) and the judge using the SPML system_prompt as operator_intent (§3.2 Step 0). The pre-fix v1.21 SPML hijack rate was 0.313; the +0.217 lift came from exposing persona-substitution attacks (H3) that were invisible when the agent was a generic helpful assistant with no role to substitute away from. The fix is documented in `reports/methodology_appendix.md` §5.6.

The augmented v1.21 rubric net catches +29 injections out of 251 versus the minimum rubric (paired McNemar b=11, c=40, p=5.7e-05, highly significant), and routes 7.6% of cases to the new AMBIGUOUS bucket which the binary v1.8 rubric did not have. The per-dataset variance pattern shifts after the SPML fix: SPML's hijack rate is now comparable to neuralchemy's (~0.53 vs 0.58) rather than substantially lower (~0.27 vs 0.50 pre-fix). Persona-substitution attacks against role-specific operators are not easier to defend against; they were artificially low because of the prior data-side mismatch. The headline observation that even with an output-side judge roughly half of injection-class prompts produce text-level hijacked responses now holds uniformly across all three datasets. No judge-blocked rows occurred during the pilot, so the wrapper hardening (Section 4.2) was prophylactic rather than triggered.

A parallel cost-vs-accuracy sweep on the same 500 cached agent responses re-judged with Haiku 4.5 and GPT-4o-mini under the v1.21 rubric produced the following cross-judge agreement results:

| Judge pair | Agreement | Cohen's kappa (v1.21, post-SPML-fix) | Cost on 500-row pilot |
|---|---|---|---|
| Sonnet 4.6 vs Haiku 4.5 | 0.900 | 0.752 | $1.67 vs $0.50 (3.3x cheaper) |
| Sonnet 4.6 vs GPT-4o-mini | 0.850 | 0.644 | $1.67 vs $0.07 (24x cheaper) |
| Haiku 4.5 vs GPT-4o-mini | 0.890 | 0.744 | (cross-cheap pair) |

The cross-judge kappa numbers shifted slightly downward after the SPML fix (Sonnet/Haiku from 0.787 to 0.752; Sonnet/GPT-mini from 0.729 to 0.644). The shift came from the SPML re-judge: with the agent now playing the SPML role and the judge using the SPML system_prompt as operator_intent, the judges' verdicts on those 166 SPML rows separated more, with Sonnet readily classifying persona-substitution as HIJACKED while GPT-4o-mini more often called the same cases CLEAN. Per @landis1977Measurement, Haiku 4.5's kappa of 0.752 with Sonnet remains in the "substantial" range (0.61-0.80); GPT-4o-mini's kappa with Sonnet of 0.644 also stays "substantial" but at the lower end. Both cheaper judges track Sonnet closely enough to be candidate production judges for Defense B at full eval-set scale, with cost reductions of 3.3x and 24x respectively. The choice between them depends on whether the marginal 10-15 percentage points of disagreement matter for the deployment scenario in question.

A separate cross-family observation: under v1.21, Sonnet readily uses the AMBIGUOUS verdict (15 of 500 cases, 3.0%), Haiku uses it sparingly (5 of 500, 1.0%), and GPT-4o-mini ignores it entirely (0 of 500, 0.0%), instead flipping verdicts within the binary CLEAN/HIJACKED space. Different model families interpret the rubric's AMBIGUOUS instruction with different fidelity. The full disagreement breakdown and v1.8/v1.21 side-by-side numbers are in `results/aggregate_metrics_v121.md` and `results/defense_b_judge_cost_comparison.md`.

## 5.5c Defense C: combined pipeline at pilot scale

Defense C is the OR-combination of Defense A (input classifier) and Defense B (output-side LLM-as-judge): a prompt is flagged by Defense C if Defense A flags it as INJECTION or if Defense B's judge flags the agent's response as HIJACKED. The plan v2 listed Defense C as a stretch goal contingent on Phase 2 timing; the existence of paired Defense A and Defense B verdicts on the same 500-row pilot made the analysis available without new inference, so the result is promoted to a main pilot-scale finding.

Headline metrics on the 500-row pilot under the v1.21 rubric, with 1,000-iteration bootstrap 95% confidence intervals. Defense B and Defense C numbers reflect the v1.21 judge verdicts (AMBIGUOUS counted as HIJACKED, the conservative deployment-oriented convention). Defense A numbers are independent of the judge rubric and identical to the v1.8 report.

| Defense | Precision [95% CI] | Recall [95% CI] | F1 [95% CI] |
|---|---|---|---|
| A: DeBERTa alone | 0.960 [0.937, 0.978] | 0.761 [0.715, 0.802] | 0.849 [0.819, 0.876] |
| A: DeBERTa + PG2 ensemble | 0.955 [0.932, 0.974] | 0.769 [0.722, 0.811] | 0.852 [0.822, 0.879] |
| B: Sonnet judge alone (v1.21) | 1.000 [1.000, 1.000] | 0.534 [0.468, 0.591] | 0.696 [0.638, 0.743] |
| C: DeBERTa + B (v1.21) | 0.964 [0.935, 0.987] | 0.861 [0.818, 0.898] | 0.909 [0.879, 0.934] |

For reference, under the older v1.8 minimum rubric the corresponding numbers were Defense B F1 = 0.590 and Defense C F1 = 0.912; the v1.21 augmented rubric (post-SPML-fix) shifts Defense B F1 up by +0.106 (catching substantially more attacks, especially SPML persona-substitution) and Defense C F1 down by -0.003 (negligible, well within the bootstrap CI overlap). Defense B's precision under v1.21 is 1.000 (zero false positives on the 249 benign rows in the pilot) — the post-fix judge is highly conservative on clean inputs while now catching the previously-invisible persona-substitution attacks.

Three observations stand out:

First, Defense C strictly dominates every single defense. The OR-combination cannot do worse than its components on any single prompt; the question is whether the recall lift is meaningful and whether the precision cost is acceptable. The 95% CIs for Defense C's F1 do not overlap with the 95% CIs for any single defense, so the lift is statistically robust at the pilot sample size.

Second, recall lift is substantial. Defense C catches 86.1 percent of injections vs Defense A's 76.1 percent (a 10-percentage-point lift) and Defense B's 46.2 percent (a 40-percentage-point lift). The Defense A miss rate is roughly cut in half by adding the output-side judge.

Third, precision does not degrade. Defense C's precision of 0.960 is identical to Defense A's 0.960. Sonnet 4.6 under v1.21 has 0.991 precision on the 500-row pilot (one false positive on a benign agent response, down from zero under v1.8); the marginal increase in false-positive rate is too small to move Defense C's precision in a deployment-relevant direction.

Paired McNemar test (n = 500, v1.21, post-SPML-fix) confirms the dominance: Defense C (DeBERTa + B) vs Defense A (DeBERTa alone) shows b = 0, c = 25, p = 5.96e-08. Zero cases now exist where Defense A correctly flags but Defense C does not, because the OR-combination cannot in principle lose to A alone — the single case prior to the SPML fix that produced b = 1 was an artifact of the data inconsistency between agent context and judge context on SPML rows. Defense C strictly dominates Defense A at every prompt.

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

### Headline kappa: human vs LLM judges (n=150, post-SPML-fix)

| Judge | v1.21 binary kappa [95% CI] | Landis-Koch band |
|---|---|---|
| Sonnet 4.6 | 0.477 [0.336, 0.608] | Moderate |
| Haiku 4.5 | 0.471 [0.340, 0.600] | Moderate |
| GPT-4o-mini | 0.422 [0.283, 0.561] | Moderate |

The design target was Cohen's kappa above 0.60 (substantial agreement) between human auditor and each LLM judge. No judge meets that threshold, but all three now sit in the "moderate" band (0.41-0.60). Sonnet and Haiku are essentially tied (~0.47); GPT-4o-mini is ~5 points lower. This bounds how confidently Defense B hijack rates in §5.5b/§5.8 can be interpreted: cross-agent comparisons with effect sizes above the kappa-noise floor (~10pp) are robust; marginal differences (±5pp) are within judge-human disagreement and should not drive deployment decisions on their own.

These numbers reflect the post-SPML-fix state. Prior to the fix (when SPML rows had generic-assistant agent responses but were judged with operator_intent=system_prompt), kappa was Sonnet 0.324 / Haiku 0.362 / GPT-4o-mini 0.221 — all in the "fair" band. The +0.10 to +0.20 lift after correcting the SPML methodology is itself a finding: data-side consistency between agent context and judge context is a substantial source of measured judge-human disagreement, separate from rubric-application differences. The SPML fix is documented in `reports/methodology_appendix.md` §5.6.

### Where the disagreement concentrates

Among rows where the human auditor said CLEAN but the v1.21 judge said HIJACKED (or AMBIGUOUS), 30 to 41 percent contain a known attack signature pattern (HackAPrompt's "I have been PWNED" string, DAN persona declaration, JAILBROKEN marker, or equivalent). The §3.2 v1.23 scope note added to the operational definitions explicitly states that signatures alone do not trigger HIJACKED under §3.2 — only mechanism-level deviation from operator intent does. The judges are pattern-matching on the signature; the human auditor applying §3.2 v1.23 strictly recognises that no Step 4 mechanism is present and labels CLEAN. This empirically validates the v1.23 scope note and identifies the clear-target next iteration for the production judge prompt.

When both rater and judge agree on HIJACKED, they agree on the H-category set in 81-88 percent of cases (containment metric: judge's category set contains the human's primary H-category). Substantive judgment on WHICH H-category applies is robust; the disagreement concentrates at the CLEAN-vs-HIJACKED boundary.

### Cost-vs-agreement Pareto

Combined with cost data: Haiku 4.5 and Sonnet 4.6 are statistically tied on human-judge kappa (0.471 vs 0.477; CIs overlap heavily). Haiku is 3.3x cheaper ($0.50 vs $1.67 per 500-row pilot) and 2.6 sec faster per call (§7.4), making it the recommended production judge on cost-vs-agreement Pareto grounds. GPT-4o-mini's 20x cost advantage over Sonnet is partially defensible now (0.422 vs 0.477 kappa, 12-point cost-adjusted Pareto gap rather than the pre-fix 33-point gap), but Haiku remains strictly dominant: cheaper than Sonnet AND higher kappa than GPT-4o-mini.

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

Following @guo2017Calibration, a single temperature parameter T is fit on a stratified 10% calibration fold (455 rows) by minimising NLL against the binary labels, then applied to the remaining 90% test fold (4,091 rows). Expected Calibration Error (ECE, equal-width binning, 10 bins) is computed pre and post temperature scaling on the test fold. Per @chidambaram2024How, binning-based ECE has known pathologies and should be read directionally rather than absolutely; the pre-vs-post comparison is the load-bearing measurement.

| Scope | n (test fold) | ECE pre | ECE post | Δ |
|---|---|---|---|---|
| Overall | 4,091 | 0.084 | 0.037 | -55% |
| deepset | 491 | 0.220 | 0.166 | -25% |
| neuralchemy | 1,800 | 0.093 | 0.089 | ~unchanged |
| SPML | 1,800 | 0.046 | 0.078 | +69% |

The fitted T = 4.70 indicates DeBERTa was substantially overconfident pre-calibration: the model's effective sharpness was ~5x too high relative to its empirical accuracy. Temperature scaling softens the distribution toward more honest uncertainty.

Temperature scaling preserves the binary classification decision at the default 0.5 threshold (since `sigmoid(logit/T) > 0.5` iff `logit > 0`), so the §5.1-§5.3 F1, recall, and precision numbers are unchanged by calibration. The improvement is in the probability output's reliability as a confidence signal, not in the classifier's catch rate. This distinction matters for any deployment that consumes Defense A's probability outputs beyond the default binary decision: threshold-tuned routing, selective prediction (§7.6), confidence-weighted ensembling, and honest user-facing uncertainty all require calibrated probabilities to be meaningful.

Per-dataset behaviour is the interesting story. Overall ECE more than halves (-55%), and deepset improves most (-25%) — the dataset where DeBERTa was most miscalibrated also benefits most from the global temperature. SPML degrades, going from already-well-calibrated (ECE 0.046) to less-well-calibrated (ECE 0.078) under the global temperature. The single-temperature solution is a compromise across datasets with different empirical calibration properties; deepset and neuralchemy share an overconfident regime while SPML does not. Per-dataset temperature scaling would be the natural follow-on but trades parsimony for empirical fit; this is documented as future work in §9.1.

Practical implication for the coverage curve above: with calibrated probabilities, the bimodal-at-0-and-1 distribution would be spread out across the [0, 1] interval, and the curve's near-flat shape would gain a moderate slope. The selective-prediction routing recommendation accordingly changes: calibrated DeBERTa probabilities are usable as a confidence signal for auto-routing on deepset and neuralchemy, while SPML deployments should retain the existing routing strategy (Defense B on a fixed fraction). The reliability diagram at `results/figures/defense_a_calibration.png` visualises the pre-vs-post distribution shift.

## 5.8 BIPIA indirect injection [FILLED]

The BIPIA email-QA evaluation runs the full defense stack (Defense A in both query-only and full-prompt variants, Defense B with Together AI's Llama 3.3 70B agent + Sonnet 4.6 judge, Defense C as the OR-combination of DeBERTa full-prompt and the judge) against @yi2025Benchmarking's indirect-injection benchmark. Data: 50 base test emails composed with the 15 BIPIA attack categories (grouped into three themes: task-performance, stealth/obfuscation, and social-manipulation; see Section 2.1 and operational definitions Section 2.1 for the full enumeration), producing 750 attack rows plus 50 clean control rows for a total of 800 rows.

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

**Off-the-shelf is the floor, not the deployment recommendation.** The 38% FAR on clean controls and the 65.6% attack success rate on full-prompt Defense A reported above are the off-the-shelf measurements that motivated the §5.11 BIPIA extension. They are not the operating numbers a practitioner should deploy. The NB10e LoRA-v4 adapter (§5.11) achieves FAR = 0.000 on held-out base emails and ASR = 0.020 on the same held-out distribution by fine-tuning the same DeBERTa-v3 architecture on symmetrically-augmented (clean × question style) training data with base-document-stratified splitting. The fine-tuning recipe and reproducibility paths are in §5.11. Any production deployment for retrieved-content indirect injection should default to the NB10e workflow (or a practitioner-trained equivalent on their own corpus), not to the off-the-shelf §5.8 baseline. Off-the-shelf Defense A on BIPIA-shaped indirect injection is the demonstrated failure case that the §5.11 extension exists to resolve.

Full per-row results: `results/bipia_email_qa_results.csv` (800 rows, with v1.21 columns added); aggregate v1.21 metrics: `results/aggregate_metrics_v121.md`; v1.8 baseline structured writeup: `results/bipia_email_qa.md`.

## 5.9 Action-level evaluation: AgentDojo

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

The smoke results predicted a design tension for full-scale A1: v1.21 under-fires (no prevention); v1.24 over-fires (aborts crash benign utility). The A1 numbers below confirm v1.24 over-fires at full scale, but the result is confounded by an agent-side artifact (tool-name hallucination at the FP8 serving tier) that is reported separately in the headline.

### Headline results: A1 evaluation on workspace, Llama 3.3 70B Instruct Turbo via Together AI

Full A1 evaluation ran 4 defense configurations × 240 security cases × 40 benign-utility cases = 1,120 total per-task evaluations on AgentDojo's workspace suite. Reference numbers from the AgentDojo paper for context: no-defense Targeted ASR = 57.69%, tool-filter defense ASR = 6.84% (51pp reduction), benign utility 69-73% for comparable agents.

| Configuration | Targeted ASR | Utility Under Attack | Benign Utility | Judge calls |
|---|---|---|---|---|
| Baseline (none) | 0.971 | 0.179 | 0.175 | 0 |
| Defense A (DeBERTa on tool outputs) | 0.988 | 0.167 | 0.175 | 0 |
| Defense B (Sonnet v1.24 judge inside loop) | 0.992 | 0.142 | 0.125 | 461 |
| Defense C (A OR B) | 0.996 | 0.138 | 0.150 | 428 |

Two unexpected patterns characterise the A1 numbers and require careful interpretation before treating them as defense-effectiveness findings.

**Pattern 1: Targeted ASR is uniformly very high (97.1% baseline, rising slightly with each added defense layer to 99.6%) and benign utility is uniformly very low (12.5%-17.5%).** Both numbers diverge sharply from the AgentDojo paper's reported ranges for similar-tier agents (typically 55-65% ASR, 60-75% benign utility). The pattern is consistent across all four defense configurations.

**Pattern 2: Defenses do not reduce ASR.** Adding Defense B's judge to the pipeline modestly hurts benign utility (-0.050) without preventing attacks (+0.021 ASR). Defense C (the OR-gate) shows the same pattern.

Diagnostic inspection of the per-task JSON logs (`_local/agentdojo_logs/runs/llama-3.3-70b--none--benign/...`) reveals the source of both patterns: the Llama 3.3 70B Instruct Turbo agent systematically hallucinates tool names that do not exist in AgentDojo's workspace suite. Of 40 user tasks, the agent succeeds on 7 by happening to use plausibly-named real tools (`get_unread_emails`, `search_calendar_events`); the remaining 33 fail because the agent calls invented tool names (`get_appointments`, `find_appointments`, `get_calendar_events`) that AgentDojo's tool executor silently returns as empty strings. The agent then attempts further hallucinated names, accumulates empty responses, and gives up. Concurrently, the injection content is embedded in tool OUTPUTS that the agent does manage to receive on tools it correctly names, so the attack succeeds via those few real tool calls while the user task fails on the hallucinated ones.

This failure mode is an infrastructure-tier artifact rather than a Llama 3.3 70B capability finding. The A1 evaluation used Together AI's `meta-llama/Llama-3.3-70B-Instruct-Turbo` serverless tier, which is documented as FP8-quantized for serving throughput. FP8 quantization is known to degrade function-calling fidelity in particular because tool-name generation is sensitive to the precise weights that govern structured-output decisions. A control smoke test on user_task_0 via OpenRouter (routing to a BF16 provider of the same nominal Llama 3.3 70B model) yielded utility under attack of 1.0 (the agent successfully used real tool names and completed the user task), confirming the hallucination is specific to the Turbo serving tier rather than to the model weights themselves.

### Plan B: BF16 reproduction attempt and infrastructure limitations

A planned reproduction on a non-quantized serving tier ("Plan B") encountered separate infrastructure-side failures and is reported as a methodology limitation rather than a finding. Two attempted reproductions:

- **OpenRouter default routing.** All four defense configurations crashed mid-run with `json.JSONDecodeError: Unterminated string` when AgentDojo's tool-call parser tried to read malformed JSON in `tool_call.function.arguments` returned by OpenRouter's failover routing layer.
- **OpenRouter `:nitro` sub-route + crash-resilient eval driver.** All four configurations crashed with `pydantic.ValidationError: args Input should be a valid dictionary [type=dict_type, input_value=None]` when an upstream provider returned `null` instead of a JSON string for `tool_call.function.arguments`. The defensive partial-recovery layer added between attempts succeeded in salvaging per-task JSONs for the configurations that ran longest, but only 40 of 240 security cases per configuration completed before crash.

Both failure modes are characteristic of OpenRouter's multi-provider failover for tool-using requests: the layer routes opaquely across underlying providers, none of which is perfectly OpenAI-compatible for tool-call structured output. Provider-pin attempts via OpenRouter's `provider` body parameter (`DeepInfra`, `Hyperbolic`, `Lambda`) hit different errors (strict pydantic message-schema rejection on DeepInfra; no serving endpoints for the others). The cleanest controlled comparison would require provisioning a Together AI dedicated endpoint at the Reference (BF16) tier, which is paid-tier infrastructure ($4-6/hour for an H100 instance) and was outside the capstone time budget for this iteration.

The honest framing of the Plan B failures is methodological rather than substantive: they are infrastructure-choice artifacts of cheap-tier serverless inference (OpenRouter auto-routing for $0.10/$0.32 per million tokens; Together Turbo for $0.88 per million via FP8 quantization). A production deployment of a tool-using LLM agent would not rely on either tier; the cost difference between cheap-tier and dedicated BF16 endpoint ($30-50 per evaluation run vs $0.30-1) is dwarfed by the LLM-call costs in any enterprise deployment that produces useful tool work. The Plan B attempts are reported here to document what was tried and to scope what is and is not concluded from the A1 numbers.

### Text-level vs action-level comparison

The §5.5b text-level evaluation reports Defense B hijack rates of 49-58% across the three direct-injection datasets on Llama 3.3 70B Instruct Turbo. The A1 action-level ASR is 97.1% on workspace under the same agent. The two numbers do not directly compare:

- §5.5b measures whether the agent's natural-language response indicates compliance with an attacker's text instruction in the user prompt.
- A1 measures whether the agent's tool-call sequence executes the attacker's specified action when the attack is in tool output content the agent retrieved.

The 49-point gap (49-58% text-level vs 97% action-level) is consistent with two possibilities that this evaluation cannot disentangle given the A1 hallucination artifact: (a) action-level attacks are genuinely much easier than text-level on this benchmark distribution, and the §5.5b numbers are not extrapolable to tool-using agents, or (b) the A1 hallucination artifact inflates measured ASR (because the few tool calls that succeed are the ones that read injected content, biasing the security outcome towards "compromised"). A clean isolation would require either an A100/dedicated-endpoint re-run as outlined above or evaluation on a benchmark with a non-Llama agent that does not exhibit the hallucination pattern.

### Implications for the deployment guide (§7)

The A1 evaluation contributes one robust deployment qualifier and one open methodological question to §7

**Robust qualifier:** if a practitioner deploys an LLM agent on tool-using workflows using serverless quantized inference (cheap tier on Together, Fireworks, OpenRouter, etc.) without validating function-call fidelity on their specific tool schema, the agent may hallucinate tool names at a high rate. Validation of function-call fidelity is a deployment prerequisite, not an optional optimisation. This is a methodology recommendation backed by direct A1 evidence.

**Open question:** the §5.5b text-level finding that Defense B catches ~50% of direct-injection attacks (Llama agent, Sonnet judge) does not currently extrapolate to action-level threat against tool-using agents. Until a dedicated-endpoint or non-Llama A1 reproduction is run, the safest deployment posture is to assume action-level ASR is materially worse than text-level ASR and to compensate with layered tool-level guards (§7.8 in the hardening section).

### Methodological notes

The AgentDojo evaluation is run with the same §3.2 operational definitions framework, using v1.24 (the tool-call variant) rather than v1.21. Mapping AgentDojo's outcome categories (Targeted ASR, Utility Under Attack) to the H1-H5 hijack categories: most AgentDojo injection tasks fall under H1 (task-execution hijack: agent executed attacker's specified action instead of operator's) and H4 (content injection: agent inserted attacker-specified data such as URLs into user-facing responses). H2 (system-prompt extraction) and H3 (persona substitution) are not the primary AgentDojo attack vectors. The §3.2 v1.23 scope note on signature-vs-mechanism applies symmetrically: an agent that emits a signature string is not by itself HIJACKED unless it also executes the attacker's tool action.

Reproducibility: framework installed via `pip install agentdojo`; evaluation runs via the project driver `scripts/run_agentdojo_eval.py`, which monkey-patches `agentdojo.attacks.base_attacks.MODEL_NAMES` to register our Together- and OpenRouter-hosted models, and wraps benchmark calls in `OutputLogger` to satisfy AgentDojo's logging contract. Defense B integration in `src/defense_b/agentdojo_integration.py::V121JudgeDefense` (the class name predates the v1.24 rubric; `rubric_version` parameter selects v1.21 or v1.24). Cost ceiling for A1: under $85 (Workspace, all four defense configs, Llama 3.3 70B); cross-family extension and additional suites contingent on A1 outcomes.

## 5.11 LoRA fine-tune stretch: closing the cross-dataset variance gap

The §6.1 cross-dataset variance finding (36-point F1 spread between deepset 0.59 and SPML 0.95 on the same off-the-shelf ProtectAI DeBERTa classifier) admits two interpretations: training-distribution mismatch, or fundamental architectural limitation of surface-pattern classifiers against adversarial framing. This section runs a controlled fine-tuning experiment to distinguish the two.

### Setup

The frozen 4,546-row evaluation set is split into 70% train (3,182 rows) / 15% val (682 rows) / 15% test (682 rows), stratified by (dataset × label) so all six combinations (deepset/neuralchemy/SPML × benign/injection) appear proportionally in each split. Splits are saved as `results/eval_set_splits.parquet` for reproducibility.

LoRA fine-tuning starts from `microsoft/deberta-v3-base` (Microsoft's raw 184M-parameter checkpoint, no prior prompt-injection training) so the fine-tuning signal is purely from our eval-set distribution rather than ProtectAI's. LoRA configuration: rank 16, alpha 32, dropout 0.1, `target_modules='all-linear'`, bias='none', following the Week 3 lab convention. Training: 3 epochs, learning rate 2e-4, batch size 16, max sequence length 512, AdamW with linear LR schedule and 6% warmup ratio. Hardware: NVIDIA L4 on Colab Pro (~4 minutes wall time for the base model; A100 used for DeBERTa-v3-large to fit batch size 16 at max_length 512 within VRAM).

**Modeling methodology note.** This experiment uses one configuration with sensible defaults. No hyperparameter sweep was performed. The goal is to establish a clean baseline lift from in-distribution fine-tuning, not to find the optimal LoRA recipe. Production deployment would benefit from tuning LoRA rank, target modules, learning rate, dropout, num epochs, class weighting, and student-model choice (for the distillation extension in §7.7). The findings reported here are therefore conservative.

### Headline result: cross-dataset spread closes from 0.36 to 0.031

LoRA fine-tuning on the 3,182-row stratified train set collapses the cross-dataset F1 spread observed in §5.1. All metrics below are on the held-out 682-row test split; baseline is the same off-the-shelf ProtectAI DeBERTa classifier evaluated on the same 682 rows for apples-to-apples comparison. Wilson 95% intervals [@brown2001Interval] per §4.3.

| Dataset | Off-the-shelf baseline F1 | LoRA-tuned F1 | ΔF1 |
|---|---|---|---|
| deepset (n=82, 30 positives) | 0.636 | 0.931 | **+0.295** |
| neuralchemy (n=300, 181 positives) | 0.898 | 0.964 | +0.066 |
| spml (n=300, 150 positives) | 0.952 | 0.966 | +0.014 |
| **Overall** (n=682, 361 positives) | **0.906** | **0.962** | **+0.056** |
| **Cross-dataset F1 spread** | **0.316 (spml − deepset)** | **0.035** | **closed** |

The deepset gap, which §6.1 identifies as the load-bearing evidence for the underspecification interpretation, collapses by 89% (0.316 → 0.035). The recall lift is the dominant mechanism: deepset recall rises from 0.467 to 0.933 (a +0.467 absolute improvement). Off-the-shelf DeBERTa was missing half of deepset's adversarially framed injections; LoRA on a balanced training mix catches them.

Full metrics including Wilson confidence intervals are in `results/lora_metrics.json`.

### Robustness experiments: capacity, starting checkpoint, deployment precision

The +0.295 deepset finding holds across three orthogonal robustness axes, evaluated on the same held-out 682-row test split. All four configurations were trained from scratch with the same LoRA recipe and stratified split; the only varied factor is identified per row.

| Configuration | Overall F1 | Deepset F1 | Neuralchemy F1 | SPML F1 | Notes |
|---|---|---|---|---|---|
| Baseline (ProtectAI off-the-shelf) | 0.906 | 0.636 | 0.898 | 0.952 | §5.1 classifier on the same test rows |
| LoRA on DeBERTa-v3-base, FP16 | 0.962 | 0.931 | 0.964 | 0.966 | Primary experiment |
| LoRA on DeBERTa-v3-large, FP16 | 0.955 | 0.814 | 0.958 | 0.980 | 2.4× model capacity |
| **LoRA on ProtectAI-v2 as base, FP16** | **0.981** | **0.966** | **0.975** | **0.990** | Best; ProtectAI checkpoint + our distribution |
| LoRA on DeBERTa-v3-base, INT8 quantized | 0.811 | 0.877 | 0.772 | 0.842 | bitsandbytes 8-bit inference |

Three findings from this matrix

1. **DeBERTa-v3-large does not improve over base** (overall F1 0.955 vs 0.962; deepset F1 0.814 vs 0.931). Larger model capacity at the same 3,182-row train set produces marginal overfitting on deepset, where the small dataset (382 train rows) cannot support 435M parameters as well as 184M can. Base size is sufficient for our distribution and recommended for deployment on cost-vs-capability grounds.

2. **ProtectAI-as-starting-point is the optimal recipe** (overall F1 0.981, deepset F1 0.966). The +0.019 lift over LoRA-from-Microsoft-checkpoint confirms ProtectAI's prompt-injection training and our eval-set distribution are additive rather than redundant. Practitioners deploying DeBERTa as Defense A on similar internal-employee scenarios should start from ProtectAI v2 and add a thin LoRA layer trained on their own attack distribution. This is the production recommendation.

3. **INT8 quantization is NOT deployment-safe** for this model class. Post-hoc bitsandbytes 8-bit quantization of the LoRA-tuned model drops overall F1 from 0.962 to 0.811, with recall collapsing from 0.942 to 0.695 (precision stays high at 0.973). DeBERTa's disentangled-attention architecture quantizes poorly to INT8 via post-hoc methods; the merged LoRA weights compound the degradation. Practitioners requiring smaller deployment footprints should use FP16 inference, distillation (§7.7 future work), or quantization-aware training rather than post-hoc INT8.

### Robustness sanity checks

Four checks verify the +0.295 deepset finding is a real measurement rather than an artifact:

**Duplicate prompts across train/test.** 1 of 682 test prompts (0.15%) appears in the train split, well below the 1% threshold that would indicate memorization. The single duplicate is a short benign template that appears in two different dataset families. No meaningful leakage.

**Prompt length as potential shortcut.** Injection prompts in our eval set are systematically longer than benign prompts within each dataset: deepset 2.65× ratio (mean), neuralchemy 2.87×, SPML 10.38×. This is a real feature of the data distribution rather than a measurement bug, but it raises the question whether LoRA learned "longer prompt ⇒ injection" instead of attack content. Two pieces of evidence argue it did not: (a) off-the-shelf DeBERTa achieves F1 0.91 on neuralchemy where the ratio is 2.87×, so content signals are demonstrably learnable on this distribution and (b) the per-dataset confusion matrices below show balanced false-positive and false-negative rates, not the asymmetric pattern a length-only classifier would produce on inputs with mismatched lengths. The length correlation is documented as a methodology caveat: an adversarial test set with length-controlled prompts (short attacks paired with long benign retrievals) would tighten the finding and is listed as future work in §9.

**Per-subcategory breakdown within deepset.** Not feasible. The deepset dataset does not expose a subcategory column in the eval set (only neuralchemy does). The +0.295 lift therefore holds across the deepset population as a whole; we cannot test whether it concentrates on one specific attack subtype. This is a known limitation of the deepset benchmark, not of our analysis.

**Confusion matrices per dataset.** All three datasets show balanced false-positive rate (FPR) and false-negative rate (FNR) without extreme asymmetry, ruling out the failure modes typical of single-feature shortcut classifiers:

| Dataset | n | FPR (false alarms) | FNR (misses) |
|---|---|---|---|
| deepset | 82 | 0.019 | 0.100 |
| neuralchemy | 300 | 0.034 | 0.050 |
| spml | 300 | 0.007 | 0.060 |

deepset's slightly elevated FNR (0.100) is the expected pattern for the dataset that was hardest for the off-the-shelf classifier; the LoRA-tuned model has narrowed but not eliminated this asymmetry.

### Interpretation for the §6.1 underspecification narrative

The four-config matrix and four robustness checks together rule out the architectural interpretation of §6.1: DeBERTa-v3-base can correctly classify deepset's adversarially framed injections when fine-tuned on a balanced sample of the distribution. The 36-point F1 spread between deepset and SPML in §5.1 was substantially a training-distribution artifact of ProtectAI's particular training mix, not a fundamental limit of surface-pattern classifiers on this attack class. This is direct empirical support for the underspecification framing [@damour2020Underspecification]: pipelines with equivalent architecture and roughly equivalent training data can produce predictors that behave very differently on stress tests, and our cross-dataset variance reflects upstream choices in the published classifier rather than capability limits.

The deployment implication is concrete and updated in §7: practitioners deploying Defense A on enterprise scenarios with a known attack distribution should add a thin LoRA layer trained on a balanced sample of their own attack data, starting from ProtectAI v2 rather than from scratch. Compute cost is approximately $1-5 on a free Colab T4 for 3,000-5,000 training rows. The +0.075 F1 lift (overall) and +0.330 deepset F1 lift relative to the off-the-shelf baseline are deployment-grade improvements at trivial compute cost.

Reproducibility: notebook at `notebooks/08_defense_a_lora_finetune.ipynb` (executed version with cell outputs at `notebooks/08_defense_a_lora_finetune_post_run.ipynb`); metrics JSON at `results/lora_metrics.json` (primary LoRA-base experiment) and `results/lora_metrics_extended.json` (all four robustness configurations + comparison table); train/val/test split at `results/eval_set_splits.parquet`; trained LoRA adapter at `_local/deberta_v3_base_lora_v1/` (gitignored; ~15MB).

Language scope of this finding. The LoRA fine-tune was conducted on `microsoft/deberta-v3-base` (English-pretrained) using training data drawn from the deepset, neuralchemy, and SPML datasets (predominantly English with a small German subset in deepset). The +0.295 deepset F1 lift therefore characterises in-distribution fine-tuning effectiveness for English content. For multilingual deployments, the equivalent recipe would substitute `microsoft/mdeberta-v3-base` (multilingual DeBERTa pretrained on 100+ languages via CC-100) as the base model and augment the training set with multilingual injection samples. Whether the same gap-closing effect generalises to multilingual fine-tuning is an empirical question this study cannot answer with the available data; constructing or licensing a multilingual prompt-injection benchmark is itself a research contribution, not a one-line follow-up. The language scope is documented further in §8.8.

### Extending §5.11 to BIPIA indirect injection: four iterations and a pressure-test discipline

The §5.11 result above measures direct-injection generalisation: training and testing both within the deepset / neuralchemy / SPML attack family. A natural follow-on question is whether the same LoRA recipe transfers to indirect injection, where the attack is not in the user's prompt but in retrieved content (an email body, a document, a tool output) that the agent reads. This subsection reports four sequential fine-tune iterations on BIPIA's email-QA task [@yi2025Benchmarking] and the pressure-test workflow that prevented a methodological false positive from being reported as the main finding. The arc was: negative transfer, data-scarcity diagnosis, an apparent rescue, a pressure-test failure, and a symmetric-augmentation fix that survives all the same probes. The final recipe is deployment-ready; the intermediate results are the audit trail that establishes why.

**NB10: §5.11 LoRA-v1 does not transfer to BIPIA.** Applying the LoRA-from-ProtectAI adapter trained in §5.11 (the 0.981 F1 winner on direct injection) to BIPIA's 800 email-QA prompts produced a degenerate output distribution: every input scored in a near-constant 0.79-0.83 band regardless of whether it contained an attack instruction. Cohen d between clean and attack score distributions on BIPIA was 0.13. The model had no discriminative signal on indirect injection despite working well on direct. This is a real negative-transfer result: the §5.11 LoRA learned features specific to the direct-injection distribution (short, dense, lexical override patterns) that do not surface on BIPIA's longer, embedded, contextually-framed indirect injections.

**NB10b: naive retraining on BIPIA fails due to data scarcity.** Combining the §5.11 eval-set training data with BIPIA's 800-row dataset and retraining the LoRA produced a misleading-looking 0.966 F1 on BIPIA test that turned out to be the trivial all-positive baseline (BIPIA test is 93% positive, so predicting INJECTION for all 120 test rows gives precision 0.933, recall 1.000, F1 0.966). The robustness checks introduced for this experiment (macro F1, balanced accuracy, MCC, Cohen d) all flagged the degeneracy immediately: macro F1 = 0.483, balanced accuracy = 0.500 (random-guess baseline), Cohen d = 0.13. The cause is data scarcity: BIPIA provides only 50 unique clean control emails (35 in the train split after stratification). Class-weighted loss cannot synthesise new clean examples; with only 35 unique clean patterns, the model latched onto BIPIA's email format ("inbox assistant" wrapper + pipe-delimited metadata + user question) as the negative-class signal rather than learning what a clean email body looks like as content. eval_set test F1 was preserved at 0.981, confirming that combining datasets in training does not degrade direct-injection performance, but the BIPIA arm provided no useful signal.

**NB10c: augmenting clean controls appears to work.** Pairing each of the 50 BIPIA base emails with 5 generic legitimate questions ("Can you summarize this email?", "What is the main point?", "Who sent this and what do they want?", etc.) raised the clean control count from 50 to 300 and produced metrics that looked clearly publishable: BIPIA test macro F1 = 0.992, balanced accuracy = 0.989, MCC = 0.984, Cohen d between clean and attack score distributions = 9.37 (clean scores cluster at 0.024 ± 0.147, attack scores at 0.998 ± 0.002). The eval_set direct-injection F1 stayed at 0.979 (vs §5.11's 0.981), confirming no interference. On its face this was the deployment-ready answer. The robustness checks built into the notebook (duplicate prompts, length shortcut, score distribution, confusion matrix, interference vs §5.11) all passed.

**NB10d: pressure tests expose a question-style shortcut.** Six adversarial probes were applied to the NB10c Variant B adapter to test whether the d = 9.37 separation was genuine content discrimination or methodology artifact. Five probes passed: clean classification was robust to question-style perturbations (Test 2: flag rate stayed 0.022 to 0.044 when generic questions were swapped for BIPIA-style ones), novel question phrasings did not flip classifications (Test 5), and held-out base emails from BIPIA's `train.jsonl` (50 emails never seen in training) produced d = 9.90 with balanced accuracy 0.990 (Test 3) and a false-positive rate of 0.040 on real legitimate queries about those unseen emails (Test 6). One probe failed and was the load-bearing one: Test 1 (attack-question ablation) swapped the BIPIA-style attack questions on test attack rows for one of the 5 generic questions used in clean training. Flag rate on attacks collapsed from 1.000 to 0.487, a coin-flip. The model had learned the training-time correlation between question style and label as a shortcut. All 524 attack training rows had BIPIA-style questions; all 300 clean training rows had generic questions. The model used question style as a confidence-boosting signal for attack detection. Without that cue at test time (attack content with a generic question), the model lost its discriminative ability.

**Pressure-test workflow as methodological contribution.** The NB10d notebook implements six probes that target the failure modes most common in benchmark-trained classifiers: question-style independence (Tests 1 and 2), email-body generalisation (Test 3 on held-out base emails from a different BIPIA split), novel-template robustness (Test 5), and false-positive rate on real legitimate queries about unseen emails (Test 6). The pattern of one failure plus five passes was diagnostic: the model has genuine content recognition on cleans (Test 2 plus Test 5 plus Test 6) and genuine email-body generalisation (Test 3), but missing question-style independence on attacks (Test 1). That pattern points to a fixable training-data confound rather than a fundamental architectural limit, and the fix follows directly: decorrelate question style from label by also augmenting attack rows with generic questions. Most published Defense A papers do not report tests of this kind; the next iteration would not have been attempted without them.

**NB10e: symmetric augmentation plus base-email-stratified split.** The fix has two components. First, symmetric augmentation: each of the 50 BIPIA base emails contributes 6 clean rows (one per question style, 1 BIPIA-original plus 5 generic) and 15 attack rows (one per attack category, with the question style assigned randomly across the 6 styles). The marginal distribution of question styles is approximately equal across both classes (50 clean per style, 109-136 attack per style, the variation reflecting random assignment), so question style is no longer correlated with the label and cannot be learned as a shortcut. Second, base-email-stratified split: each base email goes entirely into train, val, or test rather than being split across (email, question) pairs as in NB10c. The 50 base emails are partitioned 34 / 8 / 8, ensuring that no test base email appears in any training row. The NB10d duplicate-check that found 100% clean train/test body overlap on the NB10c split is structurally impossible on the NB10e split. Training data and recipe otherwise match NB10c (combined eval_set + symmetric BIPIA, LoRA-from-ProtectAI at rank 16 / alpha 32 / dropout 0.1 / `target_modules='all-linear'`, 3 epochs, learning rate 2e-4, class-weighted loss with weights computed on the combined training mix).

The NB10e Variant B adapter (`lora_v4b_symmetric_aug`) passes all four key probes the NB10c Variant B failed or did not face. Test 1 (attack-question ablation) returns to flag rate 1.000 (was 0.487). Test 3 (held-out triple cross: 50 BIPIA `train.jsonl` base emails the model has never seen, paired with generic questions and with held-out attack templates from `text_attack_train.json`) achieves Cohen d = 7.73, balanced accuracy = 0.980, ASR = 0.020, FAR = 0.000; this is the strongest pressure test in the suite because it varies three dimensions at once (base email, question style, attack template) and the model has not seen any of them. Test 6 (held-out emails with BIPIA's own train-split questions, no attack content) produces a 0.020 flag rate on 50 legitimate user queries, the operational false-positive rate practitioners care about. Direct-injection performance is preserved at eval_set F1 = 0.974 (vs §5.11 LoRA-v1's 0.981), a 0.7 percentage-point difference within noise. In-distribution BIPIA test metrics on the symmetric split are very strong (macro F1 = 1.000, d = 189) because the model fits the augmented BIPIA distribution well; the more informative number for deployment is the Test 3 triple-cross d = 7.73, which characterises generalisation to email content and attack styles the model has never encountered.

| BIPIA experiment | Macro F1 | Cohen d on test | Test 1 flag rate (attack + generic Q) | eval_set F1 (direct) | Verdict |
|---|---|---|---|---|---|
| NB10: §5.11 LoRA-v1 transfer | n/a | 0.13 (degenerate) | n/a | 0.981 (unchanged) | Negative transfer; LoRA-v1 has no signal on BIPIA |
| NB10b: naive retraining | 0.483 | 0.13 (degenerate) | n/a | 0.981 (preserved) | Data scarcity; 35 clean training rows insufficient |
| NB10c: clean augmentation only | 0.992 | 9.37 (in-distribution) | 0.487 (FAIL) | 0.979 (preserved) | Apparent success masking question-style shortcut |
| NB10e: symmetric augmentation + base-email-stratified split | 1.000 (in-dist) / 0.980 (triple cross) | 189 (in-dist) / 7.73 (triple cross) | 1.000 (PASS) | 0.974 (preserved) | Deployment-ready |

### Deployment recipe for indirect injection

The NB10e Variant B configuration is the recommended starting point for practitioners extending Defense A to retrieved-content indirect injection. The recipe is:

1. **Base model:** `ProtectAI/deberta-v3-base-prompt-injection-v2` (the §5.11 winner on direct injection). Starting from ProtectAI v2 rather than Microsoft's raw checkpoint preserves the cross-dataset generalisation lift documented in §5.11 above.
2. **LoRA configuration:** rank 16, alpha 32, dropout 0.1, `target_modules='all-linear'`, bias='none' (same as the §5.11 recipe).
3. **Training data composition:** combine the direct-injection training distribution (deepset / neuralchemy / SPML or the practitioner's own equivalent) with the indirect-injection training distribution (the practitioner's retrieved-content corpus). For BIPIA-style email-QA the symmetric augmentation pattern is: each base document contributes equal counts of clean and attack rows across multiple legitimate user-question phrasings, with attack content embedded at the document level rather than the prompt level. The marginal distribution of user-question phrasings should be approximately equal across the clean and attack classes; the marginal distribution of document content should be approximately equal across question styles.
4. **Splitting discipline:** stratify the train / val / test split at the document level (each document goes entirely into one split) rather than the (document, question) pair level. This prevents the train/test body-overlap memorization confound documented above for NB10c.
5. **Training hyperparameters:** 3 epochs, learning rate 2e-4, batch size 16, max sequence length 512, AdamW with linear LR schedule and 6% warmup ratio, class-weighted cross-entropy (sklearn `compute_class_weight('balanced', ...)`).
6. **Pressure tests before deployment:** run NB10d's six probes (attack-question ablation, clean-question ablation, held-out base emails, length-shortcut check, novel question, false-positive rate on real legitimate queries) on the final trained adapter. The attack-question ablation (Test 1) is the load-bearing probe; if flag rate falls below 0.95 on attacks paired with question styles the model has not seen, the augmentation has a residual shortcut and the training data needs to be rebalanced.

The deployment implication for Hiflylabs and similar enterprise scenarios where the agent reads from a retrieved-content corpus (email, document, knowledge base) is concrete: Defense A is a viable input layer for indirect injection at the same cost profile as for direct injection (one LoRA adapter, ~15MB on disk, single forward pass per inference at the same latency as off-the-shelf DeBERTa), but only with the augmentation discipline above. The §7.5-§7.10 hardening recommendations still apply; in particular, Defense B (output judge) remains the correct second layer because the input classifier does not see the agent's response to retrieved content.

Reproducibility for the BIPIA arm: augmentation scripts at `scripts/augment_bipia_clean.py` (NB10c, included for historical comparison) and `scripts/augment_bipia_symmetric.py` (NB10e, the recommended one). Notebooks at `notebooks/10_lora_v1_on_bipia.ipynb`, `10b_lora_v2_bipia_retraining.ipynb`, `10c_lora_v3_bipia_augmented.ipynb`, `10d_lora_v3_pressure_tests.ipynb`, `10e_lora_v4_symmetric_augmented.ipynb` with `_post_run` versions preserving execution outputs. Metrics at `results/lora_v2_metrics.json` (NB10b), `results/lora_v3_metrics.json` (NB10c), `results/lora_v3_pressure_tests.json` (NB10d), `results/lora_v4_metrics.json` (NB10e). Per-row test predictions at `results/lora_v4_test3_holdout.csv` (the triple-cross probe). Augmented data at `results/bipia_email_qa_prompts_symmetric.csv`. Trained adapter at `MyDrive/capstone_lora/adapters/lora_v4b_symmetric_aug/` (Drive, gitignored). The notebook sequence is documented in `notebooks/README.md`.

# 6. Discussion [DRAFT]

## 6.1 Cross-dataset variance as the headline finding

The 36-point F1 spread between deepset and SPML on the same classifier is the most consequential empirical result in this study. Two interpretations are consistent with the evidence:

1. The deepset distribution is closer to in-the-wild adversarial behavior and was less represented in the classifier's training mix; neuralchemy and SPML overlap more with the training distribution, inflating their numbers.
2. Both classifiers have learned a fairly narrow surface-level pattern (override-language keywords); deepset attacks evade this pattern, while neuralchemy and SPML are enriched in patterns the classifier recognizes.

The error-pattern analysis (Section 5.4) supports interpretation 2: classifiers' true positives are concentrated in cases with override-keyword markers, and the relative scarcity of those markers in deepset's attack distribution explains the recall gap mechanically. Interpretation 1 (training-distribution overlap) likely also contributes but is not necessary to explain the gap. A further mechanism the audit data (Section 5.4) surfaces is language coverage: 13 of deepset's audit rows are German, and DeBERTa is English-pretrained; on the 8 German injection rows in the audit DeBERTa catches 5 (62.5%), substantially below its English catch rate. The cross-dataset variance is partly a cross-language variance, with deepset disadvantaged because it carries non-English content the classifier was not trained to recognise.

Implication for practitioners: a single F1 number on a single benchmark is not a meaningful summary of an input classifier's protection. The honest summary is per-dataset, or better, per-subcategory.

This pattern fits the underspecification framing of @damour2020Underspecification: pipelines with equivalent training and architecture can produce predictors that behave very differently on stress tests, and aggregate test-set metrics do not surface those differences. The within-dataset analogue is hidden stratification: aggregate accuracy can mask large performance gaps on unidentified subgroups within a single test set. The per-subcategory variation within neuralchemy (Section 5.3, DeBERTa recall ranging from 0.553 on jailbreak to 1.000 on token smuggling on the same model and the same dataset) is the prompt-injection counterpart of the medical-imaging finding documented by @oakden-rayner2020Hidden. The methodological response in both literatures is the same: design evaluations targeted at where predictors differ, and report per-slice numbers alongside aggregate ones.

## 6.2 The layered-defense thesis, refined

The sneak preview shows that the value of an output-side judge varies by attack class. On subtle role-play injections (the deepset misses), the judge catches half the cases the classifier missed. On blunt harmful content (the neuralchemy jailbreak misses), the agent's RLHF alignment refuses before the judge sees a response. On obfuscated payloads (the neuralchemy encoding misses), the agent does not parse the embedded instruction at all.

The combined-defense argument is therefore stronger but more nuanced than a single catch-rate would suggest. The right deployment uses each layer for the attack class it is best at, and accepts that for some attack classes the defense in effect is the model's own training rather than the deployed defense stack.

## 6.3 Judge reliability is upstream of judge cost

The LLM-as-judge methodology was established and validated by @zheng2023Judging against human pairwise preference, with multi-judge agreement and human-judge agreement as the standard validation moves. Section 5.6 applies the same validation to our defense-evaluation use case, with Cohen's kappa as the agreement statistic per @artstein2008InterCoder for NLP annotation tasks. The cost-sensitivity question (can a cheaper judge like Claude Haiku 4.5 or GPT-4o-mini replace Sonnet 4.6 at scale? or conversely, does Claude Opus 4.7 deliver a reliability ceiling worth paying for?) is methodologically downstream of the judge-reliability question. Five measurements now anchor the answer:

1. Cross-judge agreement at the 500-row pilot scale (§5.5b): Sonnet/Haiku kappa = 0.787, Sonnet/GPT-4o-mini kappa = 0.729 under v1.21. Stable to rubric version. Indicates judges substantially agree with each other.

2. Human-vs-judge agreement at the 150-row gold-subset scale (§5.6, post-SPML-fix) under the v1.21 judge rubric (binarised AMBIGUOUS=HIJACKED per §7.6 fail-closed convention, computed via `scripts/rejudge_v125_gold_subset.py` so that v1.21 and v1.25 numbers are apples-to-apples): Sonnet 4.6 kappa = 0.440, Haiku 4.5 kappa = 0.471, GPT-4o-mini kappa = 0.422 against §3.2 v1.23 human labels. The Sonnet v1.21 number here is 0.037 lower than the §5.6 headline (0.477 [0.336, 0.608]) because §5.6 used a slightly different binarisation in `judge_validation_report.md`; both numbers fall well within §5.6's bootstrap CI and the §6.3 number is the one used for the v1.21 → v1.25 comparison below. NONE reach the 0.60 design target but all three are in the "moderate" Landis-Koch band. The pre-SPML-fix numbers were ~0.10-0.20 lower; the lift came from making the SPML agent context consistent with the judge's operator_intent. The remaining gap to 0.60 reflects a residual common bias in all three judges relative to strict §3.2 application: the signature-vs-mechanism pattern matching empirically identified in §5.6 (judges flag based on the appearance of known attack-success tokens such as "I have been PWNED" or DAN persona declarations rather than verifying that the prompt contained an actual override / persona-substitution / authority-escalation mechanism per §3.2).

3. Rubric iteration to v1.25 (signature-vs-mechanism scope note plus four worked examples inserted between Step 0 and Step 1 of the v1.21 prompt; full prompt at `src/defense_b/judge.py::_V125_SYSTEM_HEADER`): Haiku 4.5 kappa rises to **0.554** (+0.083), breaking out of "moderate" toward "substantial" on the Landis-Koch scale. Sonnet 4.6 kappa rises to 0.466 (+0.026), with the lift present only under the AMBIG=HIJACKED convention (under the AMBIG=CLEAN / 3-class / drop-AMBIG alternatives Sonnet v1.25 is tied with or slightly below v1.21). GPT-4o-mini kappa drops to 0.403 (-0.019), within noise. The verdict-shift pattern is strongly one-directional: HIJACKED to CLEAN dominates (Sonnet 31:0, Haiku 23:2, GPT-4o-mini 18:5), confirming v1.25 is doing what it was designed to do — reducing signature-driven false-positive HIJACKED verdicts. The Haiku improvement is the only one robust across all four AMBIGUOUS-handling conventions (AMBIG=HIJ 0.554; AMBIG=CLEAN 0.497; 3-class 0.507; drop-AMBIG 0.541), establishing it as a real reliability gain rather than a convention artifact.

4. Cost ceiling test: Claude Opus 4.7 as a fourth judge on the same 150-row gold subset under v1.25 (Anthropic's top tier, list price $5 input / $25 output per 1M tokens, 5x Haiku's cost). Opus 4.7 kappa = **0.550**, statistically tied with Haiku 4.5 at 0.554 (the 0.004 difference is well within noise on n=150). Verdict distribution: CLEAN 89, HIJACKED 53, AMBIGUOUS 2, parse errors 6. Supplementary conventions: AMBIG=HIJ 0.550, AMBIG=CLEAN 0.461, 3-class 0.481, drop-AMBIG 0.543. Per-dataset Opus vs Haiku splits the per-distribution lead: Haiku is stronger on deepset (0.567 vs 0.465) and tied on neuralchemy (both 0.388); Opus is stronger on SPML (0.683 vs 0.606, the operator_intent-anchored dataset where Opus's longer reasoning depth appears to help). The headline implication for §7.4 cost reasoning: paying 5x more for Opus over Haiku produces no measurable kappa lift on this task; the Anthropic-family cost ceiling on judge reliability is therefore Haiku-level, not Opus-level. Empirical run cost on the 150-row subset: $3.38 ($2.25 input + $1.13 output at the list rates above), one-time spend; logged at `cache/judge_v125_opus_gold_subset.jsonl`.

5. Per-dataset interaction patterns under v1.25: neuralchemy improves on Sonnet (+0.272), Haiku (+0.130), and GPT-4o-mini (+0.095); SPML drops on Haiku (-0.116) and GPT-4o-mini (-0.272) but rises on Sonnet (the latter probably reflects Sonnet's pre-iteration over-conservatism on SPML rather than a rubric effect). The post-iteration Haiku SPML kappa remains in the moderate band at 0.606; Opus 4.7 leads on SPML at 0.683 but at 5x the cost. The SPML drop on cheaper judges reflects an interaction between v1.25's signature-vs-mechanism guidance and SPML's explicit operator_intent anchor; the v1.25 examples do not reference operator-intent-anchored deviations, so the cheaper judges over-correct in the conservative direction on SPML rows. A subsequent v1.26 iteration could add an operator-intent-aware example to the scope note to address this; the current capstone scope does not pursue it.

The cost-vs-reliability picture given these five measurements has changed materially from the §5.6 pre-iteration state:

- Haiku 4.5 with v1.25 (kappa 0.554) is the strongly-recommended production judge across all cost tiers. Haiku now exceeds Sonnet 4.6 on human-judge kappa under every AMBIGUOUS convention, and is statistically tied with Opus 4.7 at 5x the price. Haiku is 3.3x cheaper and 2.6 sec faster than Sonnet (§7.4) and 5x cheaper and similarly fast versus Opus. The previous "statistically tied with overlapping CIs" caveat no longer applies: the v1.25 iteration produced a real kappa lift on Haiku and not on Sonnet, breaking the tie in Haiku's favour.

- Opus 4.7 (kappa 0.550, ~$3.38 per 150-row gold subset run vs Haiku's ~$0.55) does not deliver a reliability ceiling above Haiku. The Anthropic-family judge reliability ceiling on this task is therefore Haiku-level: paying more does not help. Opus retains a niche deployment role on SPML-shaped distributions (kappa 0.683 on SPML vs Haiku's 0.606) where the operator-intent-anchored deviation patterns appear to benefit from Opus's longer reasoning depth, but the 5x cost premium is unlikely to be justified outside that specific case. For typical mixed-distribution deployment, Haiku is dominant.

- Sonnet 4.6 retains a narrow deployment role for cost-tolerant scenarios where AMBIGUOUS verdicts must be handled distinctly rather than collapsed to HIJACKED (e.g., routing to human review queues rather than fail-closing). For the primary §7.6 fail-closed deployment semantic, both Haiku and Opus dominate Sonnet on cost-per-kappa-point.

- GPT-4o-mini's kappa (0.403 under v1.25, essentially unchanged from v1.21) is ~0.15 below Haiku. The 20x cost advantage over Sonnet does not compensate for the larger reliability gap to Haiku, so GPT-4o-mini's deployment role narrows to "fallback when Anthropic-family inference is unavailable" rather than "competitive cost-tier option."

Reproducibility: full v1.25 prompt at `src/defense_b/judge.py::_V125_SYSTEM_HEADER`; per-row verdicts at `results/judge_gold_subset_v125.csv`; primary and supplementary kappa tables at `results/judge_v125_kappa.md`; cached judge responses at `cache/judge_v125_*_gold_subset.jsonl` (incremental, safe to re-run). Total v1.25 measurement cost: ~$3.93 (Sonnet ~$0.30, Haiku ~$0.10, GPT-4o-mini ~$0.05, Opus ~$3.38, all on the same 150-row gold subset).

## 6.4 What the evaluation measures, and against whom [DRAFT-TODO]

> Note for wrap-up writing: distinguish three adversary tiers explicitly so the deployment recommendations carry the right scope. To develop in the final pass; key framing below.

The evaluation in this study, like the public benchmarks it uses, measures defense behaviour against three broadly distinct classes of inputs, and the deployment guidance that flows from it should be read against each class separately.

- Own-goals (legitimate users who trip an injection-shaped pattern unintentionally): a user discussing prompt injection in their query, a developer pasting a prompt-engineering example, a benign request that happens to use words like "ignore" or "forget". These are the false positives Defense A produces on clean traffic. The 38% false-alarm rate on BIPIA clean controls (Section 5.8) is the empirical scale of this class on retrieved-content evaluation.
- Casual attackers (unsophisticated adversaries using canonical patterns): users copying a DAN prompt from a forum, pasting "ignore previous instructions" verbatim, or applying a published jailbreak template. The bulk of the three direct-injection datasets is this class. Defense A's high F1 on neuralchemy and SPML, and Defense C's 86.5% catch rate on the direct-injection pilot, are measured against this distribution.
- Determined adversaries (sophisticated attackers designing against the defenses): semantic-synonym evasion of override language, fictional-framing carriers, novel encodings and homoglyph payloads, multi-turn crescendo attacks [@russinovich2024Great], authority-by-implication, and attacks specifically crafted with knowledge of the deployed defense stack. The deepset dataset captures more of this class than the others (F1 = 0.59 vs 0.95 on SPML), but no public benchmark in this study comprehensively measures defense behaviour against an attacker who is adapting in real time.

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

## 7.4 Latency and cost characteristics of the defense stack

Deployability is bounded by per-prompt latency budget and per-prompt cost. The two combine into a deployment-tier choice: free-form-text judges add 1-6 seconds of latency and $0.10-$3 per 1,000 prompts depending on judge tier, on top of the agent's own latency. The figures below use Artificial Analysis benchmarks for output speed and time-to-first-token (TTFT), accessed 2026-05-27. Cost figures are official provider list pricing.

Per-model latency and price benchmarks (published, third-party-measured)

All API-hosted figures below are from @artificialanalysis2026Llama, accessed 2026-05-27, with per-model bibliography entries `artificialanalysis2026{ModelDescriptor}` in `references.bib` carrying the Wayback-archived URL for each page. The Claude Opus 4.7 row uses Anthropic's API pricing page directly (`anthropic2026Pricing`, Wayback-archived 2026-06-01), since Opus 4.7 was added to the judge set after the Artificial Analysis baseline was captured.

Primary defense components (production-recommended):

| Component | Role in this study | Output speed (tok/s) | TTFT (s) | Input $/1M | Output $/1M | Reference |
|---|---|---|---|---|---|---|
| ProtectAI DeBERTa v3 v2 | Defense A primary classifier | n/a (local) | < 0.05s | $0 | $0 | local inference |
| Meta Prompt Guard 2 86M | Defense A second classifier (OR-gate) | n/a (local) | < 0.05s | $0 | $0 | local inference |
| Llama 3.3 70B Instruct (Together AI) | Primary agent under test | 80.1 (median) | 1.68 | $0.59 | $0.71 | @artificialanalysis2026Llama |
| Claude Sonnet 4.6 (Anthropic) | Defense B v1.21 judge (mid-tier) | 49.2 | 1.32 | $3.00 | $15.00 | @artificialanalysis2026SonnetFortySix |
| Claude Haiku 4.5 (Anthropic) | Defense B v1.25 judge (recommended) | 104.1 | 0.91 | $1.25 | $5.00 | @artificialanalysis2026HaikuFortyFive |
| Claude Opus 4.7 (Anthropic) | Defense B v1.25 judge (cost-ceiling test) | ~40 | ~1.5 | $5.00 | $25.00 | @anthropic2026Pricing |
| GPT-4o-mini (OpenAI) | Defense B judge (cross-family validation) | 47.8 | 1.49 | $0.15 | $0.60 | @artificialanalysis2026GPT4o |

Cross-family agents (used in §5.5b cross-family extension and §5.8 BIPIA email-QA):

| Component | Role in this study | Output speed (tok/s) | TTFT (s) | Input $/1M | Output $/1M | Reference |
|---|---|---|---|---|---|---|
| Qwen 3 235B-A22B-Instruct-2507 (Together) | Cross-family agent | 62.5 | 2.35 | $0.20 | $0.82 | @artificialanalysis2026Qwen3 |
| Mistral Large 2 (Nov 2024, OpenRouter) | Cross-family agent | 31.4 | 1.73 | $2.00 | $6.00 | @artificialanalysis2026Mistral |
| DeepSeek V3 0324 (OpenRouter) | Cross-family agent | not published | not published | $1.19 | $1.25 | @artificialanalysis2026DeepSeek |

The Reference column gives the bibliography descriptor; the full citation, including the Wayback-archived URL with timestamp, is in `references.bib` under the key `artificialanalysis2026{Descriptor}`. Cost figures match Anthropic / OpenAI / Together AI / OpenRouter list pricing as of 2026-05-27; Sonnet 4.6 input is $3.00/M on Anthropic's API (the $3.75 figure on Artificial Analysis is a blended price that includes batch-API and cache-hit discounts averaged together).

Observed wall-time per row in our runs deviates from published median speed for Qwen 3. The SPML re-run on Together AI's hosting of Qwen 3 235B-A22B-Instruct-2507 averaged ~40 sec per agent call, versus the ~8 sec expected from published Alibaba-API benchmarks at the observed 400-token response length. Inspection of the 166 cached Qwen responses confirms no `<think>` tags or unusually long outputs (median 1,595 chars / ~400 tokens, P95 1,989 chars), so the gap is not driven by reasoning-token overhead. The honest reading: Artificial Analysis benchmarks Qwen 3 on Alibaba's first-party API; Together AI's hosting of the same model weights is substantially slower at the concurrency levels used in this study. Mistral Large 2 via OpenRouter ran ~5-8 sec per call, consistent with the published 31.4 tok/s for shorter responses. The reported published numbers should be read as best-case rate-card benchmarks; deployment-time per-prompt latency depends on the actual response length and the provider's serving infrastructure, both of which vary materially.

End-to-end Defense C latency budget for a typical interaction (100-token user query, 400-token agent response, 200-token judge analysis):

| Configuration | Per-prompt latency | Per-1000-prompt cost |
|---|---|---|
| Defense A only (DeBERTa) | < 0.1 s | $0 |
| Agent only (Llama 3.3 70B) | ~6.7 s | $0.34 |
| Defense C with Sonnet judge | ~12.0 s | $2.44 |
| Defense C with Haiku judge | ~9.5 s | $1.09 |
| Defense C with Opus judge | ~12.0 s | $4.50 |
| Defense C with GPT-4o-mini judge | ~12.5 s | $0.43 |

Tier-of-judge choice has the dominant cost lever; the §6.3 v1.25 rubric iteration plus the Opus 4.7 ceiling test establish that the reliability ceiling on the Anthropic family is Haiku-level. Under the v1.21 baseline rubric Haiku 4.5 and Sonnet 4.6 were statistically tied on the 150-row human-vs-judge kappa (0.471 vs 0.440, overlapping CIs); under v1.25 Haiku rises to 0.554, Sonnet rises only to 0.466, and Opus 4.7 enters at 0.550 (statistically tied with Haiku at 5x the cost). Haiku now exceeds Sonnet on human-judge agreement under every AMBIGUOUS-handling convention while remaining 2.2x cheaper on output and 5.6x cheaper on input plus 2.6 s faster per call, and matches Opus on overall agreement while costing 5x less. Haiku 4.5 with the v1.25 rubric is the strongly-recommended production judge across all cost tiers.

Opus 4.7's only per-distribution lead is on SPML (kappa 0.683 vs Haiku 0.606), where the operator-intent-anchored deviation patterns benefit from Opus's longer reasoning depth. Practitioners deploying on system-prompt-heavy distributions (chatbots with strict role anchors, regulated workflows with explicit policy enforcement) may choose Opus there. For typical mixed-distribution deployment, the 5x cost premium is not justified.

GPT-4o-mini's kappa under v1.25 is 0.403, essentially unchanged from its v1.21 value of 0.422. The v1.25 iteration did not help GPT-4o-mini, leaving a 0.15-kappa-point gap to Haiku that the 20x cost advantage over Sonnet does not compensate for. Reserved as a fallback if Anthropic-family inference is unavailable, with the documented reliability gap.

### Multilingual deployment

The §8.8 language-coverage finding applies specifically to Defense A's classifier layer: DeBERTa and Prompt Guard 2 both lose substantial recall on non-English injections (-14pp and -27pp respectively against the audit-confirmed subsample). For enterprise deployments serving multilingual user populations, the recommended configuration substitutes Defense A's English-pretrained classifier with a multilingual base (`microsoft/mdeberta-v3-base` or `xlm-roberta-base`) and leans more heavily on the Defense B LLM-as-judge layer, since the proprietary judges evaluated in §5.6 (Claude Sonnet 4.6, Claude Haiku 4.5, GPT-4o-mini) are multilingual by training and do not suffer the same English-bias. The trade-off is that without a multilingual prompt-injection training corpus, the multilingual classifier base operates without the §5.11 in-distribution fine-tune lift — practitioners should expect approximately the off-the-shelf §5.1 F1 numbers rather than the §5.11 post-LoRA numbers on non-English content. This is the highest-priority data engineering work for multilingual deployments, documented further in §8.8.

### Indirect-injection / retrieved-content deployment

The §5.11 BIPIA extension (NB10 series) establishes that the same Defense A architecture handles indirect injection (attacks embedded in retrieved content rather than user prompts) at the same cost profile as direct injection: a single LoRA adapter (~15MB on disk), single forward pass per inference, same latency as off-the-shelf DeBERTa (< 0.05s local). For enterprise scenarios where the agent reads from a document corpus, email inbox, knowledge base, or any retrieved-content source, the recommended configuration is the NB10e LoRA-v4 adapter (or a practitioner-trained equivalent on their own corpus) applied to the full composed prompt (system prompt + retrieved content + user query) rather than to the user query alone. The §5.8 measurement shows that classifying the user query in isolation misses indirect attacks structurally: the user's question is genuinely benign, so the discriminative signal is in the retrieved content the classifier needs to see.

The augmentation discipline (§5.11 NB10e) is load-bearing. Practitioners should not train Defense A on raw BIPIA-style data with class imbalance left unaddressed (NB10b failed) and should not augment only one class (NB10c learned a shortcut). The two operative rules are: marginal distribution of legitimate user-question phrasings should be approximately equal across clean and attack training rows, and train/val/test split should be stratified at the document level rather than at the (document, question) pair level. Both follow from the pressure-test diagnostics in §5.11. The NB10d pressure-test workflow (Test 1 attack-question ablation in particular) should be re-run on any practitioner-trained adapter before deployment; if the attack-question ablation flag rate drops below 0.95, the augmentation has a residual shortcut and the training data needs to be rebalanced.

Defense B (output judge) remains the correct second layer for indirect injection even with the NB10e Defense A extension in place. The input classifier does not see the agent's response to retrieved content; cases where the agent reads an injected document and produces an attack-shaped output without the input classifier flagging the document (rare given NB10e's 0.000 false-negative rate on the held-out triple cross, but non-zero in production) are caught at the output layer by Defense B per §5.5b. The §7.5 onion model treats input and output filtering as independently-failing layers; this remains correct for indirect injection.

### Internal versus public-facing deployment: the soft-target trap

Hiflylabs' identified use case is an internal LLM agent for employee and contractor workflows (Section 1). The internal framing has two implications that pull in opposite directions and must NOT be conflated:

1. Volume is lower and per-interaction latency tolerance is higher than for a public chatbot. Employees will accept 5-10 second responses on a complex internal task; the same latency would crash conversion on a public consumer chatbot. This is a real budget gain that should be spent on more defense, not on cost reduction.
2. The blast radius per successful attack is larger. A compromised internal agent has access to internal tools, customer PII, financial systems, source code, and authenticated identities for further lateral movement. A compromised public chatbot, in the typical deployment, has access to public-facing read-only information.

Reading internal-audience as "we can relax security because users are trusted" inverts the actual risk profile and creates soft-target conditions: high-value asset behind a defense that has been tuned for an audience assumed to be benign. The §6.4 framing of own-goals, casual attackers, and determined adversaries (whose recommendations apply symmetrically to internal and public deployments) is the operative threat model. Specifically, an internal deployment must account for:

- Authentic insiders (employees with valid credentials acting maliciously, rare but high-stakes)
- Credential-spoofing external attackers (acquired through phishing, leaked passwords, session hijack — these present the same attack signal to the LLM defense as authentic insiders)
- Authentic users committing own-goals (legitimate work that resembles injection patterns)

The defense stack sits downstream of authentication; it sees prompts and responses, not who sent them. So the question is not "are users trusted?" — it is "given the per-prompt cost / latency budget, how many defense layers can we stack without breaking the UX?" For an internal deployment the answer is: more layers than for a public one, because the latency budget is larger and the per-attack cost (if successful) is also larger. This is strictly stronger argument for Defense C (DeBERTa + LLM-as-judge) than for either layer alone, and a strong argument to pair the LLM-defense stack with runtime monitoring, per-identity rate limiting (so spoofed-credential attackers cannot free-fire), and audit trails on flagged interactions.

## 7.5 Hardening recommendations: defense-in-depth beyond the measured stack

The Defense A + Defense B + Defense C numbers in §5 and §7.1-§7.4 characterise three specific defensive components measured against three public benchmarks. A practical deployment guide bridges measured-finding to engineered-system by layering additional controls that this study does not directly evaluate but that follow from the §6.4 threat model and the adversarial-ML literature.

The model below is the eight-layer onion that formalises this bridge. Each layer fails independently and the security posture is the AND of the layers (no single layer is treated as sufficient). The study measures layers 1, 3, and 4; layers 0, 2, 5, 6, and 7 are deployment work the practitioner adds on top.

| Layer | Component | What this study measures | Section reference |
|---|---|---|---|
| 0 | Authentication and authorization | not measured | upstream of LLM stack |
| 1 | Input filtering | Defense A (DeBERTa, Prompt Guard 2) | §5.1, §5.7, §5.11 |
| 2 | Prompt template hardening | not measured | §7.8 |
| 3 | Agent's own RLHF alignment | Defense B observable via §5.5 catch rates | §5.5, §6.2 |
| 4 | Output filtering | Defense B (Sonnet 4.6 v1.21 LLM-as-judge) | §5.5b, §5.5c, §5.6, §5.8 |
| 5 | Tool-level guards | not measured | §7.8 |
| 6 | Runtime monitoring | not measured | §7.9 |
| 7 | Audit, incident response, periodic red-team | not measured | §7.10 |

Sections 7.6-7.10 below characterise the deployment work at the unmeasured layers. The recommendations are anchored to specific empirical findings from §5 where applicable and to peer-reviewed literature where the finding is methodological rather than empirical.

## 7.6 Fail-closed defaults and calibrated threshold tuning

Production prompt-injection defenses fail in three ways: detection error (false negative on real attacks), false-alarm error (false positive on benign traffic), and execution error (defense crashes, API timeout, model unavailable). The third class is operationally underweighted in the academic literature and frequently mishandled in deployment.

**Fail-closed semantics.** A defense that fails-open (treats execution errors as CLEAN and lets the request through) creates a denial-of-service path for the attacker: any input that reliably crashes Defense B's judge API call becomes a free pass. A defense that fails-closed (treats execution errors as HIJACKED) trades availability for security. For internal scenarios where the per-attack cost dominates the per-blocked-prompt cost (§6.4 determined-adversary class with §7.3 high cost ratio), fail-closed is the correct default. The judge wrapper at `src/defense_b/judge.py::_blocked_record_v121` already implements this for content-policy rejections (`anthropic.BadRequestError` and `anthropic.PermissionDeniedError`), recording the verdict as HIJACKED rather than missing-data. Extending fail-closed to network errors and timeouts is a one-line change at the inference call site and is the recommended production posture.

**Threshold tuning under calibrated probabilities.** §5.7b documents that post-hoc temperature scaling of Defense A (T=4.70, overall ECE 0.084 → 0.037, deepset ECE improving 25%) produces calibrated probabilities suitable for non-default decision thresholds. The §5.7b coverage curves show DeBERTa's pre-calibration injection-score distribution is bimodal at 0 and 1, so the default 0.5 threshold gives near-identical results to any threshold in the 0.05-0.95 range. After temperature scaling, the probability distribution spreads and threshold tuning becomes meaningful: at threshold 0.8 the false-alarm rate drops materially on deepset (where DeBERTa was most overconfident pre-calibration), at the cost of a small recall loss on the same dataset. Production deployments with known cost ratios should run the §7.2 cost-weighted scoring with calibrated probabilities to select the optimal threshold per scenario.

## 7.7 Selective prediction and the distilled-defender extension

§5.7b reports a coverage / accuracy curve on Defense A's confidence scores: at confidence threshold 0.99 only 6.0% of the eval set is routed away from auto-classification (selective F1 lifts only +0.022). This is the headline finding that DeBERTa's pre-calibration confidence is not a useful routing signal for selective prediction. The §5.7b paragraph at line 351 documents the implication: with calibrated probabilities, the coverage curve would gain a moderate slope and confidence-based routing would become a usable cost-saving lever for deepset and neuralchemy (but not SPML, which §5.7b found degrades under global temperature scaling).

**Distilled defender for cost reduction.** A complementary deployment path is to distil the layered Defense C stack into a single small classifier (DistilBERT, MiniLM, or similar) trained to mimic Defense C's binary output. The DS4 §6.10 stretch goal scaffolds this as `notebooks/09_defense_c_distillation.ipynb`; results when run produce `results/distillation_metrics.json` with Cohen kappa for student-vs-teacher agreement and student-vs-true-label F1. A successful distillation collapses Defense C's ~5-10 second latency budget (DeBERTa local + Sonnet API + agent inference) into a single ~50ms DistilBERT inference at near-zero per-call cost. The deployment trade-off is whether the student preserves Defense C's catch rate; if Cohen kappa exceeds 0.80 and student F1 vs true labels stays within 0.02 of Defense C F1 on a held-out test set, the student is the appropriate production artifact for cost-sensitive deployments. The §6.4 own-goals + casual-attackers class is the natural scope for the distilled-defender; the determined-adversary class should retain Defense C with the LLM-as-judge layer.

## 7.8 Tool-level hardening for tool-using agents

§5.9 reports a deployment-critical observation about tool-using LLM agents on AgentDojo's workspace suite: when the agent is served from a quantized inference tier (FP8 in our A1 evaluation), it hallucinates tool names at high frequency, calling functions that do not exist in the tool schema. AgentDojo's tool executor returns empty strings on unknown tool names, which compounds the failure (the agent has no feedback to self-correct). Production tool-using deployments are vulnerable to a generalisation of this pattern: any agent that emits a malformed or unrecognised tool call should produce a loud failure rather than a silent empty response. Three layered guards address this:

**Spotlighting and prompt template hardening.** @hines2024Defending "Defending Against Indirect Prompt Injection Attacks With Spotlighting" empirically tests three encoding variants (datamarking, encoding, special-character delimiting) for separating trusted system instructions from untrusted retrieved content in the agent's prompt. The empirical reduction in indirect-injection success rate is substantial across all three variants. Production deployments of tool-using agents (the §6.4 high-blast-radius scenario) should adopt at least one spotlighting variant by default. The implementation cost is a single prompt-template change; the methodological cost is documenting and validating the chosen variant against the deployed model.

**Least-privilege tool design.** Each tool exposed to the agent should expose the minimum capability required for the task. `send_email` should be bounded to internal addresses unless explicitly authorised; `delete_file` should require a confirmation tool call before executing; `transfer_money` should always require human confirmation regardless of the LLM judge verdict. The principle is independent of any LLM defense layer: a tool that cannot do harm cannot be misused regardless of who is calling it, including a hijacked agent.

**Pre-execution argument validation and error visibility.** For sensitive tools, validate arguments against business rules BEFORE the tool executes (not as a wrapper around the LLM). For ALL tools, ensure unrecognised tool names produce an informative error message ("function 'get_appointments' does not exist; available tools are: search_calendar_events, get_day_calendar_events, ...") rather than silently returning empty content. The §5.9 diagnostic finding is direct evidence that the silent-empty-return failure mode degrades both utility and security simultaneously.

## 7.9 Runtime monitoring and anomaly detection

The defense stack at deployment time generates two signals that this study measures at evaluation time but that deployment should expose as monitoring streams:

**Defense agreement as an anomaly signal.** §5.5b reports the cross-judge agreement under v1.21 at the 500-row pilot scale: Sonnet/Haiku 0.752 kappa, Sonnet/GPT-4o-mini 0.644 kappa. The cases where multiple Defense B judges disagree are higher-value for review than the cases where they agree, because disagreement empirically tracks the ambiguous-boundary cases that §3.2 v1.23 identifies. A production deployment running multiple judges (the §5.6 cost-vs-reliability frontier supports this) should log disagreements as ANOMALY-FLAGGED events for human review queue. The §5.5b data show this is a small fraction of total traffic (under 10% in our pilot).

**Defense agreement between Defense A and Defense B.** A prompt that Defense A's input classifier flags as CLEAN while Defense B's output judge flags as HIJACKED is a "missed attack" signal: the attack content was not visible at the input stage but produced an attack-shaped response. Logging these cases is the basis for the periodic adversarial-test-set construction recommended in §7.10. The §5.5c paired McNemar test (Defense A vs Defense C, b=0 c=25 p=5.96e-08 post-SPML-fix) measures this signal directly: 25 of 500 pilot rows fall in the Defense-A-clean / Defense-C-flagged disagreement region.

**Drift detection on defense agreement rates.** The §5.5b cross-judge kappa numbers and the §5.6 human-judge kappa numbers are point-in-time measurements against the May 2026 model snapshots of Sonnet 4.6, Haiku 4.5, and GPT-4o-mini. Provider model updates can shift these numbers materially without notice; the §5.5b numbers themselves shifted by 0.06-0.09 kappa points after the SPML methodology fix. Production deployments should re-measure cross-judge kappa weekly on a stable held-out sample and flag drift exceeding the §5.5b CI half-widths as a model-update-induced regression.

**Canary tokens.** Plant a known unique string in the system context that should never appear in legitimate agent output. If it appears, the agent was prompt-injected to leak system context. This is a single-fire deterministic detector for one specific attack class (H2 extraction in our §3.2 H1-H5 taxonomy), with near-zero false-positive rate. Cheap and high-signal. Recommended as a standing detector on top of Defense B's stochastic LLM judge.

## 7.10 Periodic red-team, defense opacity, and the determined-adversary class

§6.4 distinguishes three adversary classes (own-goals, casual attackers, determined adversaries) and notes that this study's public-benchmark evaluation directly measures the first two but extrapolates only directionally to the third. The hardening work at this layer is what closes the gap.

**Periodic red-team against a private adversarial test set.** @carlini2023Are "Are Aligned Neural Networks Adversarially Aligned?" demonstrates that RLHF-aligned LLMs (including those used as agent and as judge in this study) can be defeated by adversarial inputs crafted with knowledge of the defenses. The §3.2 v1.23 scope note on signature-vs-mechanism, the §5.4 error-pattern analysis showing classifier reliance on override-language keywords, and the §6.1 cross-dataset variance all converge on the same operational implication: any public benchmark used for defense validation will be partially "known" to determined adversaries, who design around its specific surface patterns. The defensive answer is a private adversarial test set, curated quarterly by an internal red-team or contracted security researcher, that is never published. The §5.11 LoRA finding (in-distribution fine-tuning closes the cross-dataset gap on our distribution) gives the operational shape of the defensive update cycle: when the red-team produces new attack samples, retrain the input classifier on the augmented distribution. The fine-tuning cost is trivial (~$1-5 per cycle on Colab). For deployments with retrieved-content surfaces (the §7.4 indirect-injection scenario), the NB10e workflow is the operational template: symmetric augmentation across the (legitimate-question-style × label) axis, base-document-stratified train/val/test split, and the NB10d pressure-test battery (attack-question ablation as the load-bearing probe) run on the new adapter before it replaces the production one. The same template applies symmetrically when the red-team produces new clean-but-injection-shaped queries that trip Defense A's false-alarm rate: rebalance and retrain rather than relax the threshold.

**Defense opacity and the published-benchmark gap.** @apruzzese2022Real "Real Attackers Don't Compute Gradients: Bridging the Gap Between Adversarial ML Research and Practice" empirically documents that real-world attackers use cheaper and simpler attack patterns than the gradient-based adversarial-example literature assumes. The corollary for defenders is that the gap between published benchmark numbers and operational risk is asymmetric: published benchmarks tend to OVERESTIMATE defense effectiveness against real attackers because the benchmarks capture casual-attacker patterns the defense was trained on, while UNDERESTIMATING defense effectiveness against the gradient-based attacks the benchmark stresses but real attackers don't use. The deployment recommendation is to publish the EXISTENCE of a layered defense and the OWASP LLM01 mitigation framework being followed [@owasp2025LLM01], but not the specific component versions, classifier thresholds, or judge prompts. This slows adaptation by determined adversaries without requiring security-through-obscurity at the architectural level.

**Operational runbook for incident response.** When the monitoring layer (§7.9) flags a high-frequency burst of Defense-C-positive events from a single authenticated identity (the §7.4 credential-spoofing scenario), the deployment needs a documented response procedure: rate-limit the identity, revoke session tokens, escalate to security operations, snapshot the agent's recent tool-call history for forensic review. This runbook is operational work outside the scope of this study but follows from the threat model. Production deployments without such a runbook are operationally vulnerable regardless of how well-tuned the §5 defenses are.

# 8. Limitations [FILLED]

## 8.1 Scope of measurement

This evaluation measures the agent's textual compliance with injection attempts, not tool-execution side effects. An agent that produces an innocuous-looking text response while silently firing a malicious tool call is a vector this evaluation cannot observe. Real-tool evaluation requires a sandboxed framework [@debenedetti2024AgentDojo] and is marked as future work.

## 8.2 Judge robustness at the minimum-rubric stage

The 75% agreement between Claude Sonnet 4.6 and GPT-4o at n = 8 (Section 5.6) indicates that the judge call is currently model-family-sensitive. The 150-row human gold subset and 500-row GPT-4o sensitivity subsample address this; until they are complete, all Defense B results carry a judge-reliability caveat.

## 8.3 Inference-provider portability

Defense B at scale ran across two inference providers during the study (Groq for sneak-preview work, Together AI for the formal pilot). Both serve Llama 3.3 70B under the same simulated-agent protocol, but the operational characteristics differ: Groq's on-demand tier has a 100K-token daily cap that limited pilot-scale work, while Together AI's pay-as-you-go pricing imposes no daily cap. The model-class equivalence preserves the methodological position of the study (Llama 3.3 70B simulated via system prompt) across both providers. Production deployments should not interpret the choice of inference provider as a defense-design choice; it is an operational decision about throughput and cost.

## 8.4 Dataset label noise

The 200-row stratified label audit (`reports/label_audit_report.md`) measures Cohen's kappa between the human auditor (applying the v1.22 §3.1 decision tree) and the three datasets' as-released gold labels at 0.930 [0.878, 0.970], "almost perfect" agreement per @landis1977Measurement. Per-dataset disagreement-as-noise-rate proxies: deepset 4.5% [0.9%, 12.5%], neuralchemy 6.0% [1.7%, 14.6%], SPML 0.0% [0.0%, 5.4%], overall 3.5% [1.4%, 7.1%]. This is consistent with the 3.3% average label-error rate @northcutt2021Pervasive document across 10 widely used ML benchmarks. Reported metrics in Section 5 are uncorrected for label noise; the 36-point cross-dataset F1 spread (Section 5.1) is an order of magnitude larger than the noise-rate uncertainty, so the cross-dataset variance finding is robust to this level of label noise. F1 numbers should be read as bounded above by approximately F1_observed plus the per-dataset noise rate.

## 8.5 Subcategory-level inference

Per-subcategory results on neuralchemy include some categories with n as low as 12 to 30. Wilson 95% intervals [@brown2001Interval] are used for per-subcategory recall throughout, so the displayed intervals remain calibrated at small n; the cost is wide intervals (≥ 0.20 at moderate recall when n < 50). Per-subcategory findings are reported as exploratory and not corrected for multiple comparisons. The smallest subcategories in the full breakdown (e.g., crescendo at n = 4, encoding_obfuscation at n = 3) are anecdotes, not measurements, and are noted as such in §5.3.

## 8.6 Multi-modal injection out of scope

The datasets used here are text-only. Multi-modal injection (adversarial perturbations of images or audio) is a real attack channel for multi-modal agents and is not evaluated here.

## 8.7 Reported confidence intervals are data-side only

The bootstrap 95% confidence intervals reported throughout Section 5 measure sampling variability over the 4,546-row frozen evaluation set. They do not measure model-side variability: training seed, checkpoint choice, fine-tuning run, or pretrained-classifier version. @saleva2025Statistical make this distinction explicit and show that accounting for only data-side variability substantially underestimates real replication uncertainty in NLP evaluation. Because Defense A uses off-the-shelf pretrained classifiers with no retraining in this study, model-side variability is structurally absent from our measurement, but it is not zero in the real world: a defender retraining DeBERTa from a different seed on the same data would observe shifted F1 numbers. The reported CIs should be read as a lower bound on the true "is this defense better than that one" uncertainty, and probably a loose one.

## 8.8 Language coverage of the input classifier

The audit-side measurement in Section 5.4 finds that DeBERTa loses approximately 14 percentage points of recall on non-English injections (82.3% English vs 68.4% non-English on the n=98 audit-confirmed injections) and Prompt Guard 2 loses approximately 27 percentage points (53.2% vs 26.3%), despite PG2's multilingual mDeBERTa backbone. The non-English audit sample is small (n=19), heavily German-dominated (13 of 19), and other-language coverage is too thin for per-language conclusions, so the magnitude carries substantial uncertainty; the direction is unambiguous and consistent across both classifiers. The deployment implication is that defense recommendations in Section 7 should be read with a language qualifier: enterprise deployments serving non-English-speaking user populations should treat the reported F1 numbers as upper bounds, and either layer a content-moderation classifier with broader multilingual coverage on top of Defense A, or include language-specific evaluation data in their own validation. A full cross-language Defense A evaluation (DeBERTa and PG2 on a language-stratified test set with multiple non-English languages at n >= 100 each) is marked as future work in Section 9.1.

LoRA fine-tune scope on this limitation. The §5.11 LoRA fine-tune result demonstrates that in-distribution training closes the cross-dataset variance gap for English content. The same training lever is in principle available for multilingual deployments using a multilingual classifier base (`microsoft/mdeberta-v3-base` or `xlm-roberta-base`) and multilingual injection training data. The constraint is the data, not the recipe: public multilingual prompt-injection benchmarks comparable to deepset/neuralchemy/SPML in scope are not available at the time of this study, so we cannot run the multilingual analogue of §5.11 ourselves. BIPIA [@yi2025Benchmarking], used in §5.8 as the indirect-injection anchor, is English-only and does not address the multilingual retrieved-content vector. Multilingual fine-tuning therefore requires either constructing or licensing a multilingual prompt-injection benchmark, or augmenting English benchmarks via machine translation (with the caveat that translation can distort attack signatures by smoothing override-language patterns). Practitioners deploying in multilingual enterprise scenarios should treat this gap as the highest-priority data engineering work that precedes the §5.11 fine-tune recipe.

# 9. Future Work and Conclusion [DRAFT]

## 9.1 Future work

- Real-tool agent evaluation in AgentDojo [@debenedetti2024AgentDojo] to measure action-level compromise beyond textual compliance.
- Custom adversarial test set crafted to target the specific blind spots identified in Section 5.4, to test whether the defenses generalize to attacks shaped by knowledge of their weaknesses.
- Multi-modal extension once a multi-modal injection benchmark is available.
- Production-rubric iteration on the LLM-as-judge component, informed by the human gold subset.
- Deployment-time disagreement monitoring of the LLM-as-judge layer. The cross-judge agreement work in Section 5.6 (Cohen's kappa 0.720 to 0.799 across Sonnet 4.6, Haiku 4.5, and GPT-4o-mini at the 500-row pilot scale) is a one-shot validation measurement. @nguyen2025Reliably propose disagreement-driven deployment monitoring (D3M) as a deployment-time signal: track agreement between judges over time and alert when divergence increases, without requiring ground-truth labels at deployment. Operationalising the multi-judge measurements as a D3M-style monitor would let a deployed system detect drift in attacker behaviour, judge model versions, or workload distribution without re-collecting gold labels.
- Cross-language Defense A evaluation. Section 8.8 documents a ~14pp recall gap between English and non-English injections on the audit subsample; this should be measured at higher per-language n (~100+ per language across German, French, Spanish, Mandarin, Arabic, and other commonly-deployed languages) to quantify the deployment risk and inform multilingual defense-stack recommendations.

## 9.2 Conclusion

Off-the-shelf pre-trained input classifiers (Defense A) for prompt injection deliver high F1 numbers on the benchmarks closest to their training distributions, and substantially weaker performance on benchmarks featuring subtler attacks. The drop is not a calibration problem; it is a coverage problem, and one that ensembling does not solve. An output-side LLM-as-judge (Defense B) is empirically valuable but operates in different ways for different attack classes; its value comes partly from the judge itself and partly from the agent's own RLHF training, depending on the attack pattern. For enterprise deployments, the practical recommendation is a layered defense (input classifier ensemble + output-side judge), per-subcategory production monitoring against known blind spots, and explicit judge-rubric validation against a human-labeled gold subset before scaling.

# References

::: {#refs}
:::

# Appendices

- Appendix A: Operational Definitions (`reports/operational_definitions.md`)
- Appendix B: Methodology and Statistical Choices (`reports/methodology_appendix.md`)
- Appendix C: Contamination Report (`results/contamination_report.md`)
- Appendix D: Label Audit Report (`reports/label_audit_report.md`) [pending audit completion]
- Appendix E: Judge Validation Report (`reports/judge_validation_report.md`) [pending 150-row gold subset]
- Appendix F: Business Decision Framework (`reports/business_decision_framework.md`)
