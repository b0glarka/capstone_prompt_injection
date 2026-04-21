# Capstone: Comparative Evaluation of Prompt Injection Defenses

MS Business Analytics capstone project (CEU, sponsor: Hiflylabs). Comparative evaluation of input-side and output-side defenses against prompt injection attacks in enterprise AI agent deployments.

## Repo structure

```
capstone_prompt_injection/
├── _project_notes/      Project state, plan, decisions, implementation notes
├── data/                Raw datasets (gitignored, downloaded via notebooks/01_data_validation.ipynb)
├── src/                 Reusable Python modules
├── notebooks/           Pipeline-driver and analysis notebooks
├── cache/               JSONL API response caches (gitignored)
├── results/             Computed artifacts (predictions, metrics, figures)
└── reports/             Written deliverables
```

## Environment setup

1. Clone the repo.
2. Create the conda environment: `conda env create -f environment.yml` and activate `capstone`.
3. Create a `.env` file at the repo root with:
   ```
   HF_TOKEN=hf_your_token
   GROQ_API_KEY=gsk_your_key
   ANTHROPIC_API_KEY=sk-ant-...
   OPENAI_API_KEY=sk-...
   ```
4. Run `notebooks/01_data_validation.ipynb` Section 1 once to download the three datasets to `data/`.

## Status

Active implementation. See `_project_notes/INDEX.md` for navigation. Latest state at `_project_notes/capstone_state.md`, detailed plan at `_project_notes/capstone_plan.md`.

## Deliverables

- Interim progress report, due May 11
- Final 20-25 page report, due June 8
- 10-20 slide deck
- 3-page public CEU summary
