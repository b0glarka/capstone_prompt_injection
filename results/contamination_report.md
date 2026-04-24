# Classifier Contamination Report

*Run date: 2026-04-24. HuggingFace dataset IDs are stable, but datasets can be updated or removed by their owners; re-running at a later date may produce different results.*

Exact-string-match check between our three evaluation datasets and the *named* training sources of ProtectAI DeBERTa v3 base v2, plus the V1 model's named sources as a precautionary second tier. Meta Prompt Guard 2 is not checked (no source enumeration).

Totals are counted as UNIQUE prompts matched in at least one source within a tier (a prompt matched in multiple sources counts once per tier).

## Tier 1: V2 named sources (definitive)

Six of the seven V2-named datasets checked. Harelix is omitted because the original was removed from HuggingFace and no pure-recovery substitute was found (see limitations below).

| source                                   |   training_prompts |   deepset_matches |   neuralchemy_matches |   spml_matches |
|:-----------------------------------------|-------------------:|------------------:|----------------------:|---------------:|
| VMware/open-instruct                     |             118015 |                 2 |                     4 |              3 |
| alespalla/chatbot_instruction_prompts    |             296334 |                 2 |                    11 |              5 |
| HuggingFaceH4/grok-conversation-harmless |              17155 |                 0 |                     0 |              0 |
| OpenSafetyLab/Salad-Data                 |              21318 |                 0 |                     6 |              0 |
| jackhhao/jailbreak-classification        |               1289 |                 0 |                     0 |              0 |
| natolambert/xstest-v2-copy               |                451 |                 0 |                    69 |              0 |

**Tier 1 totals (unique prompts matched)**:

- **deepset**: 3 of 546 prompts matched (0.55%)
- **neuralchemy**: 86 of 4391 prompts matched (1.96%)
- **spml**: 8 of 15914 prompts matched (0.05%)

## Tier 2: V1 named sources (precautionary)

Three datasets named on the V1 model card. V2 was retrained and its card does not enumerate V1's sources, so these may or may not have been inherited. Reported separately; treat as conservative upper-bound contamination.

| source                       |   training_prompts |   deepset_matches |   neuralchemy_matches |   spml_matches |
|:-----------------------------|-------------------:|------------------:|----------------------:|---------------:|
| HuggingFaceH4/ultrachat_200k |             515292 |                 0 |                     1 |              8 |
| fka/prompts.chat             |               1680 |                 3 |                     0 |              0 |
| HuggingFaceH4/no_robots      |               9999 |                 0 |                     1 |              0 |

**Tier 2 totals (unique prompts matched)**:

- **deepset**: 3 of 546 prompts matched (0.55%)
- **neuralchemy**: 1 of 4391 prompts matched (0.02%)
- **spml**: 8 of 15914 prompts matched (0.05%)

## Unverifiable contamination risks (documented limitations)

### Harelix (original removed from HuggingFace)

`Harelix/Prompt-Injection-Mixed-Techniques-2024` is named on ProtectAI's V2 card but has been removed from HuggingFace. The [ShieldLM README](https://huggingface.co/datasets/Abdennebi/shieldlm-prompt-injection/blob/main/README.md) points at `ahsanayub/malicious-prompts` as a recovery source, but that dataset is a large aggregation of many prompt-injection datasets (including our deepset and SPML eval sets themselves), so overlap counts from it are uninterpretable for this check. Contamination from the original Harelix cannot be verified.

### ProtectAI V2 unnamed sources

15 additional V2 training datasets are disclosed by license category only (8 MIT, 1 CC0 1.0, 6 no-license/public-domain). ProtectAI's maintainer confirmed in an April 2024 [HuggingFace Discussion](https://huggingface.co/protectai/deberta-v3-base-prompt-injection-v2/discussions/1) that training-data details are kept partly confidential by design, and a follow-up asking to open-source the training data went unanswered.

### Meta Prompt Guard 2

The Meta Llama Prompt Guard 2 86M model card states only: 'a mix of open-source datasets reflecting benign data from the web, user prompts and instructions for LLMs, and malicious prompt injection and jailbreaking datasets... plus synthetic injections and red-teaming material.' No specific sources enumerated; no research paper expands on this.

## Handling decision

(Fill in after reviewing the tables above.) Options:
- Remove overlapping rows (from tier 1 and/or tier 2) from the eval set
- Report contaminated vs clean metrics separately
- Accept and caveat in results
