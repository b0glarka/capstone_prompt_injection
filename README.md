# Capstone: Comparative Evaluation of Prompt Injection Defenses

MS Business Analytics capstone project (CEU, sponsor: Hiflylabs). Comparative evaluation of input-side and output-side defenses against prompt injection attacks in enterprise AI agent deployments.

## Repo structure

```
capstone_prompt_injection/
├── _project_notes/      Project state, plan, decisions, implementation notes
├── data/                Raw datasets (gitignored, downloaded via notebooks/01_data_validation.ipynb)
├── src/                 Reusable Python modules
├── scripts/             Pipeline-driver scripts (Defense A, B, C, BIPIA, cost sweep)
├── notebooks/           Pipeline-driver and analysis notebooks
├── cache/               JSONL API response caches (gitignored)
├── results/             Computed artifacts (predictions, metrics, figures)
└── reports/             Written deliverables
```

## Environment setup

1. Clone the repo.
2. Install [uv](https://docs.astral.sh/uv/getting-started/installation/) if not already present.
3. Run `uv sync --extra api` from the repo root. This creates `.venv/` with exact pinned versions from `uv.lock`, including the optional API client extras (`anthropic`, `openai`, `groq`) needed for Defense B and the API smoke tests. If you only need Defense A (HuggingFace classifier), plain `uv sync` is sufficient. To reproduce the §5.9 AgentDojo evaluation, additionally install with `uv sync --extra api --extra agentdojo`.
4. Copy `.env.example` to `.env` and fill in the API keys. The example file documents which key each provider expects (Anthropic, OpenAI, Groq, Together AI, OpenRouter, HuggingFace) and which module uses it. `.env` is gitignored. ANTHROPIC_API_KEY now covers Sonnet 4.6, Haiku 4.5 (production-recommended judge), and Opus 4.7 (cost-ceiling test). GROQ_API_KEY is historical (Phase 1 sneak-preview only); production agent work uses Together AI.
5. In VSCode, select `.venv/Scripts/python.exe` (Windows) or `.venv/bin/python` (macOS/Linux) as the kernel for notebooks in `notebooks/`. The kernel is registered by the project as `capstone` if you ran the `ipykernel install` step; otherwise the default `python3` kernel pointing at the venv works too.
6. Run `notebooks/01_data_validation.ipynb` Section 1 once to download the three datasets to `data/`.
7. Verify the API keys with `.venv/Scripts/python.exe scripts/smoke_test_apis.py`. All four API providers (Anthropic, OpenAI, Groq, Together AI) should report PASS. The OpenRouter key is exercised only by the cross-family Defense B agent scripts (`run_*_mistral.py`, `run_*_deepseek.py`); validate it by running one of those scripts at small scale if you need to reproduce the §5.5b cross-family or §5.8 BIPIA cross-family results.

## Local CPU vs Colab Pro GPU split

The repository is split into two reproducibility tiers:

**Tier 1: local CPU reproducible.** Most of the analytical pipeline runs on a laptop without a GPU. Defense A (HuggingFace transformer classifiers DeBERTa-v3 and Prompt Guard 2) and Defense B (API-driven agent + judge) both run on CPU at the pilot scales reported in the final report (500 rows for Defense B, 4,546 rows for Defense A's full eval set is the only run that benefits from GPU). Local-CPU artifacts: `notebooks/01_data_validation.ipynb`, `notebooks/02_eval_set_construction.ipynb`, `notebooks/05_defense_a_pilot.ipynb`, `notebooks/04_contamination_check.ipynb`, `notebooks/08_bipia_email_qa.ipynb`, `notebooks/09_analysis_and_plots.ipynb`, the Defense A scripts in `scripts/run_defense_a_*.py`, the Defense B pilot driver `scripts/run_defense_b_pilot.py`, the v1.21 rejudge script at `src/defense_b/rejudge_v121.py`, the v1.25 rejudge script at `scripts/rejudge_v125_gold_subset.py`, and all the analysis / plotting / augmentation scripts in `scripts/`.

**Tier 2: requires GPU (Colab or equivalent).** Two notebook families need a GPU to execute from scratch: `notebooks/colab_defense_a.ipynb` for the full 4,546-row Defense A scale-up (T4 sufficient, ~5 min wallclock vs ~25 min on CPU), and the `notebooks/08_defense_a_lora_finetune.ipynb` (§5.11 LoRA on direct injection), `notebooks/09_defense_c_distillation.ipynb` (Defense C OR-gate distillation into DistilBERT), and `notebooks/10*.ipynb` series (§5.11 BIPIA arm LoRA iterations) families which need an L4 or T4 GPU for the fine-tuning steps.

Colab session checklist for any Tier 2 notebook: set `HF_TOKEN` in Colab Secrets (for the gated Prompt Guard 2 download if needed), upload the inputs listed in the notebook intro to `MyDrive/capstone_lora/data/`, mount Drive for output, run the notebook, download artifacts back to the repo. The trained LoRA adapters live on Drive (gitignored from this repo); the resulting metrics JSONs and CSVs in `results/` capture the headline numbers for each run.

## Reproducibility and verification without a GPU

A reviewer or future collaborator without a GPU CAN verify every quantitative claim in the final report without re-running the Tier 2 notebooks. Three verification paths:

1. **Post-run notebooks with cell outputs preserved.** Each Tier 2 notebook has a `_post_run.ipynb` companion downloaded from Colab with all execution outputs intact (`notebooks/08_defense_a_lora_finetune_post_run.ipynb`, `notebooks/09_defense_c_distillation_post_run.ipynb`, `notebooks/10_lora_v1_on_bipia_post_run.ipynb` through `10e_lora_v4_symmetric_augmented_post_run.ipynb`). Open them in JupyterLab / VSCode / GitHub's renderer to see exactly what each cell produced. No execution needed.

2. **Canonical metrics JSONs.** Headline numbers reported in the final report sit in `results/lora_metrics.json` (§5.11 direct injection), `results/lora_metrics_extended.json` (§5.11 5-config robustness matrix), `results/lora_v2_metrics.json` (NB10b), `results/lora_v3_metrics.json` (NB10c), `results/lora_v3_pressure_tests.json` (NB10d pressure tests), `results/lora_v4_metrics.json` (NB10e symmetric augmentation), `results/judge_v125_kappa.md` (v1.25 rubric iteration + Opus 4.7 ceiling test).

3. **Reproducibility-as-figure scripts.** `scripts/plot_lora_series_comparison.py` reads the metrics JSONs above and regenerates `reports/figures/lora_series_comparison.png` and `.pdf` locally on CPU. Verifying the figure matches the JSONs takes under 30 seconds on a laptop and does not require GPU, HuggingFace download, or any API call.

The Tier 2 notebooks themselves are kept in the repo because their markdown cells document the methodology choices (the §5.11 BIPIA arm pressure-test workflow lives in NB10d's markdown; the symmetric augmentation discipline is documented in NB10e's intro). Reading the markdown cells gives you the design choices; reading the `_post_run` cell outputs gives you the empirical results. Re-execution is only needed if you want to retrain the LoRA adapters from scratch on your own data.

## Status

Phase 0-3 complete. All empirical work frozen. Final report at `reports/final_report.md` is substantially drafted: §1-§5 complete with figures and tables; §6 Discussion and §7 Business Framework tagged [DRAFT] pending final-week prose polish; §8 Limitations and §9 Future Work + Conclusion are filled. Interim report PDF submitted 2026-05-11 (`reports/Petruska_interim_progress_report.pdf`). Final submission due 2026-06-08.

Key stretch findings since the interim report: §5.11 LoRA fine-tune on direct injection closes the cross-dataset F1 spread from 0.36 to 0.031 (5-config robustness matrix); §5.11 BIPIA arm (NB10 series) produces a deployment-ready Defense A for indirect injection via symmetric augmentation + base-document-stratified splitting; §6.3 / §7.4 judge rubric iteration to v1.25 plus Opus 4.7 cost-ceiling test establishes Haiku 4.5 + v1.25 as the strongly-recommended production judge (kappa 0.554, statistically tied with Opus 4.7 at 5x less cost).

See `_project_notes/INDEX.md` for navigation. Latest state at `_project_notes/capstone_state.md`, detailed plan at `_project_notes/capstone_plan.md`.

## Deliverables

- Interim progress report, due May 11
- Final 20-25 page report, due June 8
- 10-20 slide deck
- 3-page public CEU summary
