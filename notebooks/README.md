# notebooks

Exploration and pipeline-driver notebooks. Heavy reusable code lives in `src/`; notebooks orchestrate and analyze.

## Planned notebooks (numbered by workflow order)

- `01_data_validation.ipynb` — download and EDA on the three datasets (existing, to be moved from repo root).
- `02_eval_set_construction.ipynb` — build the frozen 6,000-row stratified eval set.
- `03_label_audit.ipynb` — sample 200 labeled prompts, audit against the operational definition, report label noise rate.
- `04_contamination_check.ipynb` — check ProtectAI DeBERTa and Llama Prompt Guard training data disclosures against the eval set.
- `05_defense_a_run.ipynb` — run both classifiers on the eval set (Colab version also in `colab_defense_a.ipynb`).
- `06_augmentation_run.ipynb` — run 3 augmentation conditions through agent + judge.
- `07_defense_b_run.ipynb` — run Defense B pipeline (agent + judge + sensitivity check).
- `08_bipia_email_qa.ipynb` — BIPIA phase 1 (email QA only).
- `09_analysis_and_plots.ipynb` — compute metrics, confidence intervals, produce figures and tables.
- `colab_defense_a.ipynb` — GPU-accelerated version of Defense A inference (syncs predictions CSV back to repo).
