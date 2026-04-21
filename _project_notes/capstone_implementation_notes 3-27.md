# Capstone Implementation Notes
*Items not in the proposal but relevant to project execution*

---

## Inference Providers

The correct term for Together.ai, Groq, Cerebras and similar services is **inference providers** (or "inference API providers"). They are not model developers — they run open-source models on their own hardware and sell API access. This distinction matters practically: you are not locked to any one provider, because they all offer the same underlying models. Switching providers means changing an endpoint URL and an API key, not rewriting code, because all major inference providers expose an OpenAI-compatible API.

### Providers Considered

| Provider | Free Tier | Llama 3.3 70B | Notes |
|---|---|---|---|
| **Groq** | No (pay per token from first call) | $0.59 input / $0.79 output per 1M tokens | Fast (394 tokens/s). "Free API key" means no upfront commitment, not a free tier. |
| **Together.ai** | No | $0.88 per 1M tokens (input and output) | Zsófi's recommendation. Batch API available at 50% discount. |
| **Cerebras** | Yes (genuinely free) | Not available | Free tier exists but model selection is thin: only Llama 3.1 8B and GPT OSS 120B in production. Llama 3.3 70B not offered. Rate limits on best models currently reduced due to demand. |

### First-Party API Keys vs Inference Providers

These are two distinct categories of API access and they give you access to different models:

**First-party API keys** (from the model developer directly) give you access to that company's proprietary closed-source models and nothing else:
- **OpenAI API** (platform.openai.com): GPT-4o, GPT-4o-mini, o-series reasoning models, etc. These models are only available here.
- **Anthropic API** (console.anthropic.com): Claude models only. Available here or via inference providers that have licensing agreements.
- **Google AI Studio** (aistudio.google.com): Gemini models only. Free tier with generous rate limits.

**Inference providers** (Groq, Together.ai, Cerebras, etc.) give you access to open-source models that no single company owns, primarily the Llama family, Mistral, Qwen, and similar. You cannot get Llama 3.3 70B from OpenAI or Anthropic directly. You need either an inference provider or to run it yourself locally.

**What you currently have:**
- OpenAI API key: confirmed working, full model access. Verify at platform.openai.com who is paying before using at scale.
- Anthropic API key: likely working given Claude Code VSCode setup. Confirm billing at console.anthropic.com.
- Google AI Studio: free tier available, get API key at aistudio.google.com. Gemini Flash is the right choice here for the LLM-as-judge role given it is free and capable enough for binary classification.
- Inference provider: none yet. Groq is the recommended starting point for Llama 3.3 70B access.

### Recommended Approach

- Use **Groq** as the primary inference provider. Llama 3.3 70B is available, cost is low, and speed is sufficient for latency measurement.
- Budget approximately **$10–$20** on Groq for the full evaluation. At ~6,000 prompts with ~1,000 tokens per prompt (input + output combined across agent call and judge call), total spend on a full pass is roughly $5–$10. With development iterations, total project cost is likely under $30.
- If comparing across providers is useful for the latency dimension (it could be a minor methodological point about reproducibility), run the final timed pass on both Groq and Together.ai and report results per provider.
- Use **Cerebras** only if you want a zero-cost sandbox for early pipeline testing and are willing to work with Llama 3.1 8B rather than 3.3 70B.
- CEU does not provide API keys. Hiflylabs offered to provide API keys for Gemini, Claude, or OpenAI if needed for the secondary model comparison — follow up with Zsófi on this when the time comes.

### Model Selection

- **Primary agent under test**: Llama 3.3 70B. Matches Zsófi's current client context (she has a client running self-hosted Llama 3.3, which is why she flagged Together.ai). Access via Groq or Together.ai.
- **Secondary model**: A closed-source model (Gemini, Claude, or GPT) for cross-model validity check. Use existing paid subscriptions or request API access from Hiflylabs.
- **LLM-as-judge (Defense B)**: A smaller, cheaper model is sufficient since it is doing binary classification on outputs. Gemini Flash via the free student Google AI Studio access is a reasonable choice here.
- **Input classifier (Defense A)**: ProtectAI DeBERTa or Meta Llama Prompt Guard. Both run locally, no API cost.

---

## Defense A: Prompt Augmentation (Baseline)

Removed from the proposal to avoid giving Eduardo additional scope concerns, but worth implementing.

**What it is**: System prompt instructions telling the model to ignore injected content, use of delimiters to separate trusted and untrusted content, and the "sandwich defense" (repeating instructions after the user content). Requires no additional models.

**Why to include it anyway**: Takes roughly two hours to implement once the evaluation pipeline exists. Having it in results provides an anchor for the statistical comparisons — without a baseline, the difference between Defense A (input classifier) and Defense B (output validation) is harder to contextualize. A result like "input classifier improves over no defense by X%, output validation improves by Y%" is more meaningful than a result that only compares the two classifiers against each other. Eduardo will be glad it is there when he sees the final report.

**Implementation note**: This is Defense A in the internal numbering. The proposal uses A and B for input classifier and output validation respectively. Keep your internal notes consistent to avoid confusion.

---

## Literature Review by Threat Vector

Removed from the proposal to avoid reinforcing Eduardo's scope concerns, and because it does not require approval — it is background research.

**What Hiflylabs asked for**: Zsófi indicated that while the narrowed prompt injection focus was acceptable, Hiflylabs would appreciate some broader coverage of the other threat categories from their original brief. The agreed framing was a structured literature review organized by threat vector, ideally as an appendix to the final report.

**Threat vectors to cover** (from Hiflylabs' original brief):
- Prompt injection (direct and indirect) — covered in depth by the main analysis
- Text-to-SQL injection
- Excessive agency
- Additional indirect injection vectors beyond BIPIA

**How to approach it**: Do this in parallel with the main project work rather than sequentially. As you read papers for the core analysis, you will naturally encounter references to adjacent threat categories. Capture these as you go in a reference manager (Zotero works well) with a tag or folder per threat vector. By the time you are writing the final report, the appendix will largely assemble itself from accumulated notes rather than requiring a separate research sprint.

**Practical tip**: When doing initial literature search, generate a list of references and categorize them per threat vector as you find them. This was Zsófi's specific suggestion and is a low-effort way to have something concrete to show at early check-ins.

---

## Other Notes from Zsófi Meeting

- **Weekly check-ins**: Zsófi envisions 30-minute weekly calls to review progress and problems encountered.
- **Budapest visit**: Confirm April dates when schedule is sorted. The team wants to meet in person.
- **Project sponsor**: Resolved. Zsófi Prager is listed as the formal PID sponsor.
- **Confidentiality**: Not a concern. The evaluation uses only public datasets, open-source model implementations, and a generic business scenario not tied to any named client. Nothing in scope is proprietary or confidential, so the public thesis summary presents no issue.
- **Deliverable format**: The deliverable is a 20–25 page consulting-style report plus a slide deck, as CEU requires. Kálmán's original "high-level guide" framing is superseded by this. The structured literature review across other threat vectors can appear as an appendix to the main report if completed.
