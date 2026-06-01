# Aggregate metrics under v1.21 §3.2 rubric

- Date: 2026-05-27
- Source CSVs: re-judged 2026-05-26 via `src/defense_b/rejudge_v121.py`
- v1.8 baseline: `_local/baseline_v1.8_judge/` (preserved for comparison)
- AMBIGUOUS handling: counted as HIJACKED for hijack-rate computation (conservative); ambiguous rate reported separately

## Defense B pilot, Sonnet 4.6 (n=500)

On 251 injection-class rows in the pilot:

| Scope | n | v1.8 hijack rate | v1.21 hijack rate (AMB=HIJACKED) | v1.21 AMBIGUOUS rate |
|---|---|---|---|---|
| deepset (injection rows) | 84 | 0.4881 | 0.4881 | 0.0714 |
| neuralchemy (injection rows) | 84 | 0.5000 | 0.5833 | 0.0595 |
| spml (injection rows) | 83 | 0.2651 | 0.5301 | 0.0964 |
| **All injection rows** | **251** | **0.4183** | **0.5339** | **0.0757** |

Paired McNemar v1.8 vs v1.21 (on injection rows, HIJACKED = correct): b=11, c=40, p=5.704e-05

## Cheap-judge sweep: cross-judge kappa under v1.21 (n=500)

| Pair | n | v1.8 agreement | v1.8 kappa | v1.21 agreement | v1.21 kappa |
|---|---|---|---|---|---|
| Sonnet 4.6 vs Haiku 4.5 | 500 | 0.930 | 0.788 | 0.900 | 0.752 |
| Sonnet 4.6 vs GPT-4o-mini | 500 | 0.894 | 0.706 | 0.850 | 0.644 |
| Haiku 4.5 vs GPT-4o-mini | 500 | 0.912 | 0.755 | 0.890 | 0.744 |

Three-judge agreement: v1.8 = 0.868, v1.21 = 0.820

## Defense C combined (n=500, pilot)

| Defense | F1 (v1.8) | F1 (v1.21) | Precision (v1.21) | Recall (v1.21) | Acc (v1.21) |
|---|---|---|---|---|---|
| Defense A (DeBERTa) | 0.849 | 0.849 (unchanged; A is independent of judge) | 0.960 | 0.761 | 0.864 |
| Defense B (Sonnet judge) | 0.590 | 0.696 | 1.000 | 0.534 | 0.766 |
| Defense C (A OR B) | 0.912 | 0.909 | 0.964 | 0.861 | 0.914 |

Defense C v1.21 bootstrap 95% CIs: F1 = 0.909 [0.879, 0.934], precision = 0.964 [0.935, 0.987], recall = 0.861 [0.818, 0.898]

Paired McNemar Defense A vs Defense C (v1.21): b=0, c=25, p=5.96e-08

## BIPIA email-QA under v1.21 (n=800, 750 attacks + 50 controls)

On 750 attack rows and 50 clean controls:

| Defense | v1.8 attack success | v1.21 attack success | v1.8 FAR | v1.21 FAR |
|---|---|---|---|---|
| Defense A: DeBERTa (query only) | 1.0000 | 1.0000 (A unchanged) | 0.0000 | 0.0000 |
| Defense A: DeBERTa (full prompt) | 0.6560 | 0.6560 (A unchanged) | 0.3800 | 0.3800 |
| Defense A: PG2 (full prompt) | 0.9773 | 0.9773 (A unchanged) | 0.0000 | 0.0000 |
| Defense B: Sonnet judge | 0.7813 | 0.6693 | 0.0000 | 0.0000 |
| Defense C: DeBERTa (full) + judge | 0.5173 | 0.4440 | 0.3800 | 0.3800 |

v1.21 AMBIGUOUS rate: 0.0387 on attacks, 0.0000 on controls.

### BIPIA per-category attack success (Defense C under v1.21)

| Category | n | v1.8 Defense C | v1.21 Defense C |
|---|---|---|---|
| Base Encoding | 50 | 0.50 | 0.26 |
| Business Intelligence | 50 | 0.68 | 0.68 |
| Conversational Agent | 50 | 0.64 | 0.64 |
| Emoji Substitution | 50 | 0.64 | 0.64 |
| Entertainment | 50 | 0.34 | 0.28 |
| Information Dissemination | 50 | 0.34 | 0.18 |
| Language Translation | 50 | 0.64 | 0.60 |
| Marketing & Advertising | 50 | 0.46 | 0.42 |
| Misinformation & Propaganda | 50 | 0.14 | 0.10 |
| Research Assistance | 50 | 0.66 | 0.66 |
| Reverse Text | 50 | 0.46 | 0.42 |
| Scams & Fraud | 50 | 0.36 | 0.26 |
| Sentiment Analysis | 50 | 0.70 | 0.70 |
| Substitution Ciphers | 50 | 0.46 | 0.08 |
| Task Automation | 50 | 0.74 | 0.74 |

## GPT-4o judge sensitivity, deepset role-play (n=8)

Of 8 cases:

- v1.8: Claude flagged 4/8; GPT-4o flagged 2/8; agreement 6/8.
- v1.21: Claude flagged 2/8; GPT-4o flagged 6/8; agreement 2/8.
