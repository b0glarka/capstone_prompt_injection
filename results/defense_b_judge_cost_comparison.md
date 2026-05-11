# Judge cost-vs-accuracy sweep (Defense B 500-row pilot)

- Run date: 2026-05-11
- Sample: same 500 (prompt, agent response) pairs as the formal Sonnet pilot
- Judges: Claude Sonnet 4.6 (primary), Claude Haiku 4.5 (5x cheaper), GPT-4o-mini (~20x cheaper)
- Same minimum-rubric judge prompt, temperature 0, max_tokens 400 for all three

## Headline

At n = 497 pairs where all three judges produced a verdict (of 500 total), pairwise agreement and Cohen's kappa:

| Pair | Agreement | Cohen's kappa |
|---|---|---|
| Sonnet 4.6 vs Haiku 4.5 | 0.934 | 0.799 |
| Sonnet 4.6 vs GPT-4o-mini | 0.899 | 0.720 |
| Haiku 4.5 vs GPT-4o-mini | 0.913 | 0.757 |

All three judges agree on **0.873** of pairs.

## Cost per judge (500 rows)

| Judge | Input tokens | Output tokens | Cost (USD) | Implied cost at 4,546 rows |
|---|---|---|---|---|
| Sonnet 4.6 | 207,627 | 21,245 | $0.9416 | $8.56 |
| Haiku 4.5 | 207,127 | 30,039 | $0.3573 | $3.25 |
| GPT-4o-mini | 185,447 | 16,801 | $0.0379 | $0.34 |

## Per-dataset agreement

- deepset (n=167): Sonnet/Haiku agreement 0.940, Sonnet/GPT-mini 0.928, all three 0.904
- neuralchemy (n=166): Sonnet/Haiku agreement 0.964, Sonnet/GPT-mini 0.898, all three 0.867
- spml (n=164): Sonnet/Haiku agreement 0.896, Sonnet/GPT-mini 0.872, all three 0.848

## Reading

Cohen's kappa above 0.8 is conventionally read as strong agreement; 0.6 to 0.8 substantial; 0.4 to 0.6 moderate. Use those thresholds to decide whether the cheaper judge can replace Sonnet at scale. Pair the agreement number with the cost-extrapolation column: a judge that's 20x cheaper with kappa above 0.8 is a clear win for the production run.

## Caveats

Same minimum-rubric judge prompt for all three. Single agent model (Llama 3.3 70B). Pilot scale, not full eval set. Cohen's kappa is sensitive to class balance; values reported here are unadjusted. Judge-blocked rows (content-policy refusals) are excluded from the agreement denominator. Production rubric iteration is a separate Phase 2 step and may shift these numbers.