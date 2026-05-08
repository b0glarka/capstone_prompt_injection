- Purpose: session-bridge snapshot for Claude conversation continuity. Read this first when resuming work.
- Status: active (overwritten per update)
- Memorializing: 2026-05-08 (Defense A on three datasets + Defense B sneak preview on three attack classes + judge sensitivity + Prompt Guard 2 in progress, immediately pre-Hiflylabs check-in)
- Last updated: 2026-05-08 (final reconciliation pass)
- Related: [capstone_plan.md](./capstone_plan.md), [capstone_methodology_decisions.md](./capstone_methodology_decisions.md), [implementation_plan_summary_v2.md](./implementation_plan_summary_v2.md)

---

# Capstone State

## Current phase

Phase 0 (Foundation) in progress. Full plan at [capstone_plan.md](./capstone_plan.md). Methodology rationale at [capstone_methodology_decisions.md](./capstone_methodology_decisions.md). Shared implementation plan at [implementation_plan_summary_v2.md](./implementation_plan_summary_v2.md).

Interim progress report due May 11. Final due June 8.

## Active open questions

- Interim format, audience, and polish level: partially answered by Eduardo (he had no real critiques, no formal template required). Full answer pending confirmation but lower-priority than initially assumed.
- Deferred scope decisions remain in user hands (stress-test set, error taxonomy, Defense C, BIPIA expansion, etc.). Go/no-go at checkpoints per the plan.
- Budapest visit window: flexible, low priority.

## What changed in this update

Since 2026-04-24:

- **Defense A pilot complete on three datasets** (2026-05-08). ProtectAI DeBERTa v3 run on full deepset (n=546), full neuralchemy (n=4,391), and balanced 2k SPML subsample.
  - deepset: F1 0.59 [0.52, 0.66], AUC 0.88 [0.85, 0.92]. Score distribution bimodal; 40.9% of injections scored 0.000; threshold sweep yields only +0.13 F1 lift. Residual error is a coverage problem, not calibration.
  - neuralchemy: F1 0.91 [0.91, 0.92], AUC 0.97 [0.97, 0.98]. Per-subcategory blind spots: jailbreak 0.55, encoding 0.63, adversarial 0.77. Bulk patterns (direct injection 0.98, instruction override 1.00, RAG poisoning 1.00) handled near-perfectly.
  - SPML (balanced 2k): F1 0.95 [0.94, 0.96], AUC 0.998 [0.996, 0.999]. Recall flat at ~0.99 across all severity Degrees 1-10. Top of the F1 range; consistent with SPML's user-turn injections falling in the direct-instruction-override pattern class.
  - Cross-dataset spread is now 36 F1 points (deepset 0.59 → SPML 0.95). 95% CIs do not overlap. Same model, same threshold. Both readings (distribution-shift vs partial contamination) reinforce the layered-defense thesis. SPML's 0.4% contamination rate rules out the contamination reading as a primary explanation; deepset remains the most conservative deployment estimate.
- **Pipeline scaffolding**: `src/cache.py`, `src/defense_a/deberta.py`, `src/defense_a/prompt_guard.py`, `src/defense_b/agent.py` (Groq Llama 3.3 70B), `src/defense_b/judge.py` (Claude Sonnet 4.6 + GPT-4o sensitivity, both with JSON-verdict parsing). Notebooks `05_defense_a_pilot.ipynb`, `06_defense_a_neuralchemy.ipynb`, `07_defense_a_spml.ipynb`. Scripts: data-validation runs, all three Defense A dataset runs, three Defense B previews (deepset / jailbreak / encoding), GPT-4o sensitivity, three figure scripts (cross-dataset summary, score distributions, confusion grid), label-audit sampler, API smoke test.
- **Defense B sneak preview, three attack classes** (8 cases each, all DeBERTa misses):
  - deepset role-play / persona-shift injections: judge flagged 4/8. Judge load-bearing on subtle injections.
  - neuralchemy jailbreak-class (hate-content / harm-facilitation): judge flagged 0/8. Llama 3.3 70B refused all 8 on its own RLHF alignment; judge correctly classified refusals as clean. Layered defense here is the model's alignment, not the judge.
  - neuralchemy encoding-class (base64, ROT13, leet-speak, Unicode-mathematical-alphabet variants of "ignore previous instructions"): judge flagged 1/8 plus 1 parse error. Agent treated encoded payloads as cipher-decoding puzzles or code-evaluation tasks rather than recognizing them as live instructions. Defense for that class is agent's failure to parse the obfuscated directive in the first place.
  - Three-class refinement: layered defense has different mechanisms across attack classes (judge / alignment / parse failure). More nuanced than a single catch rate.
  - Artifacts: `results/defense_b_sneak_preview.md`, `results/defense_b_neuralchemy_jailbreak_preview.md`, `results/defense_b_neuralchemy_encoding_preview.md`, plus CSVs.
- **Judge sensitivity check** (Claude Sonnet 4.6 vs GPT-4o, deepset 8): Claude 4/8, GPT-4o 2/8, agreement 6/8. Judge call somewhat model-family-dependent at the minimum-rubric stage. Validates the need for the 150-row human gold subset + Cohen's kappa work scheduled before May 11. Artifact: `results/defense_b_judge_sensitivity_deepset.md`.
- **Meta Prompt Guard 2 access granted** (2026-05-08, mid-session). Deepset run complete: F1 0.41, AUC 0.95, recall 0.26 (more conservative than DeBERTa's 0.43). Within-Defense-A confirmation that the deepset gap is structural, not model-specific. Neuralchemy + SPML runs in progress as of state-doc update. Wrapper at `src/defense_a/prompt_guard.py`, script at `scripts/run_prompt_guard_all_datasets.py`.
- **Score distribution contrast**: `results/figures/defense_a_score_distributions.png` is now a three-panel figure (deepset / neuralchemy / SPML) showing the bimodality contrast. deepset 40.9% at 0.000 vs neuralchemy 6.8% vs SPML even lower. Visual smoking gun for cross-dataset variance.
- **Confusion-matrix grid**: `results/figures/defense_a_confusion_grid.png`, single 1x3 panel for the three datasets. Shows SPML's higher false-alarm rate (92 FP) against its near-perfect recall.
- **Label audit sample drawn**: `results/label_audit_sample.csv`, 200 stratified rows (67 deepset / 67 neuralchemy / 66 SPML, ~50/50 SAFE/INJECTION within each), seed 42. Empty `audit_label`, `ambiguous`, `notes` columns ready for Boga to fill in against `reports/operational_definitions.md`.
- **API smoke tests passed**: Groq Llama 3.3 70B, Anthropic Claude Sonnet 4.6, OpenAI GPT-4o (after $10 credit top-up). Script: `scripts/smoke_test_apis.py`. Total spend across all today's API work: ~$0.20.
- **Operational definitions document**: `reports/operational_definitions.md` v1.1, 18 worked examples verified against actual neuralchemy data. Dual decision trees, H1-H5 hijack categories, APA 7 references. Pre-audit draft.
- **Permissions**: `.claude/settings.local.json` updated with prefix-locked allowlist for Write/Edit/NotebookEdit and specific Bash patterns so background agents can run without permission prompts. Both relative and absolute Windows paths covered.
- **Plan reconciliation**: `_project_notes/capstone_plan.md` checkboxes synced with actual state.
- **Env**: registered `.venv` as Jupyter kernel name `capstone`. Added `sentencepiece` and `protobuf` to `pyproject.toml`. README + src/README updated to reflect uv `--extra api` setup and which modules are implemented vs planned.
- **Repo on GitHub**: four commits pushed today covering pipeline scaffolding, Defense A pilot, Defense B sneak previews, methodology + project notes.

Earlier (2026-04-21 to 2026-04-24): plan v2 with business decision framework, external LLM reviews (Kimi, Qwen, DeepSeek) incorporated, Eduardo meeting on 2026-04-24, `_local/` folder created, uv migration, contamination check.

## What's next

See [capstone_plan.md](./capstone_plan.md) Phase 0 checklist.

High-priority (most Phase 0 setup is done; remaining items are substantive):
- 200-row label audit against the operational definitions doc (sample already drawn at `results/label_audit_sample.csv`, ~5-6 hrs of human labeling time)
- Build frozen ~4,546-row evaluation set with stratification (~4 hrs)
- Wait for Prompt Guard 2 inference on neuralchemy + SPML to complete; then rebuild cross-dataset figure with both classifiers side by side
- Hardening: add `BadRequestError` handling to `src/defense_b/judge.py` before scaling
- Threshold sweep + bootstrap CIs on Defense A on the frozen eval set
- Defense B at full scale (May 5-11 week, after judge validation)
- Interim report due May 11

## Post-meeting (2026-05-08) considerations

- **Defense B judge cost optimization**: Claude Haiku 4.5 is roughly 5x cheaper than Sonnet 4.6 ($1/$5 per 1M input/output for Haiku 4.5 vs ~$3/$15 for Sonnet 4.6, approximate). For the full ~4,546-row eval set the projected $500-$800 budget is dominated by Sonnet judging. Worth testing Haiku 4.5 as the primary judge on a 100-row subsample to compare verdicts against Sonnet; if Cohen's kappa is high enough (>0.8), Haiku could be the production judge with Sonnet kept as the sensitivity layer. Decide before the full Defense B run, raise with Eduardo if scope changes.
- **Defense B judge wrapper hardening**: add `BadRequestError` handling to `src/defense_b/judge.py` so individual content-policy-blocked judgments are logged as `judge_blocked: true` and don't crash long runs. Low effort, do before scaling.

## Resuming work

If you are a fresh Claude session or picking this up after a gap:
1. Read this file (you are here).
2. Open [capstone_plan.md](./capstone_plan.md) to see the phase checklist and next unchecked items.
3. Consult [capstone_methodology_decisions.md](./capstone_methodology_decisions.md) to understand why a choice was made.
4. [implementation_plan_summary_v2.md](./implementation_plan_summary_v2.md) is the consolidated external-facing plan shared with Eduardo.
5. Historical context lives in `archive/`; local-only files (reviews, signed docs, PDFs) live in `_local/` and are gitignored.
