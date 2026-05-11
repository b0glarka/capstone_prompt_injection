# src

Reusable Python modules for the capstone pipeline. Code that is called from multiple notebooks or scripts lives here. Exploratory/one-off code lives in `notebooks/` and `scripts/`.

## Implemented modules

- `cache.py`: JSONL append-log utilities (`append_records`, `load_records`, `existing_keys`). Crash-resistant; resumable mid-run by checking already-cached keys.

  **Pipeline caching standard for API-hitting code:**
  Every script that makes external API calls (Anthropic, OpenAI, Together, Groq) must follow this pattern, because transient 500s, quota exhaustion, and policy classifier blocks are frequent and unrecoverable work is unacceptable.

  1. Cache file: `cache/<script_name>.jsonl` (one JSONL per logical workload).
  2. Stable key per row: `row_id` (preferred) or `prompt_idx`. Must be deterministic across reruns.
  3. Resume check at function entry:
     ```python
     done = existing_keys(CACHE_PATH, key="row_id")
     todo = [r for r in rows if r.row_id not in done]
     ```
  4. **Write per row, not per batch.** Call `append_records(CACHE_PATH, [{"row_id": ..., **out}])` immediately after each API call inside the loop. Do not accumulate a list and write at end-of-loop: a mid-loop crash loses all in-memory work.
  5. After the loop, reload the full cache with `load_records()` if downstream code needs the complete result set.

  Forward standard adopted 2026-05-11 after a Groq quota-exhaust incident and an Anthropic 500 error in the BIPIA run each cost cached-but-unwritten rows. Three active long-running scripts (defense_b_pilot, judge_cost_sweep, bipia_email_qa) follow per-row writes. Four early sneak-preview scripts (defense_b_sneak_preview, defense_b_neuralchemy_encoding, defense_b_neuralchemy_jailbreaks, gpt4o_sensitivity_deepset) were retrofitted to the same pattern.
- `defense_a/deberta.py`: inference wrapper for ProtectAI DeBERTa v3 (`DebertaInjectionDetector`). Batched, device auto-detect, returns label + injection score per prompt.
- `defense_b/agent.py`: Groq client wrapper for Llama 3.3 70B Versatile (`GroqAgent`).
- `defense_b/judge.py`: Anthropic client wrapper for Claude Sonnet 4.6 (`ClaudeJudge`) with structured JSON-verdict parsing.

## Planned modules (not yet built)

- `defense_a/prompt_guard.py`: inference wrapper for Meta Prompt Guard 2 (gated behind Llama license; access pending).
- `eval_set.py`: constructs the frozen stratified ~4,546-row evaluation set; saves to `results/eval_set.parquet` with a fixed seed.
- `augmentation/variants.py`: prompt augmentation templates (control, instruction-only, combined).
- `metrics.py`: shared metrics helpers including bootstrap CIs and McNemar's test. Currently inlined in scripts/notebooks; will be consolidated when the third script touches them.
- `utils.py`: shared helpers (env logging, seed setting, pathing). Same status as `metrics.py`.
