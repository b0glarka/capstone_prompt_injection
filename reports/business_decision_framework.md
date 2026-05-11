# Business Decision Framework: Prompt Injection Defense Deployment

This document translates the statistical evaluation of input-side (Defense A) and output-side (Defense B) prompt-injection defenses into deployment recommendations. It is the practitioner-facing artifact of the capstone, anchored on the empirical results in `results/defense_a_full_metrics.csv` (n = 4546, injection prevalence 0.530) and the Defense B sneak-preview data in `results/defense_b_*_preview.md`.


The framework has four layers. Layer 1 names the categories of harm a deployment must reason about. Layer 2 reduces those categories to a single cost-weighted score that varies with the deployment context. Layer 3 is a per-defense decision matrix. Layer 4 maps representative enterprise scenarios to the defense configuration that minimizes expected cost in that scenario.


## Layer 1: Business harm taxonomy

Prompt-injection failures cause two error types with very different consequences:

**Missed attack (false negative)**: an injection succeeds, the defense does not flag it, and the agent's output reflects the attacker's goal. Possible business consequences:

- Financial. Unauthorized transactions, data exfiltration to attacker-controlled destinations, leak of pricing or contract terms.
- Reputational. Brand damage from offensive or off-policy agent outputs, especially if surfaced publicly (screenshot leaks, journalist test cases).
- Operational. The attacker uses the agent to bypass workflow controls (e.g., approval routing) or to plant information that downstream automation acts on without re-checking.
- Compliance. Regulatory exposure under GDPR, sector-specific obligations (HIPAA, PCI-DSS), or AI-system safety regulations now appearing in EU and other jurisdictions.

**False alarm (false positive)**: a benign user request is wrongly flagged as an injection, and either blocked, deferred to a human reviewer, or downgraded to a more restricted response.

- Operational. Each false alarm consumes review time and adds latency. At scale (millions of interactions), even a 1% false-positive rate translates into thousands of unnecessary escalations.
- User-experience. Repeated false alarms erode trust in the agent and push legitimate users to workarounds outside the controlled environment.
- Revenue. For customer-facing deployments, blocked legitimate requests are abandoned interactions, which is a direct conversion cost.


## Layer 2: Cost-weighted decision scoring

Single-number metrics (accuracy, F1, AUC) do not select a deployment threshold because they do not encode the relative cost of false negatives vs false positives. The framework reduces this to a single expected-cost-per-prompt expression and varies it across plausible cost ratios:

```
E[cost per prompt] = P(injection) * FNR * cost_per_missed_attack
                   + P(benign)    * FPR * cost_per_false_alarm
```

Normalizing on `cost_per_false_alarm = 1` and varying `cost_per_missed_attack` across {10, 100, 1000}:

- `10x`   : false alarms are nearly as costly as missed attacks. Representative of consumer chat applications where user friction is high-impact and the underlying harm of a missed attack is bounded (e.g., a missed jailbreak that makes the chatbot say something embarrassing).
- `100x`  : missed attacks are substantially worse. Representative of business-internal tools with moderate stakes (e.g., a customer-support agent with access to billing data).
- `1000x` : a missed attack is catastrophically worse than a false alarm. Representative of agents with access to high-stakes tools (financial transactions, code execution, sensitive data systems). This is closest to the Hiflylabs deployment context described in the PID.

**Per-defense expected cost at each ratio** (lower is better; injection prevalence 0.530, n = 4546):

| Defense | TPR (recall) | FPR | E[cost] @ 10x | E[cost] @ 100x | E[cost] @ 1000x |
|---|---|---|---|---|---|

| DeBERTa (ProtectAI v2) | 0.8747 | 0.0524 | 0.6890 | 6.6678 | 66.4567 |

| Prompt Guard 2 (Meta) | 0.5033 | 0.0094 | 2.6375 | 26.3352 | 263.3128 |

| Ensemble OR-gate | 0.8867 | 0.0557 | 0.6267 | 6.0315 | 60.0790 |

| Ensemble AND-gate | 0.4913 | 0.0061 | 2.6997 | 26.9716 | 269.6905 |


Reading: the cost-minimizing defense changes with the assumed cost ratio. At 10x, **Ensemble OR-gate** minimizes expected cost. At 100x, **Ensemble OR-gate** minimizes expected cost. At 1000x, **Ensemble OR-gate** minimizes expected cost.

The qualitative pattern: the more catastrophic a missed attack is judged to be, the more aggressive the deployment should be in flagging (higher TPR, accepting more false alarms). Conservative classifiers (high precision, low recall) optimize for the low cost-ratio regime; sensitive configurations (broader flagging, lower threshold or OR-gated ensembles) optimize for the high cost-ratio regime.


## Layer 3: Decision matrix (per defense)

Practitioner-facing summary across the dimensions that determine deployment fit. Latency and cost-per-1K-prompts columns are estimates from observed pilot data where available; Defense B numbers are preliminary from the 24-case sneak preview.

| Defense | Security (TPR) | Usability (legit pass) | Latency profile | Cost per 1K prompts | Best for |
|---|---|---|---|---|---|
| DeBERTa (ProtectAI v2)        | 0.875 | 0.973 | <100ms on CPU, batched | local inference, ~$0 marginal | broad first-line filter where false alarms are visible to users |
| Prompt Guard 2 (Meta)         | 0.503 | 0.992 | <100ms on CPU, batched | local inference, ~$0 marginal | extremely conservative deployments where false alarms are unacceptable |
| Ensemble OR-gate              | 0.887 | 0.969 | <200ms on CPU (two inferences) | local inference, ~$0 marginal | applications wanting the slight recall lift of two classifiers combined |
| Ensemble AND-gate             | 0.491 | 0.998 | <200ms on CPU (two inferences) | local inference, ~$0 marginal | low-stakes deployments where conservative blocking is preferred |
| Defense B (Llama+Claude judge) | 0.418 (pilot, injection rows) | 1.000 (pilot, no FPs on benign rows at minimum-rubric stage) | seconds-per-call (LLM agent + LLM judge) | API: ~$0.002 per prompt (Sonnet judge, actual pilot rate); ~$0.0007 (Haiku 4.5) or ~$0.00008 (GPT-4o-mini) after the cost-comparison sweep validated kappa = 0.799 and 0.720 respectively | applications already running agents where the second-stage judge is the only practical defense, especially against subtle injections that input classifiers miss |
| Defense C: A + B combined (pilot, n=500) | 0.865 (DeBERTa + Sonnet judge) | 0.964 (essentially identical to A alone; no precision cost on the pilot) | seconds-per-call (A first then B; on prompts A flags, B does not need to run) | API: ~$0.002 per prompt for the rows A passes (most of them) plus zero-marginal-cost A inference | high-stakes deployments where the input classifier removes obvious attacks and the judge handles the residual; F1 0.912 in the pilot, dominant over either component (paired McNemar p < 1e-6) |


## Layer 4: Scenario-based recommendations

Three representative enterprise scenarios with the defense configuration that minimizes expected cost in each context. The Hiflylabs deployment scenario described in the PID maps closest to the high-stakes case.

**Scenario A: Consumer-facing chatbot with no tool access**

- Threat profile: misuse and brand-damaging outputs; no path to financial or data harm beyond text content.
- Cost ratio: roughly 10x. False alarms hurt conversion; missed attacks are embarrassing but bounded.
- Recommended: **DeBERTa solo at default threshold**. F1 0.91, low FPR (2.7%), local-CPU inference. No Defense B needed; the cost of false alarms outweighs the marginal value of a second-stage judge for this risk profile.

**Scenario B: Business-internal agent with read-only access to systems**

- Threat profile: data exfiltration and policy violations are possible; tool calls are bounded to safe operations.
- Cost ratio: roughly 100x. Missed attacks have real consequences but containment is partial.
- Recommended: **DeBERTa ensemble (OR-gate with PG2) plus Defense B on flagged or borderline cases**. OR-gate gives a small recall lift on the hardest dataset (deepset). Defense B as second-stage handler of subtle injections that the classifier under-flags. Use Haiku 4.5 as the judge to keep cost per prompt under $0.001 (pending the cost-comparison sweep that confirms Haiku tracks Sonnet at scale).

**Scenario C: Autonomous agent with broad tool access (Hiflylabs PID context)**

- Threat profile: agent can execute, send, transact, or persist on the user's behalf. Missed attacks are catastrophic.
- Cost ratio: roughly 1000x. False alarms are inconvenient but tolerable; missed attacks must be minimized.
- Recommended: Defense C combined pipeline (Defense A as input gate, then Defense B on Defense A's non-blocks). Empirically validated at pilot scale: F1 = 0.912 vs 0.849 for Defense A alone and 0.590 for Defense B alone, with paired McNemar p < 1e-6 against each component. Defense C lifts recall from 0.761 (Defense A alone) to 0.865 (Defense C) while preserving Defense A's precision of 0.96 (the Sonnet judge contributed zero false positives on the 500-row pilot at the minimum-rubric stage). Use Sonnet 4.6 as the primary judge for maximum second-stage detection accuracy; the marginal cost (~$0.002 per prompt) is bounded by the volume of agent actions, which is typically much smaller than raw chatbot traffic. The cost-comparison sweep validated that Haiku 4.5 tracks Sonnet at kappa = 0.799, so Haiku is a viable cost-optimization fallback at 2.6x lower per-row cost if the deployment is highly volume-constrained.

Across all three scenarios, two cross-cutting recommendations hold:

- **Pre-deploy human gold-set validation of the judge** before relying on Defense B in production. The sneak-preview judge sensitivity check (Claude vs GPT-4o agreed on 6 of 8 cases) demonstrates that judge calls are sensitive to model family and rubric design.
- **Monitor per-attack-subcategory recall in production** if the deployment has logging infrastructure. The neuralchemy subcategory analysis shows Defense A blind spots (jailbreak 0.55, encoding 0.67 on DeBERTa, both <0.10 on PG2) that an attacker can deliberately target. A defense's overall F1 is not informative if real-world traffic concentrates on the subcategories where the defense underperforms.


## Limitations and assumptions

- Cost ratios above are illustrative. A real deployment derives them from incident-cost data the deploying organization owns.
- Expected-cost calculations assume independence between false-negative and false-positive events, which is realistic at the population level but not at the user-session level (a frustrated user is more likely to try injections after a false alarm).
- Defense B numbers are sneak-preview only (24 cases). The 500-row formal pilot, when complete, will replace those placeholders. Cost-extrapolation in this document uses pilot-scale token counts.
- The eval-set distribution (deepset + neuralchemy + SPML) may not match any specific enterprise's traffic distribution. Per-dataset metrics are reported so a deploying organization can pick the dataset whose distribution is closest to their use case.
