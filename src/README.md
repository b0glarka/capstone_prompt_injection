# src

Reusable Python modules for the capstone pipeline. Code that is called from multiple notebooks lives here. Exploratory/one-off code lives in `notebooks/`.

## Planned modules

- `eval_set.py`: constructs the stratified 6,000-row evaluation set from the three datasets; saves to `results/eval_set.parquet` with a fixed seed.
- `defense_a/deberta.py`: inference wrapper for ProtectAI DeBERTa.
- `defense_a/prompt_guard.py`: inference wrapper for Meta Llama Prompt Guard.
- `defense_b/agent.py`: Groq client for Llama 3.3 70B agent calls, with JSONL caching.
- `defense_b/judge.py`: Anthropic + OpenAI clients for Claude Sonnet 4.6 and GPT-4o judge calls, with JSONL caching.
- `augmentation/variants.py`: prompt augmentation templates (control, instruction-only, combined).
- `cache.py`: JSONL append-log utilities (dedup by prompt_idx, crash-resistant).
- `metrics.py`: accuracy, precision, recall, F1, Cohen's kappa, bootstrap CIs, McNemar's test.
- `utils.py`: shared helpers (env logging, seed setting, pathing).
