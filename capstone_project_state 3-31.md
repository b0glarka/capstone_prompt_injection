# Capstone Project State
*Updated: March 31, 2026*

---

## Current Phase
PID submitted to Eduardo and Francesca. Awaiting approval to circulate to Hiflylabs for Zsófi's signature.

---

## Confirmed Decisions

**Scope**: Comparative evaluation of prompt injection defenses for enterprise AI agent deployments. Narrowed from Hiflylabs' original five-category brief to prompt injection (direct and indirect) to satisfy CEU's requirement for a statistical analytics workflow.

**Business scenario**: Autonomous agent with broad tool access (email, APIs, code execution). Identified by Zsófi as most relevant to Hiflylabs client work.

**Defenses**: Input classifier (Defense A) and output validation / LLM-as-judge (Defense B) as core. Combined A+B as conditional stretch goal only if both pipelines are stable. Prompt augmentation implemented as an unpublished baseline.

**Datasets**: Three HuggingFace datasets confirmed via EDA as suitable:
- deepset/prompt-injections: 546 train rows, binary labels
- neuralchemy/Prompt-injection-dataset: 4,391 train rows, 29 attack subcategories
- reshabhs/SPML_Chatbot_Prompt_Injection: 16,012 train rows, binary labels
- Combined: 20,949 labeled examples
- BIPIA (Microsoft): in scope for indirect injection component, set up later
- PINT (Lakera): benchmark framework only, not a data source; research access request submitted; published classifier scores used as external reference points

**LLM**: Model-agnostic per Hiflylabs. Primary: open-source model via inference provider (Groq recommended for Llama 3.3 70B). Secondary: closed-source model via existing API keys or Hiflylabs-provided access.

**Project sponsor**: Zsófia Práger (confirmed). Weekly 30-minute check-ins.

**Deliverables**: 20-25 page report, 10-20 slide deck, 3-page public CEU summary. Interim due May 11, final due June 8.

---

## Open Questions
- Eduardo and Francesca approval of revised PID
- Lakera PINT dataset access (form submitted, DocuSign link broken, emailed them)
- Final LLM and inference provider selection (pending implementation start)
- Hiflylabs API key offer for closed-source models: follow up with Zsófi when needed

---

## Just Completed
- Met with Zsófi: confirmed no internal data, LLM-agnostic, Scenario 3 priority, defense preferences
- Revised proposal to reflect Zsófi meeting outcomes
- Discovered PINT and BIPIA are frameworks not datasets
- Identified and validated three HuggingFace replacement datasets via EDA
- Built data validation notebook with label distributions, attack category breakdown, text length distributions, and summary table
- Datasets saved locally to `data/` folder
- Revised PID (v3) completed and submitted to CEU with dataset validation cover note
- capstone conda environment created (Python 3.11)
- Implementation notes saved to `capstone_implementation_notes.md`

---

## What's Next
1. Receive PID approval from Eduardo and Francesca
2. Circulate PID to Zsófi for sponsor signature
3. Set up Groq account and test inference API
4. Begin pipeline setup: prompt augmentation baseline first (simplest, no API needed)
5. Implement input classifier (Defense A) using ProtectAI DeBERTa or Llama Prompt Guard
6. BIPIA setup for indirect injection component (after core pipeline working)
