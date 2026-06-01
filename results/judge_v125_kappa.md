# v1.21 vs v1.25 judge kappa on the 150-row audited gold subset

Cohen's kappa, human verdict (post-SPML-fix) vs judge verdict, binarised CLEAN/HIJACKED.
AMBIGUOUS verdicts counted as HIJACKED (matches �5.6 convention).

| Judge | Slice | v1.21 kappa | v1.25 kappa | Delta | n | n_hij | n_clean |
|---|---|---|---|---|---|---|---|
| Sonnet 4.6 | overall | 0.440 | 0.466 | +0.026 | 150 | 52 | 98 |
| Sonnet 4.6 | deepset | 0.557 | 0.411 | -0.146 | 59 | 20 | 39 |
| Sonnet 4.6 | neuralchemy | 0.089 | 0.361 | +0.272 | 41 | 6 | 35 |
| Sonnet 4.6 | spml | 0.643 | 0.528 | -0.115 | 50 | 26 | 24 |
| Haiku 4.5 | overall | 0.471 | 0.554 | +0.083 | 150 | 52 | 98 |
| Haiku 4.5 | deepset | 0.449 | 0.567 | +0.119 | 59 | 20 | 39 |
| Haiku 4.5 | neuralchemy | 0.258 | 0.388 | +0.130 | 41 | 6 | 35 |
| Haiku 4.5 | spml | 0.722 | 0.606 | -0.116 | 50 | 26 | 24 |
| GPT-4o-mini | overall | 0.422 | 0.403 | -0.019 | 150 | 52 | 98 |
| GPT-4o-mini | deepset | 0.326 | 0.449 | +0.123 | 59 | 20 | 39 |
| GPT-4o-mini | neuralchemy | 0.237 | 0.331 | +0.095 | 41 | 6 | 35 |
| GPT-4o-mini | spml | 0.762 | 0.490 | -0.272 | 50 | 26 | 24 |
| Opus 4.7 | overall | n/a | 0.550 | n/a | 150 | 52 | 98 |
| Opus 4.7 | deepset | n/a | 0.465 | n/a | 59 | 20 | 39 |
| Opus 4.7 | neuralchemy | n/a | 0.388 | n/a | 41 | 6 | 35 |
| Opus 4.7 | spml | n/a | 0.683 | n/a | 50 | 26 | 24 |

## Supplementary: kappa under four AMBIGUOUS-handling conventions

Primary convention (AMBIG=HIJACKED) matches §5.6 reporting and §7.6 fail-closed deployment semantic.
Other conventions reported for methodology transparency.

| Judge | Rubric | AMBIG=HIJACKED | AMBIG=CLEAN | 3-class | Drop AMBIG (n) |
|---|---|---|---|---|---|
| Sonnet 4.6 | v1.21 | 0.440 | 0.443 | 0.404 | 0.533 (n=127) |
| Sonnet 4.6 | v1.25 | 0.466 | 0.404 | 0.397 | 0.533 (n=126) |
| Haiku 4.5 | v1.21 | 0.471 | 0.429 | 0.435 | 0.461 (n=145) |
| Haiku 4.5 | v1.25 | 0.554 | 0.497 | 0.507 | 0.541 (n=145) |
| GPT-4o-mini | v1.21 | 0.422 | 0.391 | 0.390 | 0.422 (n=144) |
| GPT-4o-mini | v1.25 | 0.403 | 0.380 | 0.378 | 0.403 (n=145) |
| Opus 4.7 | v1.25 | 0.550 | 0.461 | 0.481 | 0.543 (n=137) |
