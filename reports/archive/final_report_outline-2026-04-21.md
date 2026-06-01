# Final Report Outline

*Target length: 20-25 pages. Living document; iterated as results come in.*

---

## 0. Executive Summary (1 page)

- Problem: enterprise AI agents face prompt injection attacks; which defense paradigm works better?
- Approach: paired comparison of input-side classifier defense, output-side LLM-judge defense, and prompt-augmentation baseline on ~6,000 stratified prompts from three datasets.
- Headline findings: (placeholder, filled from results)
- Practitioner recommendation: (placeholder)

## 1. Introduction (2-3 pages)

- 1.1 Motivation: agent deployments and the prompt injection threat
- 1.2 Business context: Hiflylabs enterprise client scenario (generic, not client-specific)
- 1.3 Research questions
  - RQ1: How do input-side (classifier) and output-side (LLM-judge) defenses compare in head-to-head paired evaluation?
  - RQ2: How does performance vary across attack subcategories?
  - RQ3: What is the marginal value of prompt augmentation as a first-line defense?
  - RQ4: How do findings generalize to indirect injection (BIPIA)?
- 1.4 Contribution
  - Cross-dataset paired comparison of input-side vs output-side defenses
  - Attack-subcategory breakdowns uncommon in current literature
  - Deployment-relevant FPR/TPR and cost/latency framing
  - Statistical rigor (paired tests, bootstrap CIs, judge sensitivity analysis)

## 2. Background and Related Work (2-3 pages)

- 2.1 Prompt injection: definitions (OWASP LLM01, Greshake et al. 2023)
- 2.2 Defense paradigms
  - Input classification (ProtectAI, Meta Prompt Guard)
  - Output validation (LLM-as-judge)
  - Prompt augmentation (delimiters, sandwich, instruction)
  - Tool sandboxing (out of scope, cited as future work via AgentDojo)
- 2.3 Benchmarks: PINT, BIPIA, InjecAgent, Tensor Trust
- 2.4 Gaps this study addresses

## 3. Data (2-3 pages)

- 3.1 Datasets
  - deepset/prompt-injections (546 train, direct injection, curated)
  - neuralchemy/Prompt-injection-dataset (4,391 train, 29 attack subcategories)
  - reshabhs/SPML_Chatbot_Prompt_Injection (16,012 train, role-play injections)
- 3.2 Label audit methodology and findings (from Phase 0 audit)
- 3.3 Contamination check (ProtectAI and Prompt Guard training data disclosure)
- 3.4 Stratified evaluation set construction (2,000 per dataset, stratified by label and neuralchemy subcategory, seed 42)

## 4. Methods (3-4 pages)

- 4.1 Operational definitions
  - Prompt injection
  - Hijacked agent response (per BIPIA and Greshake criteria)
- 4.2 Defenses evaluated
  - Prompt augmentation: 3 conditions (control, instruction-only, combined)
  - Defense A: ProtectAI DeBERTa and Meta Llama Prompt Guard (threshold analysis)
  - Defense B: agent (Llama 3.3 70B on Groq) + judge (Claude Sonnet 4.6 primary, GPT-4o sensitivity)
- 4.3 Evaluation set and paired design
- 4.4 Metrics and statistical tests
  - Accuracy, precision, recall, F1, AUC
  - TPR/FPR tradeoff at multiple thresholds
  - Macro F1 and per-class F1
  - Cohen's kappa for judge agreement
  - McNemar's paired test for defense-vs-defense
  - Bootstrap 95% CIs
- 4.5 Gold subset for judge validation
- 4.6 Cost and latency measurement
- 4.7 Reproducibility setup (seeds, pinned versions, JSONL caching, published cache)

## 5. Results (5-7 pages)

- 5.1 Headline metrics per defense
- 5.2 Per-dataset breakdown
- 5.3 Attack-subcategory breakdown (neuralchemy subcategories, SPML role-play types)
- 5.4 Defense A vs Defense B paired comparison (McNemar's test)
- 5.5 Defense A threshold analysis (ROC, PR curves)
- 5.6 Judge reliability
  - LLM-vs-LLM kappa (Claude Sonnet 4.6 vs GPT-4o on 500-row sample)
  - LLM-vs-human kappa on gold subset
- 5.7 BIPIA phase 1 results (email QA)
- 5.8 Cost and latency per defense

## 6. Discussion (2-3 pages)

- 6.1 Interpretation of findings
- 6.2 Where each defense paradigm fails
- 6.3 Tradeoffs: FPR vs TPR, cost vs quality, simplicity vs coverage
- 6.4 Limitations
  - Sample size for rare subcategories
  - Simulated-agent methodology (no real tool execution)
  - Judge model dependence
  - Dataset label noise (from audit)
  - External validity to real enterprise traffic
- 6.5 Threats to validity

## 7. Practitioner Recommendations (1-2 pages)

- When to use input-side defenses
- When to use output-side defenses
- When to combine (Defense C discussion)
- Prompt augmentation as minimum viable defense
- Cost-quality decision framework

## 8. Future Work (1 page)

- Full BIPIA expansion across all 5 task types
- AgentDojo-style real tool execution evaluation
- Defense C combined pipeline with formal ensemble analysis
- Fine-tuning / transfer analysis across datasets
- Adversarial red-team set (novel injection crafting)
- Error taxonomy (qualitative failure-mode coding)

## 9. Conclusion (0.5-1 page)

## Appendices

- A. Operational definition of "hijacked" with decision tree and worked examples
- B. Label audit protocol and full results
- C. Judge rubric prompts (full text)
- D. Per-subcategory metric tables
- E. Code repository reference and reproducibility notes
- F. Literature review across adjacent threat vectors (Hiflylabs request)
  - Text-to-SQL injection
  - Excessive agency
  - Indirect injection vectors beyond BIPIA

---

## Writing notes

- Consulting style: clear recommendations, not hedged conclusions.
- Every claim backed by a table or figure reference.
- Limitations section is SPECIFIC and honest, not a ritual recital.
- Executive summary written last, after results are frozen.
