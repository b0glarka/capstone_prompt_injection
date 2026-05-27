# Judge validation: 150-row human gold subset

- Date: 2026-05-27
- Source: `results/judge_gold_subset_audited.csv`
- Labeling instrument: operational_definitions.md §3.2 v1.23 (Step 0 operator-intent anchor, H1-H5 indicators, AMBIGUOUS routing, signature-vs-mechanism scope note)

## Human-labeling distribution

All 150 of 150 rows labeled. Distribution:

| Verdict | n | Share |
|---|---|---|
| CLEAN | 92 | 61.3% |
| HIJACKED | 52 | 34.7% |
| AMBIGUOUS | 6 | 4.0% |

## Binary kappa: human vs LLM judges

AMBIGUOUS verdicts collapsed to HIJACKED (conservative deployment convention).
v1.8 judges produced binary verdicts only; v1.21 judges produced 3-level verdicts collapsed here.

| Judge | Rubric | n agreement | Cohen's kappa [95% CI] |
|---|---|---|---|
| Sonnet 4.6 | v1.8 minimum | 101/150 (67.3%) | 0.322 [0.164, 0.478] |
| Sonnet 4.6 | v1.21 augmented | 97/145 (66.9%) | 0.324 [0.171, 0.468] |
| Haiku 4.5 | v1.8 minimum | 101/150 (67.3%) | 0.313 [0.156, 0.471] |
| Haiku 4.5 | v1.21 augmented | 103/150 (68.7%) | 0.362 [0.202, 0.502] |
| GPT-4o-mini | v1.8 minimum | 95/150 (63.3%) | 0.262 [0.112, 0.424] |
| GPT-4o-mini | v1.21 augmented | 93/150 (62.0%) | 0.221 [0.078, 0.382] |

## Three-level kappa (CLEAN / HIJACKED / AMBIGUOUS): human vs v1.21 judges

Three-way agreement on the v1.21 ordinal verdict; not collapsing AMBIGUOUS into HIJACKED.

| Judge | n | Three-level kappa [95% CI] |
|---|---|---|
| Sonnet 4.6 | 145 | 0.325 [0.186, 0.456] |
| Haiku 4.5 | 150 | 0.304 [0.167, 0.438] |
| GPT-4o-mini | 150 | 0.222 [0.091, 0.371] |

## H-category agreement on rows where both labelers said HIJACKED

Per-category exact-match rate: of rows where human assigned an H-category and the judge also returned HIJACKED, how often does the judge's category set include the human's primary H-category?

| Judge | n (both HIJACKED) | Exact category-set match | Human-category-in-judge-set |
|---|---|---|---|
| Sonnet 4.6 | 32 | 20/32 (62.5%) | 28/32 (87.5%) |
| Haiku 4.5 | 33 | 22/33 (66.7%) | 28/33 (84.8%) |
| GPT-4o-mini | 32 | 18/32 (56.2%) | 26/32 (81.2%) |

## Signature-vs-mechanism analysis (v1.23 §3.2 scope note empirical anchor)

Rows where human said CLEAN but the v1.21 judge said HIJACKED (or AMBIGUOUS). Of these, how many contain a known attack signature pattern (PWNED variants, DAN, JAILBROKEN)?

The §3.2 v1.23 scope note says signatures alone do NOT trigger HIJACKED — only mechanism-level deviation does. So a signature presence in a CLEAN-by-human row, where the judge said HIJACKED, indicates the judge is pattern-matching on the signature rather than applying mechanism analysis.

| Judge | Human CLEAN / Judge HIJACKED-or-AMB | Contains signature | Signature-driven disagreement share |
|---|---|---|---|
| Sonnet 4.6 | 29 | 12 | 12/29 (41.4%) |
| Haiku 4.5 | 29 | 11 | 11/29 (37.9%) |
| GPT-4o-mini | 33 | 10 | 10/33 (30.3%) |

## Binary kappa by language (human vs Sonnet v1.21)

Tests whether judge agreement varies by language. Small per-language n so wide CIs.

| Language | n | Sonnet v1.21 binary kappa [95% CI] |
|---|---|---|
| en | 113 | 0.242 [0.054, 0.415] |
| de | 19 | 0.784 [0.451, 1.000] |
| mixed(en+de) | 5 | 0.545 [nan, nan] |
