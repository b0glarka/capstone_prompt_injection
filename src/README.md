# src

Reusable Python modules for the capstone pipeline. Code that is called from multiple notebooks or scripts lives here. Exploratory and one-off code lives in `notebooks/` and `scripts/`.

## Implemented modules

### Shared infrastructure

- `cache.py`: JSONL append-log utilities (`append_records`, `load_records`, `existing_keys`). Crash-resistant; resumable mid-run by checking already-cached keys.

  **Pipeline caching standard for API-hitting code.** Every script that makes external API calls (Anthropic, OpenAI, Together, Groq, OpenRouter) follows this pattern, because transient 500s, quota exhaustion, and policy classifier blocks are frequent and unrecoverable work is unacceptable.

  1. Cache file: `cache/<script_name>.jsonl` (one JSONL per logical workload).
  2. Stable key per row: `row_id` (preferred) or `prompt_idx`. Must be deterministic across reruns.
  3. Resume check at function entry:
     ```python
     done = existing_keys(CACHE_PATH, key="row_id")
     todo = [r for r in rows if r.row_id not in done]
     ```
  4. **Write per row, not per batch.** Call `append_records(CACHE_PATH, [{"row_id": ..., **out}])` immediately after each API call inside the loop. Do not accumulate a list and write at end-of-loop: a mid-loop crash loses all in-memory work.
  5. After the loop, reload the full cache with `load_records()` if downstream code needs the complete result set.

  Standard adopted 2026-05-11 after a Groq quota-exhaust incident and an Anthropic 500 error in the BIPIA run each cost cached-but-unwritten rows. All active long-running scripts (`defense_b_pilot`, `judge_cost_sweep`, `bipia_email_qa`, `rejudge_v125_gold_subset`) and the retrofitted sneak-preview scripts follow per-row writes.

- `eval_set.py`: constructs the frozen stratified 4,546-row evaluation set; saves to `results/eval_set.parquet` with seed 42. All 546 deepset rows, 2,000 from neuralchemy stratified by label and attack subcategory, 2,000 from SPML balanced 50/50 by label.

- `metrics.py`: shared metrics helpers including accuracy, precision, recall, F1, Cohen's kappa, McNemar's test, bootstrap CIs, Wilson CIs.

- `utils.py`: shared helpers (env logging, seed setting, pathing helpers, masked API-key status printing for notebook setup cells).

### Defense A (input classifier)

- `defense_a/deberta.py`: inference wrapper for ProtectAI DeBERTa v3 v2 (`DebertaInjectionDetector`). Batched, device auto-detect, returns label + injection score per prompt.
- `defense_a/prompt_guard.py`: inference wrapper for Meta Llama Prompt Guard 2 86M and 22M (gated behind Llama license; access granted via `HF_TOKEN`).

### Defense B (LLM-as-judge)

- `defense_b/agent.py`: agent client wrappers.
  - `GroqAgent`: Groq Llama 3.3 70B Versatile. Historical (Phase 1 sneak-preview only); quota exhausted mid-project.
  - `TogetherAgent`: Together AI Llama 3.3 70B Instruct Turbo. Primary production agent from the 500-row pilot onward.
  - `OpenRouterAgent`: OpenRouter cross-family agents (Mistral Large 2, DeepSeek V3, Qwen) for the Section 5.7 cross-agent robustness checks.
- `defense_b/judge.py`: judge classes with structured JSON-verdict parsing.
  - `ClaudeJudge`: Claude Sonnet 4.6 (default) and Opus 4.7 (pass `model="claude-opus-4-7"`). Opus path omits the `temperature` parameter (deprecated in Opus 4.x).
  - `HaikuJudge`: Claude Haiku 4.5. Production-recommended judge under v1.25 per thesis Section 5.4 (judge validation) and Section 7.4 (Hiflylabs internal-agent scenario).
  - `GPT4oJudge`: GPT-4o sensitivity and GPT-4o-mini cost-comparison judge.
  - Each judge supports v1.21 rubric (`judge`) and v1.25 rubric (`judge_v125`, with the signature-vs-mechanism scope note baked into `_V125_SYSTEM_HEADER`).
- `defense_b/rejudge_v121.py`: re-judge utility that re-scores cached agent outputs under a different rubric version without re-running the agent.
- `defense_b/agentdojo_integration.py`: AgentDojo action-level evaluation harness. Cut from the final thesis (queued as future work in Section 9.1) after a Together AI FP8-tier function-call hallucination issue; code preserved for reproducibility.

### Prompt augmentation

- `augmentation/variants.py`: three augmentation templates (control, instruction-only, combined). Pilot notebook `notebooks/06_augmentation_run.ipynb` is scaffolded but not executed; the prompt-augmentation arm was deprioritised in favour of the Section 5.6 LoRA fine-tune arm.

### BIPIA

- `bipia/email_qa.py`: BIPIA email-QA pipeline adapter. Loader (`load_bipia_email_qa`), agent-input composer (`compose_agent_input` for the agent stack), and Defense A composer (`compose_for_defense_a` for the classifier stack). Drives `notebooks/08_bipia_email_qa.ipynb` and the Section 5.6 BIPIA-arm LoRA fine-tune notebooks.
