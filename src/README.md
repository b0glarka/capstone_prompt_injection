# src

Reusable Python modules for the capstone pipeline. Code that is called from multiple notebooks or scripts lives here. Exploratory/one-off code lives in `notebooks/` and `scripts/`.

## Implemented modules

- `cache.py`: JSONL append-log utilities (`append_records`, `load_records`, `existing_keys`). Crash-resistant; resumable mid-run by checking already-cached keys.
- `defense_a/deberta.py`: inference wrapper for ProtectAI DeBERTa v3 (`DebertaInjectionDetector`). Batched, device auto-detect, returns label + injection score per prompt.
- `defense_b/agent.py`: Groq client wrapper for Llama 3.3 70B Versatile (`GroqAgent`).
- `defense_b/judge.py`: Anthropic client wrapper for Claude Sonnet 4.6 (`ClaudeJudge`) with structured JSON-verdict parsing.

## Planned modules (not yet built)

- `defense_a/prompt_guard.py`: inference wrapper for Meta Prompt Guard 2 (gated behind Llama license; access pending).
- `eval_set.py`: constructs the frozen stratified ~4,546-row evaluation set; saves to `results/eval_set.parquet` with a fixed seed.
- `augmentation/variants.py`: prompt augmentation templates (control, instruction-only, combined).
- `metrics.py`: shared metrics helpers including bootstrap CIs and McNemar's test. Currently inlined in scripts/notebooks; will be consolidated when the third script touches them.
- `utils.py`: shared helpers (env logging, seed setting, pathing). Same status as `metrics.py`.
