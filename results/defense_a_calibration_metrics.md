# Defense A calibration analysis (DeBERTa, full eval set)

- Date: 2026-05-27
- Method: post-hoc temperature scaling per Guo et al. (2017), single-parameter T fit by minimising NLL on a stratified 10% calibration fold
- Input: `results/defense_a_full_eval_set.csv` (4546 rows after dropping NaN)
- Calibration fold: 455 rows (stratified by dataset, seed 42)
- Test fold: 4091 rows (the calibration metrics below are computed on this fold)
- ECE caveat: per Chidambaram et al. (2024), binning-based ECE has known pathologies; the directional comparison pre vs post is reliable; the absolute numbers should be read with the standard ECE caveats in mind

## Fitted temperature

`T = 4.7028` (T > 1 means original model was overconfident; T < 1 means underconfident)

## Overall ECE pre vs post temperature scaling

| Scope | n | ECE pre | ECE post | Δ |
|---|---|---|---|---|
| Overall test fold | 4091 | 0.0835 | 0.0372 | -0.0464 |
| deepset | 491 | 0.2203 | 0.1658 | -0.0545 |
| neuralchemy | 1800 | 0.0933 | 0.0887 | -0.0046 |
| spml | 1800 | 0.0457 | 0.0775 | +0.0317 |

## Per-bin diagnostics (test fold, post-calibration)

| Bin range | n | Mean confidence | Empirical accuracy | Contribution to ECE |
|---|---|---|---|---|
| [0.00, 0.10] | 1739 | 0.0546 | 0.0690 | 0.0061 |
| [0.10, 0.20] | 131 | 0.1433 | 0.2824 | 0.0045 |
| [0.20, 0.30] | 114 | 0.2477 | 0.5088 | 0.0073 |
| [0.30, 0.40] | 68 | 0.3509 | 0.6029 | 0.0042 |
| [0.40, 0.50] | 41 | 0.4485 | 0.4634 | 0.0001 |
| [0.50, 0.60] | 39 | 0.5457 | 0.5897 | 0.0004 |
| [0.60, 0.70] | 54 | 0.6571 | 0.7407 | 0.0011 |
| [0.70, 0.80] | 134 | 0.7564 | 0.7687 | 0.0004 |
| [0.80, 0.90] | 123 | 0.8476 | 0.8455 | 0.0001 |
| [0.90, 1.00] | 1648 | 0.9580 | 0.9903 | 0.0130 |

## Interpretation

DeBERTa's pre-calibration injection-class probabilities show ECE = 0.0835 on the test fold. Post-temperature scaling with T = 4.7028, ECE = 0.0372, a change of -0.0464.

The fitted T > 1 indicates the model was systematically overconfident; temperature scaling softens the distribution toward more honest uncertainty.

Implication for the §5.7b coverage/accuracy curve: the curve was nearly flat because DeBERTa's pre-calibration score distribution was bimodal at 0 and 1. The calibrated scores (post temperature scaling) should produce a more graduated distribution and a more operationally useful coverage curve. The reliability diagram at `results/figures/defense_a_calibration.png` visualises pre vs post.