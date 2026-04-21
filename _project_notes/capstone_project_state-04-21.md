# Capstone Project State
*Updated: April 21, 2026*

---

## Current Phase
PID fully executed and signed by all parties (Boga April 1, Eduardo April 1, Zsófi April 8, NDA co-signed by Dominika Dash, Eva Fodor, Gabor Bekes). Project formally started. Transitioning to active implementation using Claude Code CLI in VSCode terminal.

---

## Confirmed Decisions

**Scope**: Comparative evaluation of prompt injection defenses for enterprise AI agent deployments. Narrowed from Hiflylabs' original five-category brief to prompt injection (direct and indirect) to satisfy CEU's requirement for a statistical analytics workflow.

**Business scenario**: Autonomous agent with broad tool access (email, APIs, code execution). Identified by Zsófi as most relevant to Hiflylabs client work.

**Defenses**:
- Defense A: Input classifier (ProtectAI DeBERTa or Meta Llama Prompt Guard). Pre-trained models downloaded from HuggingFace and evaluated, not trained from scratch.
- Defense B: Output validation via LLM-as-judge. Requires two LLM calls per prompt: first to generate an agent response, second to judge whether that response was hijacked. Judge verdict compared against dataset ground truth label.
- Defense C: Combined A+B, conditional stretch goal only if both pipelines are stable.
- Prompt augmentation: implemented as an unpublished internal baseline (not in proposal, no CEU approval needed).

**How Defense A works**: take prompt from dataset, pass to pre-trained classifier, classifier returns binary prediction, compare to dataset label, compute metrics.

**How Defense B works**: take prompt from dataset, note ground truth label, send prompt to agent LLM, get response, send response to judge LLM with structured evaluation prompt, judge returns hijacked/not hijacked verdict, compare to ground truth label.

**Key constraint from Eduardo**: agent and evaluation pipeline for Defense B must be simple and consistent so results are interpretable.

**Datasets**: Three HuggingFace datasets confirmed via EDA:
- deepset/prompt-injections: 546 train rows, binary labels, avg 118 chars
- neuralchemy/Prompt-injection-dataset: 4,391 train rows, 29 attack subcategories (meaningful subgroups: direct_injection ~1,400, adversarial ~380, jailbreak ~290), avg 143 chars
- reshabhs/SPML_Chatbot_Prompt_Injection: 16,012 train rows, binary labels, avg 603 chars (includes system prompts)
- Combined: 20,949 labeled examples, all binary (0=benign, 1=injection)
- Cross-attack comparison scoped to subcategories with sufficient examples; long tail noted as limitation
- BIPIA (Microsoft): in scope for indirect injection component, set up after core pipeline working
- PINT (Lakera): benchmark framework only, not a data source; research access request submitted; published scores (DeBERTa 79.1%, Llama Prompt Guard 78.8%) used as external reference points

**Data validation notebook**: `data_validation.ipynb` contains EDA confirming dataset suitability. To be restructured into Section 1 (download, run once or on new machine) and Section 2 (EDA from local disk). Data saved locally to `data/` folder which is gitignored. Re-downloadable by running Section 1.

**LLM**: Hiflylabs is model-agnostic. Primary: open-source model via inference provider (Groq recommended, Llama 3.3 70B at $0.59/$0.79 per 1M tokens). Secondary: closed-source model via existing API keys (OpenAI confirmed working) or Hiflylabs-provided access. Total estimated cost under $30.

**Environment**: conda `capstone`, Python 3.11. Repo: `capstone_prompt_injection` on GitHub (private). `data/` gitignored.

**Primary implementation tool**: Claude Code CLI in VSCode terminal.

**Project sponsor**: Zsófi Práger. Weekly 30-minute check-ins. Rescheduled April meeting due to illness.

**Deliverables**: 20-25 page report, 10-20 slide deck, 3-page public CEU summary. Interim due May 11, final due June 8.

**Two-Claude-environment division of labor**: Claude Code CLI for implementation, debugging, pipeline work. This chat project for strategy, methodology decisions, emails, project state updates.

---

## Open Questions
- Lakera PINT dataset access (form submitted, DocuSign link broken, emailed them, no response yet)
- Final LLM and inference provider selection (Groq likely, confirm at pipeline setup)
- Hiflylabs API key offer for closed-source models: follow up with Zsófi when needed
- Defense B judge prompt quality: a poorly designed judge prompt could produce unreliable verdicts independent of whether the attack succeeded. Needs careful design; may warrant sensitivity analysis in report.
- Rescheduled Zsófi check-in: moved from April 8 due to illness, confirm new date

---

## Just Completed
- PID fully executed with all signatures (April 1-8)
- NDA signed by all required parties
- EDA confirmed datasets suitable: 20,949 labeled examples, consistent binary labels, neuralchemy subcategories support interaction analysis for meaningful subgroups

- Clarified how Defense A and Defense B actually work mechanically
- Clarified that Defense A uses pre-trained classifiers, not models built from scratch
- Understood PINT and BIPIA as frameworks/benchmarks, not datasets
- Understood that HuggingFace is standard, credible, non-dubious data source for this type of work
- Confirmed OpenAI API key is active and working
- Decided on Claude Code CLI as primary implementation tool
- April check-in with Zsófi rescheduled due to illness

---

## What's Next
1. Restructure data_validation.ipynb into Section 1 (download, run once) and Section 2 (EDA from local disk), with a markdown cell between them explaining when to run Section 1
2. Reschedule Zsófi check-in
2. Activate capstone conda environment, open repo in VSCode
3. Set up Groq account, test Llama 3.3 70B inference API call
4. Build prompt augmentation baseline pipeline (no API needed, simplest first)
5. Implement Defense A: input classifier using ProtectAI DeBERTa
6. Run Defense A evaluation across all three datasets, compute metrics
7. Design judge evaluation prompt for Defense B
8. Implement Defense B: LLM-as-judge pipeline
9. BIPIA setup for indirect injection (after core pipeline working)
10. Interim report due May 11
