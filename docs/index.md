---
layout: default
---

<p align="center">
  <img src="boga.jpg" alt="Boglarka Petruska" width="180" style="border-radius: 50%;">
</p>

<p align="center">Boglarka Petruska • MSc Business Analytics, Central European University, 2026</p>

<p align="center">🏆 Outstanding Capstone Project Award, CEU MSc Business Analytics 2026</p>

---

## What this is about

This is my MSc Business Analytics capstone project from Central European University. It received the program's Outstanding Capstone Project Award for the 2026 cohort.

The project is about defending AI agents from prompt injection. As companies start to deploy AI agents to help their employees with internal work like querying databases, summarising emails, or scheduling meetings, one of the many security concerns is that these agents can be tricked by someone hiding malicious instructions inside what looks like an ordinary user message or document the agent has to read. These hidden-instruction attacks are what the term 'prompt injection' refers to.

The project approaches the defense problem in roughly five stages. The first stage settles on a strict definition of what counts as a "hijacked" agent (one that pins the outcome to the agent's final answer to the user, so the metric reflects actual deployment behavior), surveys the small set of public benchmarks worth evaluating against, and shows why naive measurement on these benchmarks is unreliable: label noise, scope drift between datasets, and disagreement between human and model labellers all show up in the audit. The second stage evaluates two defense families on three of those benchmarks. The first family is an encoder classifier that screens user messages before the agent sees them (the candidates here are ProtectAI's DeBERTa-based detector and Meta's Prompt Guard 2). The second family is an LLM-as-judge that reads the agent's final output and decides whether the agent ended up doing what the attacker asked. The two families catch different failure modes, so the project treats them as complementary.

The third stage finds that the off-the-shelf classifiers score near the top on one benchmark and noticeably worse on the other two. The cross-dataset spread is large enough that picking a defense based on a single benchmark would mislead a deployer. A short LoRA fine-tune of the DeBERTa head on a balanced mix of the three benchmarks closes most of that gap and pulls the worst-case dataset back into a useful operating range, without overfitting to any one source.

The fourth stage takes the harder case of indirect prompt injection, where the malicious instruction is hidden inside an email body or a tool output that the agent has to read, rather than in the user's message. The empirical work here is structured as a four-iteration arc, because the first attempts failed in informative ways (label asymmetries, train/test contamination introduced by augmentation, brittle augmentation prompts), and writing those failures up is part of the contribution. The fourth iteration is the version that's worth treating as a deployment candidate.

The fifth stage, which is the part the sponsor cared most about, turns the empirical findings into a Business Decision Framework for deployers. It works through three reference scenarios (a customer-facing chatbot, an internal employee assistant, and an autonomous agent with real system access) and gives, for each, a recommended defense stack, a base-model choice, a human-in-the-loop threshold, and an autonomy level. The recommendations are calibrated to a cost-of-error tradeoff that the deployer sets, so the framework outputs a small decision tree rather than a single point estimate.

The Business Decision Framework is the principal contribution. It walks a deployer through three typical use cases (a customer-facing chatbot, an internal employee assistant, and an autonomous agent with real system access) and recommends a specific defense setup, an underlying AI model, and a threshold for when humans should still step in. The recommendations are calibrated to how costly the deployer judges different kinds of mistakes to be.

The project was sponsored by Hiflylabs, a Hungarian data and AI consultancy, and that sponsorship is the reason the work is structured the way it is. Without a practitioner-facing sponsor, this would probably have been a more straightforward empirical comparison paper. With one, it became a project about helping companies actually deploy these systems sensibly.

---

## Read more

- [📄 Read the full project (PDF, 135 pages)](https://github.com/b0glarka/capstone_prompt_injection/raw/main/reports/Petruska_2026_MS_Thesis_corr_06_12.pdf)
- [💻 View the repository](https://github.com/b0glarka/capstone_prompt_injection)

The repository contains the source markdown, all code and notebooks, the evaluation pipeline, supporting reports, and reproduction instructions. The PDF is a self-contained read for anyone who just wants the project itself.

---

## Sponsor and acknowledgements

This capstone was sponsored by [Hiflylabs](https://hiflylabs.com), a data, artificial intelligence, and digital-product consultancy. The practitioner-facing orientation that became the project's principal contribution traces directly to the sponsorship. The Business Decision Framework, the focus on the internal-agent deployment scenario as the central case, and the cost-of-error framing all came out of thinking about what would actually be useful for Hiflylabs and their clients rather than treating the work as a purely academic exercise.

Special thanks to [Zsófia Práger](https://www.linkedin.com/in/zsofia-prager-data-science/), Data Scientist at Hiflylabs, for ongoing methodology guidance, weekly check-ins, and the practitioner-oriented framing that shaped the project from start to finish. Thanks also to my CEU advisors [Eduardo Ariño de la Rubia](https://at.linkedin.com/in/earino) and [Zoltán Tóth](https://www.linkedin.com/in/zoltanctoth/) for the structure and support that made the work possible.

---

*Project submitted June 2026. Repository archived for reproducibility. The empirical thresholds reported in the project are conditional on the models evaluated as of mid-2026; the framework structure is designed to be durable across model generations.*
