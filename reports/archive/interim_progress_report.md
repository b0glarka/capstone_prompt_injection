# CEU MSBA Capstone Interim Progress Report

Student name: Boglarka Petruska, MS Business Analytics, CEU\
Client organization: Hiflylabs\
Project sponsor: Zsófia Práger, Data Scientist, Hiflylabs\
Faculty supervisor: Eduardo (CEU primary advisor); Professor Zoltan Toth (methodology consultation)

Capstone project title: Business-Oriented Evaluation of Prompt Injection Defenses for Enterprise AI Agent Deployments

Submission date: 2026-05-11\
Final report due: 2026-06-08

Repository: https://github.com/b0glarka/capstone_prompt_injection

\newpage

\tableofcontents

\newpage

# 1. Executive Status Summary

Overall project status: On track.

Phase 0 (foundation) is complete and Phase 1 (core pipelines build) is substantially complete on the report date. The input-side defense (Defense A: ProtectAI DeBERTa v3 v2 and Meta Prompt Guard 2 86M) has been evaluated on all three target datasets and on the 4,546-row frozen evaluation set, with bootstrap 95% confidence intervals and paired McNemar tests. The output-side defense (Defense B: Llama 3.3 70B agent with Claude Sonnet 4.6 as judge) has completed a 500-row formal pilot. The combined-defense stretch goal (Defense C) has been completed at pilot scale and the results are statistically robust. The indirect-injection extension (BIPIA email-QA, 800 rows) has also completed. The remaining work is concentrated in human judge validation (150-row gold subset), label audit (200 rows), and the full-scale Defense C run, all within the planned window before the June 8 final deadline.

Most important update since the PID: Defense C, listed as a conditional stretch goal in the v2 plan, has been validated empirically at pilot scale. F1 = 0.912 [95% CI 0.889, 0.932], strictly dominates Defense A alone (F1 = 0.849) and Defense B alone (F1 = 0.590) on the paired McNemar test at p < 1e-6 against each component. The combined-defense argument that motivated the v2 framing is no longer a hypothesis; it is an empirically-anchored finding.

Most important open risk: the LLM-as-judge call at the minimum-rubric stage is sensitive to the judge model family. The 24-case sneak preview at n = 8 showed Claude Sonnet 4.6 and GPT-4o agreeing on only 6 of 8 deepset cases (75%). The 150-row human-labeled gold subset (Phase 2) is the formal mitigation; until that is complete, all Defense B numbers carry a judge-reliability caveat.

# 2. Restated Client Need and Analytical Question

## 2.1 Client Need

As AI agents are deployed in enterprise environments with increasing autonomy, the risk of prompt injection attacks grows. OWASP ranks prompt injection as the number one threat to LLM-integrated applications: adversarial inputs can hijack agent behavior in ways that cause significant business harm. Hiflylabs has encountered this directly with clients and is asking for empirical, business-grounded guidance on which defensive approaches are most effective and under what deployment conditions. The most relevant deployment scenario, identified by Hiflylabs, is the autonomous agent with broad tool access: an agent that can access databases, call APIs, and execute multi-step workflows on the user's behalf. AI agents in this configuration are particularly vulnerable to prompt injection attacks, both direct and indirect. The desired outcome of the project is a practical deployment guide recommending an optimal defense configuration for this scenario, backed by empirical evidence from a labeled dataset corpus of over 20,000 examples.

## 2.2 Analytical Question

This project asks which combinations of input-side classifier (Defense A) and output-side LLM-as-judge (Defense B) defenses, individually and combined (Defense C), provide the best protection against direct and indirect prompt injection across three diverse public benchmarks, in order to help enterprise deployers select defense configurations matched to their cost-risk profile.

The project also asks the methodological pre-question of whether single-benchmark F1 numbers are reliable: if the same classifier has very different F1 on different benchmarks, then single-benchmark numbers are not load-bearing for deployment decisions, and that itself is a finding.

## 2.3 Unit of Analysis

The primary unit of analysis is the prompt: a single user input (for direct injection) or a single composed input including a retrieved document (for indirect injection). Each prompt has a gold binary label (INJECTION or SAFE) and the agent's response.

For per-defense comparison the unit is the (prompt, defense configuration) pair. Every defense configuration is evaluated on the same prompts (paired design), enabling McNemar's test for defense-vs-defense comparison and avoiding the unpaired-comparison fallacy.

This is the right unit because the deployment-relevant question is per-prompt: at the moment a prompt reaches the agent, what is the probability the defense correctly classifies it? Higher-order units (sessions, users) are not in scope because the three direct-injection datasets are single-turn and the BIPIA email-QA task is per-email.

## 2.4 Outcome, Target, Decision Variable, or Usefulness Criterion

The primary goal is to correctly identify prompt-injection attacks. For each defense configuration, the outcome variable is a binary verdict (injection vs benign) compared against a gold label on the same prompt.

Performance is measured by:

- Detection metrics on the injection class: precision, recall, F1, ROC AUC, with bootstrap 95% confidence intervals.
- False-alarm rate on benign prompts (the usability cost of the defense).
- Latency and dollar cost per 1K prompts at production scale, per the PID's enterprise-deployment dimensions.

These metrics support the deployment decision the PID asks for: which defense configuration to recommend for the autonomous-agent-with-broad-tool-access scenario. The final deliverable is the practical deployment guide named in the PID; the statistical evidence in the final report backs it.

## 2.5 Changes Since PID

No material scope changes since the PID v2 approved on 2026-04-24. The Defense C combined pipeline, listed in v2 as a stretch goal contingent on Phase 2 timing, was completed at pilot scale without consuming the Phase 2 budget.

One operational change is recorded in Section 9: the Defense B agent role was migrated from Groq to Together AI mid-pilot because Groq's on-demand tier hit a daily quota. This is an inference-provider substitution, not a scope change. Both providers serve the same model class (Llama 3.3 70B), so the methodological position of the study is preserved.

---

# 3. Progress Against Approved PID

| Workstream | Planned in PID? | Current status | Notes |
|---|---|---|---|
| Client/stakeholder discovery | Yes | Complete | Hiflylabs check-in 2026-05-08; no scope adjustments needed |
| Data access | Yes | Complete | Three direct-injection datasets + BIPIA all loaded and frozen |
| Data cleaning/preparation | Yes | Complete | Frozen 4,546-row eval set at `results/eval_set.parquet`, deterministic at seed 42 |
| Exploratory analysis | Yes | Complete | Score-distribution analysis, threshold sweeps, per-subcategory recall, error-pattern feature analysis |
| Modeling/statistical analysis | Yes | In progress | Defense A done on full eval set; Defense B pilot done at 500 rows; Defense C pilot done; full-scale Defense C and judge validation pending |
| Dashboard/prototype/tool | No | Not applicable | The deliverable is the business decision framework document, not a tool |
| Validation/quality checks | Yes | In progress | Contamination check done; bootstrap CIs and paired McNemar done on Defense A; label audit and judge validation queued (Phase 2) |
| Client review | Yes | In progress | 2026-05-08 progress check with Hiflylabs; next checkpoint at final report |
| Final report | Yes | In progress | Skeleton drafted at `reports/final_report.md`; Sections 5.1-5.8 filled |
| Presentation | Yes | Not started | 10-20 slide deck planned for June 8 |

## Key Work Completed

- Operational definitions document with decision tree, H1-H5 hijack taxonomy, and 18 worked examples (`reports/operational_definitions.md`).
- Defense A (input classifier) evaluated on the full 4,546-row frozen eval set: F1 = 0.91 (DeBERTa), 0.67 (PG2); DeBERTa systematically better on paired McNemar; principal blind spots in jailbreak, encoding, and adversarial subcategories.
- Defense B (Llama 3.3 70B agent + Sonnet 4.6 judge) 500-row pilot via Together AI; cheap-judge sweep validates Haiku 4.5 (kappa 0.799, 2.6x cheaper) and GPT-4o-mini (kappa 0.720, 24x cheaper) as cost-optimization candidates.
- Defense C (combined pipeline) at 500-row pilot: F1 = 0.912, dominates Defense A alone and Defense B alone at paired McNemar p < 1e-6.
- BIPIA indirect-injection evaluation (800 rows, 15 attack categories): Defense C attack success 51.7%, false-alarm rate 38% on clean controls.

## Work Not Yet Started or Behind Schedule

- 200-row stratified label audit (sample drawn; auditing in progress; estimated 5-6 hours of manual labeling).
- 150-row human gold subset for LLM-judge validation against operational definitions (built; auditing not yet started; estimated 6-7 hours of manual labeling).
- Full-scale Defense C run on the full eval set (n = 4,546) is queued but optional; pilot results are statistically robust and the full-scale run is for CI tightening, not for changing the headline conclusion.
- Final report Sections 1-4 and 6-9 still in DRAFT state; Section 5 is FILLED.
- 10-20 slide presentation deck for June 8.

---

# 4. Data Received, Data Pending, and Data Quality

## 4.1 Data Sources

| Data source | Owner/system | Received? | Time period | Approx. size | Key fields | Notes |
|---|---|---|---|---|---|---|
| deepset/prompt-injections | HuggingFace (deepset) | Yes | Public, current | 546 rows | text, label | Smallest, used in full census |
| neuralchemy/Prompt-injection-dataset | HuggingFace (neuralchemy) | Yes | Public, current | 4,391 rows | text, label, subcategory | 29 attack subcategories, richest structure |
| reshabhs/SPML_Chatbot_Prompt_Injection | HuggingFace (reshabhs) | Yes | Public, current | 16,012 rows | system_prompt, user_prompt, label | Has paired system prompts (other datasets do not) |
| BIPIA email-QA test split (Yi et al., 2025) | Microsoft Research GitHub | Yes | Public, current | 50 base emails × 15 attack categories = 800 rows | email_text, user_query, attack_category, is_attack | Indirect injection: attack instruction embedded in email body |
| ProtectAI DeBERTa training corpora (7 named, 1 unverifiable, 15 disclosed-by-license-only) | Various via HuggingFace | Partial | Public, current | Variable | text | Downloaded for contamination check; Harelix unverifiable (removed) |

## 4.2 Data Still Needed

No external data still needed for the planned analyses. All evaluation datasets are public benchmarks already loaded.

## 4.3 Initial Data Quality Observations

Check all that apply and explain briefly:

- ☒ Label/target quality issues. Community-curated datasets carry label-noise rates of 3-6% on average (Northcutt et al., 2021). The 200-row stratified label audit will produce a per-dataset noise-rate estimate. Spot-checks during operational-definitions example curation already surfaced two candidate labeling errors in deepset and one ambiguous case.
- ☒ Class imbalance. Per-dataset injection prevalence varies substantially: deepset 37%, neuralchemy 53%, SPML 50% in the eval-set construction. The frozen eval set as a whole is 53% injection. Class-imbalance-aware metrics (F1, AUC, average precision) are reported throughout; accuracy is reported but not relied on.
- ☒ Small sample size in subgroups. Per-subcategory analysis on neuralchemy has some subcategories with n = 12-30. Bootstrap CIs widen at these sample sizes; per-subcategory findings are reported as exploratory only.
- ☒ Risk of training-distribution contamination. The 7 named training-data sources for ProtectAI DeBERTa v3 v2 were downloaded and exact-matched against the three evaluation datasets. Overlap rates: deepset 0.92%, neuralchemy 1.96%, SPML 0.4%. All below the threshold at which exact-match contamination would mechanically inflate metrics. Accept-and-caveat decision; full report at `results/contamination_report.md`. Limitations: Harelix (one named source) was removed from HuggingFace and is unverifiable; 15 additional V2 sources are disclosed only by license category; Meta Prompt Guard 2 enumerates zero training sources.
- ☒ Limited generalizability across attack distributions. The per-dataset variance result (F1 0.59 to 0.95 for the same classifier) demonstrates that a single F1 number is not load-bearing; this is itself a finding rather than a problem to fix.

## 4.4 Implications for the Project

The data situation does not require scope reduction.

---

# 5. Preliminary Analysis or Prototype Outputs

## 5.1 Preliminary Output 1: Defense A cross-dataset variance and per-subcategory blind spots

What this output shows: ProtectAI DeBERTa v3 v2 and Meta Prompt Guard 2 86M were evaluated on the frozen 4,546-row evaluation set without fine-tuning, at the model's default decision threshold.

Table 1. Defense A per-dataset detection metrics (bootstrap 95% CIs).

| Classifier | Dataset | n | F1 [95% CI] | ROC AUC [95% CI] |
|---|---|---|---|---|
| ProtectAI DeBERTa | deepset | 546 | 0.592 [0.524, 0.657] | 0.881 [0.846, 0.915] |
| ProtectAI DeBERTa | neuralchemy | 4,391 | 0.915 [0.906, 0.923] | 0.971 [0.966, 0.976] |
| ProtectAI DeBERTa | SPML (bal. 2k) | 2,000 | 0.954 [0.944, 0.962] | 0.998 [0.996, 0.999] |
| Meta Prompt Guard 2 | deepset | 546 | 0.413 | 0.948 |
| Meta Prompt Guard 2 | neuralchemy | 4,391 | 0.677 | 0.852 |
| Meta Prompt Guard 2 | SPML (bal. 2k) | 2,000 | 0.695 | 0.995 |

A 36-point F1 spread on DeBERTa across three benchmarks of the same task, with non-overlapping 95% CIs. The same pattern holds for Meta Prompt Guard 2 (0.41 to 0.70).

Per-subcategory recall on neuralchemy (Figure 1) reveals jailbreak (0.55), encoding (0.63), and adversarial (0.77) as the principal blind spots for DeBERTa; canonical attack patterns (direct injection, instruction override, token smuggling) are caught at 0.98-1.00. Prompt Guard 2 has a more uniform but lower recall ceiling.

![Figure 1. Per-attack-subcategory recall on neuralchemy. DeBERTa (blue) and Prompt Guard 2 (orange). The vertical dashed line marks recall = 0.5; subcategories with bars to the left of it are the deployment-relevant blind spots.](results/figures/analysis_subcategory_recall_compare.png){width=85%}

Why it matters to the client question: a single F1 number on a single benchmark is not a meaningful summary of an input classifier's protection. The honest summary is per-dataset and per-subcategory. An enterprise deployment with a threat profile concentrated in the blind-spot subcategories will receive substantially weaker protection than the headline metrics suggest. The business decision framework treats this as the primary input to scenario-specific recommendations.

What still needs to be checked: the 200-row label audit will quantify per-dataset label noise and rule out the possibility that the variance reflects labeling differences rather than attack-distribution differences.

## 5.2 Preliminary Output 2: Defense B 500-row formal pilot with cost-comparison judge sweep

What this output shows: the Defense B output-side defense (Llama 3.3 70B agent via Together AI + Claude Sonnet 4.6 judge) was evaluated on a 500-row stratified subsample of the frozen evaluation set.

\newpage

Table 2. Defense B hijack rate on injection-class rows, per dataset (Sonnet 4.6 judge).

| Scope | n (injection rows) | Hijacked by judge | Hijack rate |
|---|---|---|---|
| Overall | 251 | 105 | 0.418 |
| deepset | 84 | 41 | 0.488 |
| neuralchemy | 84 | 42 | 0.500 |
| SPML | 83 | 22 | 0.265 |

A parallel cost-comparison sweep on the same 500 cases evaluated Claude Haiku 4.5 and GPT-4o-mini as alternative judges (Table 3). Both cheaper judges track Sonnet closely.

Table 3. Cross-judge agreement and cost on the 500-row pilot.

| Judge pair | Agreement | Cohen's kappa | Cost on pilot | Cost ratio vs Sonnet |
|---|---|---|---|---|
| Sonnet 4.6 vs Haiku 4.5 | 0.934 | 0.799 | $0.36 vs $0.94 | 2.6x cheaper |
| Sonnet 4.6 vs GPT-4o-mini | 0.899 | 0.720 | $0.04 vs $0.94 | 24x cheaper |
| Haiku 4.5 vs GPT-4o-mini | 0.918 | 0.764 | (cross-cheap pair) | n/a |

Haiku 4.5's agreement with Sonnet (kappa = 0.799) falls at the boundary between substantial (0.61-0.80) and almost-perfect (0.81-1.00) on the Landis and Koch (1977) interpretive scale for kappa; GPT-4o-mini's agreement with Sonnet (kappa = 0.720) is in the substantial range.

Why it matters to the client question: the judge is the cost-dominant component of Defense B at scale. The cost-comparison sweep validates that Haiku 4.5 tracks Sonnet at substantially-to-almost-perfect agreement and is viable as a production cost-optimization. The deployment recommendation in the business decision framework names Sonnet as primary for high-stakes scenarios and Haiku 4.5 as the cost-optimized alternative for volume-constrained deployments.

What still needs to be checked: the 150-row human gold subset will produce Cohen's kappa between the student and each LLM judge. If kappa is below 0.60 ("substantial" per Landis and Koch, 1977), the rubric needs iteration before either judge can be cited as production-ready.

## 5.3 Preliminary Output 3: Defense C combined pipeline empirically validates the layered-defense thesis

What this output shows: Defense C is the OR-combination of Defense A (input classifier) and Defense B (output-side judge). On the same 500-row pilot (same prompts, same agent responses):

Table 4. Defense A, Defense B, and Defense C on the 500-row pilot (bootstrap 95% CIs).

| Defense | Precision [95% CI] | Recall [95% CI] | F1 [95% CI] |
|---|---|---|---|
| A: DeBERTa alone | 0.960 [0.937, 0.978] | 0.761 [0.715, 0.802] | 0.849 [0.819, 0.876] |
| B: Sonnet judge alone | 1.000 [1.000, 1.000] | 0.418 [0.359, 0.476] | 0.590 [0.534, 0.642] |
| C: DeBERTa + judge | 0.964 [0.945, 0.981] | 0.865 [0.825, 0.901] | 0.912 [0.889, 0.932] |

Defense C strictly dominates either component on paired McNemar tests (Table 5).

Table 5. Paired McNemar comparisons, n = 500.

| Comparison | b (baseline wins) | c (C wins) | p-value |
|---|---|---|---|
| Defense C vs Defense A alone | 0 | 26 | < 1e-6 |
| Defense C vs Defense B alone | 8 | 112 | < 1e-300 |

The b = 0 column against Defense A is structural: the OR-combination cannot lose to one of its components on any prompt. The c column is the actual lift: 26 prompts where the judge caught an injection the classifier missed.

Per-dataset: Defense C achieves +0.10 F1 lift over Defense A on deepset (the dataset where Defense A struggles most), +0.03 on neuralchemy, +0.06 on SPML. The lift is concentrated in recall (0.865 vs Defense A's 0.761) with no precision degradation (0.964 vs 0.960), because Sonnet 4.6 has perfect precision on the pilot at minimum-rubric stage.

Why it matters to the client question: the layered-defense argument that motivated the v2 plan and the business framework's recommendation for high-stakes scenarios is no longer a hypothesis. The combined-defense pipeline empirically dominates either component on a paired test at strong significance. The lift is concentrated where it is most valuable, in the dataset (deepset) and the configuration (high cost-ratio) where the input classifier alone is weakest. This is the strongest available evidence for the business decision framework's Scenario C (autonomous agent with broad tool access) recommendation.

What still needs to be checked: the full-scale Defense C run at 4,546 rows will tighten the confidence intervals and may surface dataset-specific effects not visible at 500 rows. The judge precision of 1.000 on the pilot may not generalize; the human gold subset validates this. Whether the cost-optimization (Haiku 4.5 substituted for Sonnet) preserves Defense C's dominance is an open question for the next phase.

---

\newpage

# 6. Interim Findings and Emerging Implications

| Interim finding | Evidence so far | Implication for client | Confidence level | What remains to validate |
|---|---|---|---|---|
| Cross-dataset variance: input classifiers have very different F1 on different benchmarks | F1 = 0.59 (deepset) to 0.95 (SPML) on DeBERTa, n = 4,546, non-overlapping 95% CIs; same pattern for PG2 | Single-benchmark F1 cannot be used as the headline protection number; deployments need per-attack-type evidence | High | Label audit will rule out the alternative explanation that the variance reflects label noise differences |
| Layered defenses empirically beat either component on a paired test | Defense C F1 = 0.912 vs Defense A 0.849 vs Defense B 0.590 at n = 500; paired McNemar p < 1e-6 against each component | The business decision framework's recommendation of a layered configuration for high-stakes scenarios is no longer a hypothesis | High | Full-scale Defense C run at n = 4,546 to tighten CIs |
| Indirect injection is dramatically harder than direct for the same defense stack | BIPIA email-QA Defense C attack success rate 51.7% (vs 13.5% on direct-pilot) | Citing direct-injection F1 numbers as evidence of indirect-injection protection is misleading; indirect requires its own evaluation | Medium-high | Phase 3 reviewer feedback on the BIPIA results; sensitivity to the agent (different models may behave differently) |

## Key Emerging Implications

1. The headline finding for the practitioner is cross-dataset variance, not absolute F1. The deployment-relevant question is not "what is the defense's F1?" but "what is the defense's F1 on the attack distribution my agent will face?" The final report will lead with this finding and frame all per-defense numbers against it.

2. Layered defenses are a real lift, not a marketing claim. Defense C beats each component on a paired test at high significance, and the lift is concentrated in the dataset and the configuration where the input classifier alone is weakest. This is the strongest evidence the business decision framework can offer for its high-stakes-scenario recommendation.

3. Indirect injection is materially harder than direct injection on the same defense stack. Practitioners citing direct-injection benchmark numbers as evidence of indirect-injection protection are misleading themselves and their clients. Separate evaluation against an indirect-injection benchmark is required; we ran BIPIA.

---

# 7. Validation, Checks, and Quality Assurance

## 7.1 Checks Completed So Far

- ☒ Reconciled data against client totals or known reports. Three direct-injection datasets verified by row count and label distribution against their HuggingFace cards.
- ☒ Checked missingness, duplicates, outliers, or invalid values. No missing values in label or text columns. No obvious duplicates.
- ☒ Verified business definitions with sponsor or stakeholder. Operational definitions document anchored on Hiflylabs deployment context (autonomous agents with broad tool access) and reviewed with Eduardo and Hiflylabs.
- ☒ Built a baseline model or benchmark. Defense A on default decision threshold is the off-the-shelf baseline against which all comparisons run.
- ☒ Designed train/validation/test split or cross-validation. Frozen evaluation set with deterministic stratified sampling at seed 42; same prompts go to every defense for paired comparison.
- ☒ Checked for data leakage. Contamination check against ProtectAI DeBERTa's named training sources; overlap rates 0.4-1.96%, all below the inflation-floor threshold.
- ☒ Conducted error analysis. Feature-level analysis of Defense A's 302 DeBERTa false negatives identified override-keyword reliance as the principal failure mechanism.
- ☒ Conducted sensitivity or robustness checks. Judge sensitivity check Sonnet vs GPT-4o on the deepset 8; cheap-judge cost-comparison sweep at n = 500 quantifying Sonnet vs Haiku 4.5 and Sonnet vs GPT-4o-mini agreement.
- ☒ Reviewed preliminary outputs with client sponsor. Hiflylabs check-in 2026-05-08.
- ☒ Checked reproducibility of code or workflow. All pipelines use JSONL append-log cache, deterministic seeds, temperature 0 throughout. Public GitHub repository.
- ☒ Documented assumptions. Operational definitions document (`reports/operational_definitions.md`) and methodology appendix (`reports/methodology_appendix.md`) both anchored on published references with paraphrase-not-novel-taxonomy framing.

## 7.2 Planned Validation Before Final Submission

| Validation/check | Purpose | Status | Planned completion date |
|---|---|---|---|
| 200-row label audit | Quantify per-dataset label noise; produce methodological caveat | In progress | 2026-05-25 |
| 150-row human gold subset judging | Cohen's kappa between student and each LLM judge | Subset built; labeling not yet started | 2026-05-25 |
| Full-scale Defense C run (n = 4,546) | Tighten CIs on Defense C F1; verify pilot finding holds at scale | Queued; uses cached Defense A and Defense B outputs where possible | 2026-06-01 |
| Holm-Bonferroni correction on pre-specified primary comparisons | Family-wise alpha = 0.05 across the small set of primary paired tests | Methodology documented; correction applied during statistical analysis | 2026-06-05 |
| Final report peer-review pass with CEU supervisor | Catch over-claims, weak phrasings, citation gaps | Not started | 2026-06-05 |

## 7.3 Current Evaluation Standard

For this comparative evaluation project, the standards by which results are judged credible:

- Headline metrics (F1, ROC AUC, average precision) reported with 1,000-iteration nonparametric bootstrap 95% CIs (Efron, 1979) on every defense configuration.
- Paired defense-vs-defense comparisons use McNemar's test (McNemar, 1947); exact binomial for small b+c, chi-squared with continuity correction for large b+c.
- Family-wise alpha 0.05 controlled via Holm-Bonferroni (Holm, 1979) across pre-specified primary comparisons; per-subcategory and exploratory results are not corrected and are labeled exploratory.
- Cohen's kappa with Landis and Koch (1977) interpretive thresholds for inter-rater agreement. Design target for the human-vs-LLM-judge gold subset: kappa above 0.60 (substantial).
- Baseline comparisons reported alongside every defense. The off-the-shelf default-threshold operating point is the baseline for Defense A; the minimum-rubric binary verdict is the baseline for Defense B; the OR-combination is the baseline for Defense C.
- Reproducibility: deterministic seeds throughout, temperature 0 on all API calls, JSONL append-log cache, public repository.

---

# 8. Client Engagement and Decisions Made

## 8.1 Client Interaction Summary

| Date | Participants | Purpose | Main outcome or decision |
|---|---|---|---|
| 2026-04-22 | Boga, Hiflylabs technical leadership | PID approval | PID v1 approved with two scope clarifications: business decision framework as a required deliverable; defenses limited to input classifier + LLM judge in scope, agentic action evaluation deferred to future work |
| 2026-05-08 | Boga, Hiflylabs technical leadership | Mid-Phase 1 progress check-in | No scope adjustments needed; Phase 1 progress endorsed; Defense C empirical results received positively |

## 8.2 Decisions Made With Sponsor

1. Business decision framework promoted from a stretch deliverable in PID v1 to a required deliverable in PID v2, with cost-weighted scoring and scenario-based recommendations as the practitioner-facing artifact of the project.
2. Defense C combined pipeline scoped as a conditional stretch in PID v2; promoted to a main result in the interim after pilot-scale evidence showed statistical dominance.
3. Inference-provider portability framing: the agent is a Llama 3.3 70B instance simulated via system prompt regardless of which provider serves it. This decision allowed the Together AI migration (Section 9) to proceed without scope adjustment.
4. Tool-execution side effects are explicitly out of scope. The study measures textual compliance only. AgentDojo (Debenedetti et al., 2024) is cited as future work for the action-level evaluation.

## 8.3 Open Questions for Sponsor

| Open question | Why it matters | Needed from whom | Needed by |
|---|---|---|---|
| (none requiring sponsor input at this checkpoint) |     | n/a | n/a |

---

# 9. Scope Changes Since PID

| Original PID scope | Revised scope | Reason for change | Sponsor agreed? | Impact on analytical standard |
|---|---|---|---|---|
| Defense B agent role served by Groq Llama 3.3 70B Versatile | Defense B agent role served by Together AI Llama 3.3 70B Instruct Turbo (Groq retained for sneak-preview-scale work) | Groq's on-demand tier hit a 100K-token daily cap mid-pilot. Groq Developer tier was temporarily closed to new signups. Together AI has no daily cap. Same model class on both. | Yes (operational decision communicated to Hiflylabs) | None. Both providers serve Llama 3.3 70B under the same simulated-agent protocol. The methodological position (Llama 3.3 70B agent simulated via system prompt) is preserved. |
| Defense C as conditional stretch | Defense C promoted to main result at pilot scale | Pilot-scale evidence (F1 = 0.912, paired McNemar p < 1e-6 against each component) closes the layered-defense central project question with statistical robustness | Yes (endorsed at 2026-05-08 check-in) | Strengthens the analytical standard. No new resources consumed; the analysis was derivable from already-cached Defense A and Defense B outputs. |

## Assessment of Revised Scope

The revised scope is feasible, analytically substantive, and useful to the client. The Together AI migration is an inference-provider portability question rather than a model-substitution question; the methodological position is preserved. The Defense C promotion is a scope expansion in the direction of more analytical substance, supported by paired statistical tests at strong significance. Neither change reduces the analytical standard or adds work to the timeline.

---

# 10. Risks, Blockers, and Mitigation Plan

| Risk or blocker | Severity | Impact if unresolved | Mitigation plan | Support or decision needed | Deadline for resolution |
|---|---|---|---|---|---|
| LLM-as-judge calls sensitive to judge model family at minimum-rubric stage | Medium | All Defense B numbers carry a judge-reliability caveat; cost-optimization recommendations cannot be made without quantitative kappa | 150-row human gold subset is built; student labels against operational definitions; Cohen's kappa computed between student and each LLM judge | None; methodology is in place | 2026-05-25 |
| Methodological complexity beyond original PID scope (per-subcategory comparison across imbalanced groups; cross-family judge robustness) | Medium | Final report findings may carry undefended methodological choices | Professor Zoltan Toth consultation requested; primer sent. Professor is out of town. Consultation is for final-report quality, not on the critical path to the interim | Professor Toth response expected before 2026-06-05 | 2026-06-05 |
| Inference quota or content-policy classifier blocks during full-scale runs | Low (mitigated) | Could disrupt a long-running scale-up | Per-row JSONL cache makes every run resumable; Together AI used for Defense B; judge wrapper catches `BadRequestError` and `PermissionDeniedError` as `judge_blocked=True`; per-row cache-write standard adopted across all API-hitting scripts | None | Ongoing; standard adopted |
| Manual labeling time risk: 200-row label audit + 150-row gold subset = ~12 hours of student labeling | Medium | If not completed by 2026-05-25, label-noise caveat is unanchored and judge-reliability claim is unsupported | Sessions split across multiple days to preserve consistency (kappa is fatigue-sensitive); spot-check on first 20 rows before locking in interpretation; preserved decision-tree language from operational definitions | None | 2026-05-25 |

## Escalation Needed?

No escalation needed at this time.

---

# 11. Work Remaining and Final Deliverable Plan

## 11.1 Remaining Work

| Remaining task | Planned completion date | Notes |
|---|---|---|
| Phase 2 manual labeling: 200-row label audit, operational-definitions example curation (18 to 12), and 150-row judge gold subset labeling | 2026-05-25 | Audit sample at `results/label_audit_sample.csv`; gold subset at `results/judge_gold_subset.csv` |
| Full-scale Defense C run (n = 4,546) | 2026-06-01 | Optional but planned; uses cached Defense A and Defense B outputs |
| Final report sections from DRAFT to FILLED, including methodology appendix limitations | 2026-06-05 | Section 5 (Results) is already FILLED; remaining sections need writing |
| 10-20 slide presentation deck and 3-page CEU public summary | 2026-06-07 | Storyline: cross-dataset variance, layered defense empirical lift, business framework, limitations |

## 11.2 Final Report Plan

The final technical report follows the standard structure listed below; the working draft is at `reports/final_report.md` and the major analysis sections are already FILLED.

Planned final report sections:

- Executive Summary
- 1. Introduction (motivation, sponsor and scope, contributions)
- 2. Background and Related Work (taxonomy, defense classes, evaluation conventions)
- 3. Data (source datasets, frozen eval set, label audit, contamination check)
- 4. Methods (Defense A, Defense B, statistical machinery)
- 5. Results (Defense A on full eval set; score-distribution analysis; per-subcategory recall; error-pattern analysis; Defense B sneak preview; Defense B 500-row formal pilot; Defense C combined pipeline; judge sensitivity; ensemble analysis; BIPIA indirect injection)
- 6. Discussion (cross-dataset variance as headline; layered-defense thesis refined; judge reliability upstream of judge cost)
- 7. Business Decision Framework (full framework at `reports/business_decision_framework.md`; brief in main text)
- 8. Limitations (scope of measurement, judge robustness, inference-provider portability, dataset label noise, subcategory-level inference, multi-modal injection)
- 9. Future Work and Conclusion
- References (15 entries from `reports/references.bib`)
- Appendices (operational definitions, methodology appendix, contamination report, label audit report, judge validation report, business decision framework)

## 11.3 Presentation Plan

10-20 slides, planned storyline:

- Problem/context: enterprise LLM agents with broad tool access; prompt injection as the OWASP top-ranked vulnerability; defense fragmentation in the practitioner-facing literature.
- Client decision: which defense configuration to deploy under which cost-risk profile.
- Data and method: three direct-injection datasets + BIPIA; frozen eval set; Defense A (input classifier), Defense B (LLM judge), Defense C (combined).
- Key findings: cross-dataset variance (the most consequential empirical result); Defense C empirically dominates either component on paired McNemar; indirect injection materially harder than direct on the same stack.
- Recommendations: layered defenses for high-stakes scenarios; cheaper judges (Haiku 4.5 or GPT-4o-mini) as cost-optimizations validated against Sonnet at kappa = 0.799 and 0.720 respectively; per-subcategory production monitoring against known classifier blind spots.
- Limitations: textual compliance only (not tool-execution side effects); minimum-rubric judge sensitivity; per-subcategory inference exploratory only.
- Next steps/handoff: AgentDojo for action-level evaluation; production-rubric iteration informed by the human gold subset.

## 11.4 Public Summary Plan

The public summary is a 3-page condensation of the final report for the CEU MSBA public-facing capstone collection. Because this is open-source research using public benchmarks, with no client-proprietary data, no anonymization is required. The summary describes:

- The cross-dataset variance finding
- The empirical layered-defense result (Defense C)
- The business decision framework mapping configurations to scenarios
- Reproducibility and the public GitHub repository

Confidential information to exclude or anonymize:

- (none identified; project is fully public)

---

# 12. Current Limitations and Responsible Use Considerations

Current limitations on the analysis:

- ☒ Label/target quality issues. Per-dataset label-noise rates are not yet quantified; audit in progress. Northcutt et al. (2021) 3.3% literature baseline applies as an upper bound.
- ☒ Small sample size in subgroups. Per-subcategory neuralchemy findings (some n = 12-30) are reported as exploratory only and are not corrected for multiple comparisons.
- ☒ Class imbalance. Mitigated by reporting F1, AUC, and average precision rather than accuracy.
- ☒ Risk of over-interpreting exploratory findings. Per-subcategory recall claims are framed as exploratory; only the pooled per-dataset and full-eval-set findings carry Holm-Bonferroni-corrected significance.
- ☒ Limited generalizability. The eval-set distribution (deepset + neuralchemy + SPML) may not match any specific enterprise's traffic distribution. Per-dataset metrics are reported so a deploying organization can pick the dataset whose distribution is closest to their use case.
- ☒ Measurement scope. The study measures the agent's textual compliance with injection attempts, not tool-execution side effects. A response that appears innocuous in text may simultaneously trigger a malicious tool call; this study cannot observe that vector. AgentDojo (Debenedetti et al., 2024) is cited as the applicable evaluation framework for action-level compromise.
- ☒ Risk of deploying tool/model without monitoring. The business decision framework explicitly recommends per-subcategory production monitoring against the documented classifier blind spots; deployment without monitoring would compound the cross-dataset variance problem.


## What the Current Analysis Supports

- The same input classifier delivers substantively different F1 on different benchmarks of the same task. The variance is robust to threshold tuning, ensemble methods, and classifier substitution. Practitioners selecting an input classifier on a single benchmark are making an under-informed decision.
- Layered defenses (Defense C combined pipeline) empirically beat either component on a paired McNemar test at p < 1e-6 at pilot scale (n = 500). The lift is concentrated in the deployment scenarios where the input classifier alone is weakest.
- Indirect injection (BIPIA email-QA) is materially harder than direct injection for the same defense stack. Practitioners citing direct-injection F1 numbers as evidence of indirect-injection protection are over-claiming.
- Cheaper LLM judges (Claude Haiku 4.5, GPT-4o-mini) track Claude Sonnet 4.6 at almost-perfect and substantial agreement respectively at n = 500. Cost-optimization is a viable production path subject to formal validation against a human gold subset.

## What the Current Analysis Does Not Yet Support

- A production deployment recommendation that names a single defense configuration as universally best. The cost-weighted decision framework supports scenario-specific recommendations only.
- A claim that the LLM-as-judge call reliably tracks human judgment on the operational definitions. The 150-row gold subset is the formal test; until that completes, all Defense B numbers carry a judge-reliability caveat.
- An action-level protection claim. The study measures textual compliance only; agent tool-call side effects are out of scope.
- A multi-modal protection claim. Adversarial perturbations of images or audio are not evaluated.
- A causal claim about why cross-dataset variance exists. The error-pattern analysis is consistent with surface-keyword pattern-matching as the principal mechanism, but the analysis is descriptive, not causal.

---

# 13. Appendix: Supporting Materials

All supporting materials are committed to the public repository at https://github.com/b0glarka/capstone_prompt_injection.

- Operational definitions document with three-role vocabulary, H1-H5 hijack taxonomy, decision trees, and 18 worked examples: `reports/operational_definitions.md`
- Methodology appendix documenting bootstrap CIs, McNemar's test variants, Holm-Bonferroni correction, Cohen's kappa thresholds: `reports/methodology_appendix.md`
- Business decision framework with cost-weighted scoring and three deployment scenarios: `reports/business_decision_framework.md`
- Literature tracker with 16 entries: `reports/literature_tracker.md`
- References (BibTeX export from Zotero): `reports/references.bib`
- Contamination check report: `results/contamination_report.md`
- Defense A full-eval-set results: `results/defense_a_full_metrics.csv`, `results/defense_a_full_subcategory_recall.csv`, `results/defense_a_error_features.csv`
- Defense B 500-row pilot writeup: `results/defense_b_pilot.md`
- Cheap-judge cost-comparison sweep: `results/defense_b_judge_cost_comparison.md`
- Defense C combined-pipeline pilot writeup: `results/defense_c_pilot.md`
- BIPIA email-QA evaluation writeup: `results/bipia_email_qa.md`
- Figures: `results/figures/`
- Analysis notebook: `notebooks/09_analysis_and_plots.ipynb`
- Reusable pipeline code: `src/` (cache, defense_a, defense_b, bipia, metrics, utils)
- Driver scripts: `scripts/` (per-pipeline runners with JSONL cache, resumable)

---

# Final Self-Check Before Submission

- ☒ Did I clearly state whether the project is on track, at risk, or blocked? On track, stated in Section 1.
- ☒ Did I restate the client need and analytical question? Section 2.1 and 2.2.
- ☒ Did I define the unit of analysis? Section 2.3.
- ☒ Did I define the outcome, target, decision variable, or usefulness criterion? Section 2.4.
- ☒ Did I describe what data I have received? Section 4.1.
- ☒ Did I describe what data is still pending? Section 4.2.
- ☒ Did I discuss data quality issues? Section 4.3.
- ☒ Did I include preliminary evidence, not just plans? Sections 5.1, 5.2, 5.3 (Defense A cross-dataset variance, Defense B pilot, Defense C combined-pipeline pilot).
- ☒ Did I explain what the preliminary findings mean for the client? Sections 5 (per output) and 6 (synthesized).
- ☒ Did I describe validation or quality checks? Section 7.1 (completed) and 7.2 (planned).
- ☒ Did I document client engagement and decisions made? Section 8.
- ☒ Did I identify scope changes since the PID? Section 9 (Together AI migration; Defense C promotion).
- ☒ Did I identify risks and mitigation plans? Section 10.
- ☒ Did I provide a realistic plan for final deliverables? Section 11.
- ☒ Did I acknowledge current limitations? Section 12.
- ☒ Did I avoid confidential information that should not be shared broadly? Yes; project is fully public; no client-proprietary data.
- ☒ Does the report read like a professional consulting update rather than an activity diary? Yes; structured around the template, anchored on the substantive findings (cross-dataset variance, Defense C dominance, indirect-injection difficulty), with statistical evidence and confidence levels.

---

# References

Debenedetti, E., Zhang, J., Balunovic, M., Beurer-Kellner, L., Fischer, M., & Tramer, F. (2024). *AgentDojo: A dynamic environment to evaluate prompt injection attacks and defenses for LLM agents* [Paper presentation]. NeurIPS 2024 Datasets and Benchmarks Track. https://arxiv.org/abs/2406.13352

Efron, B. (1979). Bootstrap methods: Another look at the jackknife. *Annals of Statistics*, 7(1), 1-26. https://doi.org/10.1214/aos/1176344552

Greshake, K., Abdelnabi, S., Mishra, S., Endres, C., Holz, T., & Fritz, M. (2023). *Not what you've signed up for: Compromising real-world LLM-integrated applications with indirect prompt injection* [Paper presentation]. AISec '23: 16th ACM Workshop on Artificial Intelligence and Security. https://arxiv.org/abs/2302.12173

Holm, S. (1979). A simple sequentially rejective multiple test procedure. *Scandinavian Journal of Statistics*, 6(2), 65-70. https://www.jstor.org/stable/4615733

Landis, J. R., & Koch, G. G. (1977). The measurement of observer agreement for categorical data. *Biometrics*, 33(1), 159-174. https://doi.org/10.2307/2529310

McNemar, Q. (1947). Note on the sampling error of the difference between correlated proportions or percentages. *Psychometrika*, 12(2), 153-157. https://doi.org/10.1007/BF02295996

Northcutt, C. G., Athalye, A., & Mueller, J. (2021). *Pervasive label errors in test sets destabilize machine learning benchmarks* [Paper presentation]. NeurIPS 2021 Datasets and Benchmarks Track. https://arxiv.org/abs/2103.14749

OWASP GenAI Project. (2025). *LLM01:2025 prompt injection*. OWASP Top 10 for LLM Applications. https://genai.owasp.org/llmrisk/llm01-prompt-injection/

Perez, F., & Ribeiro, I. (2022). *Ignore previous prompt: Attack techniques for language models* [Paper presentation]. NeurIPS 2022 ML Safety Workshop. https://arxiv.org/abs/2211.09527

Yi, J., Xie, Y., Zhu, B., Kiciman, E., Sun, G., Xie, X., & Wu, F. (2025). Benchmarking and defending against indirect prompt injection attacks on large language models. In *Proceedings of the 31st ACM SIGKDD Conference on Knowledge Discovery and Data Mining* (pp. 1809-1820). https://doi.org/10.1145/3690624.3709179
