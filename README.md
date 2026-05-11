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
2. Install [uv](https://docs.astral.sh/uv/getting-started/installation/) if not already present.
3. Run `uv sync --extra api` from the repo root. This creates `.venv/` with exact pinned versions from `uv.lock`, including the optional API client extras (`groq`, `anthropic`, `openai`) needed for Defense B and the API smoke tests. If you only need Defense A (HuggingFace classifier), plain `uv sync` is sufficient.
4. Create a `.env` file at the repo root with:
   ```
   HF_TOKEN=hf_your_token
   GROQ_API_KEY=gsk_your_key
   ANTHROPIC_API_KEY=sk-ant-...
   OPENAI_API_KEY=sk-...
   ```
5. In VSCode, select `.venv/Scripts/python.exe` (Windows) or `.venv/bin/python` (macOS/Linux) as the kernel for notebooks in `notebooks/`. The kernel is registered by the project as `capstone` if you ran the `ipykernel install` step; otherwise the default `python3` kernel pointing at the venv works too.
6. Run `notebooks/01_data_validation.ipynb` Section 1 once to download the three datasets to `data/`.
7. Verify the API keys with `.venv/Scripts/python.exe scripts/smoke_test_apis.py`. All three providers should report PASS.

## Local CPU vs Colab Pro GPU split

Defense A (HuggingFace transformer classifiers) and Defense B (API-driven agent + judge) can both run on a laptop CPU at pilot scale (~500-2,000 rows). The local pilot notebooks `05_defense_a_pilot.ipynb`, `06_augmentation_run.ipynb`, and `07_defense_b_pilot.ipynb` are designed for this.

For the formal scale-up to the full 4,546-row frozen evaluation set, Defense A runs much faster on a GPU. Use `notebooks/colab_defense_a.ipynb` on a Colab Pro T4 instance: under 5 minutes wallclock for both classifiers vs ~25 minutes on CPU. Defense B is API-side and does not benefit from a Colab GPU; run it locally with caching to disk regardless of whether you are on Colab or laptop.

Colab session checklist: upload `results/eval_set.parquet` (gitignored, build locally first), set `HF_TOKEN` in Colab Secrets, mount Drive for output, run the notebook, copy artifacts back. Detailed steps inside the Colab notebook.

## Status

Active implementation. See `_project_notes/INDEX.md` for navigation. Latest state at `_project_notes/capstone_state.md`, detailed plan at `_project_notes/capstone_plan.md`.

## Deliverables

- Interim progress report, due May 11
- Final 20-25 page report, due June 8
- 10-20 slide deck
- 3-page public CEU summary
