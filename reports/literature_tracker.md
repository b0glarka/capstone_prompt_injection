# Literature Tracker

Capture file for references encountered during the project. Canonical store is Zotero; this file holds quick notes plus a scope decision (main / appendix / future / skip).

## How to use

When a paper or resource lands on your desk:

1. Add it to Zotero (via browser extension or "Add Item by Identifier" with arXiv ID or DOI).
2. Tag it in Zotero: scope tag (`capstone-main`, `capstone-appendix`, `capstone-future-work`), threat-vector tag, content-type tag.
3. Append a block to the relevant section below, following the format:

```
## YYYY-MM-DD : Short title
- Zotero key: @AuthorYearKeyword
- Threat vector: (prompt injection | text-to-sql | excessive agency | indirect injection | ...)
- Scope: (capstone-main | capstone-appendix | capstone-future-work | skip)
- Why captured: one sentence
- Use: where in the report it slots (related work, methods, appendix section, future work)
- Follow-up: yes/no (any read-in-full or verify-benchmark action)
```

Keep each entry under a minute to write. Curate and expand at write-up time.

---

## Prompt injection (direct and indirect) : main study lit review

### 2026-04-21 : OWASP LLM Top 10 2025, LLM01 prompt injection
- Zotero key: `@owasp2025LLM01`
- Threat vector: prompt injection (canonical definition, industry taxonomy)
- Scope: capstone-main (definitions and framing)
- Why captured: top-ranked vulnerability in the OWASP Top 10 for LLM Applications. Authoritative industry-standard definition; names direct and indirect prompt injection as distinct subtypes.
- Use: anchor definition in operational definitions doc + final report intro and taxonomy.
- Follow-up: no.

### 2026-04-21 : Perez & Ribeiro (2022): "Ignore Previous Prompt"
- Zotero key: `@perez2022Ignore`
- Threat vector: prompt injection (direct attack techniques)
- Scope: capstone-main (related work, attack taxonomy)
- Why captured: introduces "goal hijacking" and "prompt leaking" as the two canonical attack goals. Foundational paper on direct prompt injection. NeurIPS 2022 ML Safety Workshop best paper.
- Use: cited in operational definitions Section 1.1 for the two attack-goal taxonomy and in final report Section 2.1.
- Follow-up: no.

### 2026-04-21 : Greshake et al. (2023): indirect prompt injection
- Zotero key: `@greshake2023Not`
- Threat vector: indirect prompt injection (defining paper)
- Scope: capstone-main (related work, motivation for BIPIA extension)
- Why captured: coined the term "indirect prompt injection" and systematically characterized the attack class. AISec '23 workshop. Title and abstract make the direct/indirect distinction explicit.
- Use: cited in operational definitions Section 1.1 for the direct/indirect channel distinction and in final report intro.
- Follow-up: no.

### 2026-04-21 : Yi et al. (2025): BIPIA benchmark
- Zotero key: `@yi2025Benchmarking`
- Threat vector: indirect prompt injection (benchmark)
- Scope: capstone-main (Phase 3 indirect-injection extension)
- Why captured: the standard benchmark for indirect prompt injection. KDD 2025 proceedings (arXiv preprint 2023). 5 task types, 4 attack categories.
- Use: BIPIA email-QA adapter is the Phase 3 deliverable; Section 5.8 / Appendix when results land.
- Follow-up: yes, wire up `src/bipia/email_qa.py` loader to upstream BIPIA repo before execution.

### 2026-04-21 : Toyer et al. (2024): Tensor Trust
- Zotero key: `@toyer2023Tensor`
- Threat vector: prompt injection (attack dataset from online game)
- Scope: capstone-main (related work; ambiguous-case and H3 jailbreak-persona citation)
- Why captured: 126K attacks, 46K defenses crowdsourced from a public game. ICLR 2024. Catalogues DAN-family persona-substitution and authority-escalation attacks at scale, which anchors two ambiguous-case patterns in the operational definitions doc.
- Use: cited in operational definitions Section 1.4 (fictional-framing / DAN pattern, operator-level commands by users) and Section 2.2 H3 (Persona Substitution); 1-sentence mention in final report Section 2 as alternative dataset source we did not use.
- Follow-up: no.

### 2026-05-11 : Shen et al. (2024): "Do Anything Now" in-the-wild jailbreak prompts
- Zotero key: `@shen2024Anything`
- Threat vector: prompt injection (jailbreak prompts, persona-substitution attacks, empirical characterization)
- Scope: capstone-main (operational definitions H3 citation)
- Why captured: CCS 2024. Canonical empirical study of DAN-family jailbreak personas. Characterizes 1,405 in-the-wild jailbreak prompts (Dec 2022 to Dec 2023), identifies 131 jailbreak communities, and analyzes major attack strategies including prompt injection and privilege escalation. Pairs naturally with Toyer et al. as the second citation for the jailbreak-persona phenomenon.
- Use: cited in operational definitions Section 2.2 H3 (Persona Substitution) alongside Toyer et al. (2024).
- Follow-up: no.

### 2026-04-21 : Zhan et al. (2024): InjecAgent
- Zotero key: `@zhan2024InjecAgent`
- Threat vector: indirect prompt injection (tool-integrated agents)
- Scope: capstone-main (related work, future-work pointer)
- Why captured: benchmark for indirect prompt injections in tool-integrated agents. Complements BIPIA with explicit tool-call evaluation. ACL 2024 Findings.
- Use: cited in implementation plan v2 as related work on action-level compromise (which we explicitly scope out).
- Follow-up: no.

### 2026-04-21 : Debenedetti et al. (2024): AgentDojo
- Zotero key: `@debenedetti2024AgentDojo`
- Threat vector: prompt injection in agentic settings (real-tool evaluation)
- Scope: capstone-future-work (explicitly out of scope)
- Why captured: framework for evaluating prompt injection with real tool execution in a sandbox. NeurIPS 2024 D&B. The "action-level compromise" evaluation framework we do not use but cite as future work.
- Use: scope-of-measurement limitation paragraphs (operational definitions Section 5.2, final report Sections 4.2 and 8.1).
- Follow-up: no in this project; flagged as the natural Phase 2 follow-up project.

### 2026-05-11 : Russinovich, Salem & Eldan (2024): Crescendo multi-turn jailbreak
- Zotero key: `@russinovich2024Great`
- Threat vector: multi-turn / conversational prompt injection (jailbreak class)
- Scope: capstone-main (limitations section reference) + capstone-future-work
- Why captured: characterizes the crescendo attack formally - benign early turns build conversational context that makes a final-turn override directive far more effective. Single-prompt defenses cannot detect this by construction.
- Use: cited in operational definitions Section 1.3 (per-turn labeling rule with acknowledged undercount) and Section 5.1 (multi-turn out-of-scope limitation paragraph); referenced in final report Section 8 limitations.
- Follow-up: no for this project (all our benchmarks are single-turn); flagged as natural future-work direction for conversation-level defenses.

### 2026-04-24 : BAGEL: ensemble classifier for malicious prompt detection
- Zotero key: `@hassan2026Efficient`
- Threat vector: prompt injection (defense, input classifier, ensemble)
- Scope: capstone-main (related work) + capstone-future-work
- Why captured: recent (Feb 2026) ensemble-of-classifiers approach using 86M-param fine-tuned specialists with random-forest routing. Distinct design philosophy from our single-classifier Defense A.
- Use: 1-2 sentences in related work contextualizing our single-classifier choice; 1 sentence in future work as "ensemble approaches are a natural extension."
- Follow-up: no. Not worth expanding scope to evaluate directly (would require new wrappers, contamination check, comparison columns).

---

## Text-to-SQL injection : appendix

(no entries yet)

---

## Excessive agency : appendix

(no entries yet)

---

## Additional indirect-injection vectors beyond BIPIA : appendix

(no entries yet)

---

## Statistical methodology foundations : methodology appendix

### 2026-04-21 : Northcutt, Athalye, Mueller (2021): pervasive label errors
- Zotero key: `@northcutt2021Pervasive`
- Threat vector: methodology (label noise in benchmark datasets)
- Scope: capstone-main (methodology motivation for label audit)
- Why captured: NeurIPS 2021 D&B. Documents 3.3% average and up to 6% label error rate across 10 widely-used ML benchmarks. Direct motivation for the 200-row label audit in this study.
- Use: cited in operational definitions Section 5.3 and final report Section 3.3 as the motivation for our audit.
- Follow-up: no.

### 2026-04-21 : Artstein & Poesio (2008): inter-coder agreement
- Zotero key: `@artstein2008InterCoder`
- Threat vector: methodology (kappa for inter-rater agreement)
- Scope: capstone-main (methodology appendix, judge validation framework)
- Why captured: comprehensive Computational Linguistics survey on inter-coder agreement coefficients. The canonical reference for Cohen's kappa interpretation in annotation tasks.
- Use: methodology appendix Section 5; cited in operational definitions Section 1.1 and in final report Section 2.3 for kappa methodology.
- Follow-up: no.

### 2026-05-11 : Efron (1979): bootstrap methods
- Zotero key: `@efron1979Bootstrap`
- Threat vector: methodology (bootstrap confidence intervals)
- Scope: capstone-main (methodology appendix)
- Why captured: founding paper of the nonparametric bootstrap. We use 1,000-iteration bootstrap CIs throughout; this is the canonical citation.
- Use: methodology appendix Section 2; final report Section 4.3.
- Follow-up: no.

### 2026-05-11 : Holm (1979): sequentially rejective multiple test procedure
- Zotero key: `@holm1979Simple`
- Threat vector: methodology (multiple-comparison correction)
- Scope: capstone-main (methodology appendix)
- Why captured: introduces the Holm-Bonferroni correction. Uniformly more powerful than Bonferroni at the same family-wise alpha. We use Holm-Bonferroni on the pre-specified set of primary paired comparisons.
- Use: methodology appendix Section 4; final report Section 4.3.
- Follow-up: no.

### 2026-05-11 : Landis & Koch (1977): observer agreement thresholds
- Zotero key: `@landis1977Measurement`
- Threat vector: methodology (kappa interpretation thresholds)
- Scope: capstone-main (methodology appendix)
- Why captured: source of the conventional kappa interpretation table (0.0-0.20 slight, 0.21-0.40 fair, 0.41-0.60 moderate, 0.61-0.80 substantial, 0.81-1.00 almost perfect). Biometrics 33(1).
- Use: methodology appendix Section 5.2 for kappa interpretation thresholds.
- Follow-up: no.

### 2026-05-11 : McNemar (1947): paired-proportions test
- Zotero key: `@mcnemar1947Note`
- Threat vector: methodology (paired classifier comparison)
- Scope: capstone-main (methodology appendix)
- Why captured: founding paper of McNemar's test. We use exact-binomial McNemar for the pre-specified defense-vs-defense paired comparisons on the same evaluation rows.
- Use: methodology appendix Section 3; final report Section 4.3.
- Follow-up: no. PDF was not obtainable via CEU library access, but the cite is well-anchored elsewhere; metadata-only entry is sufficient.

---

## Deep-learning methodology : ECBS5200-derived

These entries surfaced via the ECBS5200 Deep Learning course methodology audit (`_local/capstone_course_methodology_map_v1.md`, 2026-05-21). They populate methodology, calibration, and future-work slots in the final report.

### 2026-05-21 : D'Amour et al. (2022): Underspecification in ML
- Zotero key: `@damour2020Underspecification` (Better BibTeX pinned the original key year; paper year is 2022 JMLR)
- Threat vector: methodology (model selection under multiple equally-valid predictors)
- Scope: capstone-main (Discussion framing for cross-dataset F1 spread)
- Why captured: names the underspecification phenomenon - ML pipelines with equivalent training produce predictors that behave differently on stress tests. The capstone's 36-point F1 spread on DeBERTa across deepset / neuralchemy / SPML is the textbook scenario. Surfaced via ECBS5200 Week 4.
- Use: cited in final report Discussion section to frame the cross-dataset variance finding.
- Follow-up: no.

### 2026-05-21 : Oakden-Rayner et al. (2020): Hidden stratification
- Zotero key: `@oakden-rayner2020Hidden`
- Threat vector: methodology (hidden subgroups in test data)
- Scope: capstone-main (per-subcategory recall framing)
- Why captured: aggregate accuracy routinely hides >20% performance gaps on unidentified subgroups in medical imaging. The capstone's neuralchemy per-subcategory recall (0.553 jailbreak to 1.000 token smuggling on the same model) is the analogous prompt-injection finding. Surfaced via ECBS5200 Week 4.
- Use: cited in final report Section 5.3 (per-subcategory recall) and Discussion.
- Follow-up: no.

### 2026-05-21 : Guo et al. (2017): On Calibration of Modern Neural Networks
- Zotero key: `@guo2017Calibration`
- Threat vector: methodology (calibration of neural classifiers)
- Scope: capstone-main (methodology appendix + Defense A calibration)
- Why captured: ICML 2017. Standard reference for expected calibration error (ECE) and post-hoc temperature scaling. Establishes that modern neural networks are systematically overconfident; temperature scaling is cheapest and often best fix. Surfaced via ECBS5200 Pre-work 05 + Week 6.
- Use: methodology appendix calibration subsection; cited in final report Section 5 when Defense A ECE numbers land.
- Follow-up: yes - depends on B.3 calibration analysis being executed.

### 2026-05-21 : Sälevä, Ataman, Lignos (2025): Beyond statistical significance
- Zotero key: `@saleva2025Statistical`
- Threat vector: methodology (replication uncertainty in NLP)
- Scope: capstone-main (Limitations section)
- Why captured: arXiv:2509.22612. Distinguishes data-side uncertainty (bootstrap captures) from model-side uncertainty (training seed, checkpoint, fine-tune run; bootstrap does NOT capture). The capstone's CIs are bootstrap-only, so they understate real replication uncertainty by an unknown amount. Surfaced via ECBS5200 Week 4.
- Use: cited in final report Limitations section §8.7 (one-sentence caveat that reported CIs are data-side only).
- Follow-up: no.

### 2026-05-21 : Nguyen et al. (2025): Reliably detecting model failures without labels (D3M)
- Zotero key: `@nguyen2025Reliably`
- Threat vector: methodology / deployment monitoring
- Scope: capstone-future-work (Future Work section)
- Why captured: arXiv:2506.05047. Proposes D3M: a deployment-time monitor that detects model failures based on disagreement of predictive models, without requiring ground-truth labels. Reframes the capstone's multi-judge cross-agreement work (Sonnet 4.6, Haiku 4.5, GPT-4o-mini) from a one-shot validation into a deployment monitor. Surfaced via ECBS5200 Week 4.
- Use: cited in final report Future Work §9.1.
- Follow-up: no.

### 2026-05-21 : Chidambaram et al. (2024): How flawed is ECE?
- Zotero key: `@chidambaram2024How`
- Threat vector: methodology (calibration metric limitations)
- Scope: capstone-main (calibration analysis caveat)
- Why captured: arXiv:2402.10046. Characterises ECE discontinuities and proposes Logit-Smoothed ECE (LS-ECE) as a continuous alternative. Honest caveat to cite alongside any ECE numbers reported on Defense A. Surfaced via ECBS5200 Week 6.
- Use: methodology appendix calibration subsection caveat.
- Follow-up: no.

### 2026-05-21 : Hu et al. (2021): LoRA
- Zotero key: `@hu2021LoRA`
- Threat vector: methodology (parameter-efficient fine-tuning)
- Scope: capstone-future-work (custom-classifier extension)
- Why captured: ICLR 2022. Introduces low-rank adaptation: freezes most weights, adds small trainable rank-r matrices in attention layers, ~2% trainable params at near-full-fine-tune quality. The reference for any LoRA fine-tune of DeBERTa or ModernBERT-base on the capstone's eval set. Surfaced via ECBS5200 Pre-work 06 + Week 3.
- Use: cited if B.9 custom fine-tune extension is executed.
- Follow-up: yes if B.9 is scoped in.

### 2026-05-21 : Dettmers et al. (2023): QLoRA
- Zotero key: `@dettmers2023QLoRA`
- Threat vector: methodology (parameter-efficient fine-tuning at scale)
- Scope: capstone-future-work
- Why captured: NeurIPS 2023. Combines 4-bit NF4 quantization with LoRA to enable fine-tuning of 65B-parameter models on a single 48GB GPU. Relevant if any custom fine-tune extension targets a larger backbone. Surfaced via ECBS5200 Week 5.
- Use: cited alongside Hu 2021 if B.9 is executed at scale beyond DeBERTa.
- Follow-up: no.

### 2026-05-21 : Lin et al. (2018): Focal loss
- Zotero key: `@lin2018Focal` (arXiv version; IEEE TPAMI duplicate removed from Zotero 2026-05-21)
- Threat vector: methodology (class-imbalance loss)
- Scope: capstone-future-work (adversarial training extension)
- Why captured: ICCV 2017. Introduces focal loss for dense object detection; downweights easy examples to concentrate training signal on hard ones. Methodological vocabulary for any adversarial-training extension on the capstone's deepset-style hard cases (40.9% of true injections at injection-class probability 0.000). Surfaced via ECBS5200 Week 2.
- Use: cited if/when adversarial training (v3 plan Section 5.6) is executed.
- Follow-up: no.

### 2026-05-21 : Guo, Pasunuru, Bansal (2021): Overview of uncertainty calibration for text classification and the role of distillation
- Zotero key: `@guo2021Overview`
- Threat vector: methodology (KD framing as calibration regularizer)
- Scope: capstone-future-work (distilled-defender extension)
- Why captured: RepL4NLP 2021. Surveys uncertainty calibration approaches for text classification and frames knowledge distillation as a calibration regularizer (the teacher's softmax-soft labels carry information the student inherits). Relevant if the capstone adds a distilled-defender future-work item compressing Defense C into a single student classifier. Surfaced via ECBS5200 Week 6 memo.
- Use: cited if a distilled-defender extension is executed (Future Work item 5 in course methodology map Part C).
- Follow-up: no.

---

## Future work / deferred

(no entries yet)

---

## Skipped / rejected

Entries that looked plausible but are not useful. Keeping a record prevents re-evaluation if the same paper resurfaces.

(no entries yet)
