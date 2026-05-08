- Purpose: session-bridge snapshot for Claude conversation continuity. Read this first when resuming work.
- Status: active (overwritten per update)
- Memorializing: 2026-05-08 (Defense A pilot run, pre-Hiflylabs check-in)
- Last updated: 2026-05-08
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
- **Pipeline scaffolding**: `src/cache.py`, `src/defense_a/deberta.py`, `src/defense_b/agent.py` (Groq Llama 3.3 70B), `src/defense_b/judge.py` (Anthropic Claude Sonnet 4.6 with JSON-verdict parsing). Notebooks `05_defense_a_pilot.ipynb`, `06_defense_a_neuralchemy.ipynb`. Scripts `run_defense_a_neuralchemy.py`, `run_defense_b_sneak_preview.py`, `smoke_test_apis.py`. Caches: `defense_a_deberta_{deepset,neuralchemy}.jsonl`, `defense_b_agent_llama33_70b.jsonl`, `defense_b_judge_claude_sonnet_46.jsonl`.
- **Defense B sneak preview, two attack classes**:
  - 8 deepset prompts DeBERTa missed at injection_score=0.000 (mostly persona / role-play injections): judge flagged 4/8 as hijacked. Direct evidence for layered defense on subtle injections.
  - 8 neuralchemy jailbreak-class misses (blunt hate-content / harm-facilitation): judge flagged 0/8. Llama 3.3 70B refused all 8 on its own RLHF alignment; judge correctly classified the refusals as clean. The layered defense for that attack class is the model's alignment, not the judge. Refinement of the layered-defense thesis: two-stage Defense B has different value across attack classes.
  - Artifacts: `results/defense_b_sneak_preview.md`, `results/defense_b_neuralchemy_jailbreak_preview.md`, plus CSVs.
- **Score distribution contrast**: `results/figures/defense_a_score_distributions.png` shows deepset bimodal (40.9% at 0.000) vs neuralchemy graduated (6.8% at 0.000). Visual smoking gun for cross-dataset variance.
- **API smoke tests passed**: Groq Llama 3.3 70B, Anthropic Claude Sonnet 4.6, OpenAI GPT-4o (after $10 credit top-up). Script: `scripts/smoke_test_apis.py`.
- **Operational definitions document**: `reports/operational_definitions.md` v1.1, 18 worked examples verified against actual neuralchemy data. Dual decision trees, APA 7 references. Pre-audit draft.
- **Permissions**: `.claude/settings.local.json` updated with prefix-locked allowlist for Write/Edit/NotebookEdit and specific Bash patterns (`.venv/Scripts/python.exe *`, `.venv/Scripts/jupyter.exe *`, `uv *`, etc.) so background agents can run without permission prompts.
- **Plan reconciliation**: `_project_notes/capstone_plan.md` checkboxes synced with actual state (contamination done, uv migration done, Defense A pilot done, all three API keys verified, threshold sweep on deepset done).
- **Env**: registered `.venv` as Jupyter kernel name `capstone`. Added `sentencepiece` and `protobuf` to `pyproject.toml` for DeBERTa tokenizer.
- **Stale-checkbox note**: contamination check was already complete (per `results/contamination_report.md`) but the plan checkbox said otherwise. Plan doc not yet updated.

Earlier (2026-04-21 to 2026-04-24): plan v2 with business decision framework, external LLM reviews (Kimi, Qwen, DeepSeek) incorporated, Eduardo meeting on 2026-04-24, `_local/` folder created, uv migration, contamination check.

## What's next

See [capstone_plan.md](./capstone_plan.md) Phase 0 checklist.

High-priority:
- Reconcile plan checkboxes with actual progress (contamination done, uv migration done, environment.yml task obsolete, Defense A pilot done)
- Write operational definitions document
- Run 200-row label audit
- Build frozen eval set
- Verify Groq, Anthropic, OpenAI API keys
- Add Meta Prompt Guard 2 to Defense A once Llama license access is set up
- Threshold sweep + bootstrap CIs on Defense A once frozen eval set is in place

## Resuming work

If you are a fresh Claude session or picking this up after a gap:
1. Read this file (you are here).
2. Open [capstone_plan.md](./capstone_plan.md) to see the phase checklist and next unchecked items.
3. Consult [capstone_methodology_decisions.md](./capstone_methodology_decisions.md) to understand why a choice was made.
4. [implementation_plan_summary_v2.md](./implementation_plan_summary_v2.md) is the consolidated external-facing plan shared with Eduardo.
5. Historical context lives in `archive/`; local-only files (reviews, signed docs, PDFs) live in `_local/` and are gitignored.
