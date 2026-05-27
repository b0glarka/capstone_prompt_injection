"""Agent wrappers for Defense B.

Three inference providers are supported:
  - GroqAgent:     Llama 3.3 70B Versatile on Groq. Free/on-demand has a 100K
                   tokens/day cap; Dev tier has higher quotas but was temporarily
                   closed to new signups as of 2026-05-11.
  - TogetherAgent: Llama 3.3 70B Instruct Turbo on Together AI. Pay-as-you-go,
                   no daily quota. ~$0.88/M tokens. Used as the Groq-quota
                   workaround for the 500-row pilot.
  - QwenAgent:     Qwen 2.5 72B Instruct Turbo on Together AI. Structurally
                   identical to TogetherAgent but targets a different model
                   family. Used for the cross-family comparison experiment.
                   Together AI model ID: Qwen/Qwen2.5-72B-Instruct-Turbo.
                   Pricing: ~$1.20/M input + $1.20/M output tokens (Together AI
                   standard rate for 72B models; verify on together.ai/pricing).

All three classes expose the same `respond(user_prompt) -> dict` interface, so
pilot scripts can swap agents via a flag without other code changes.

Caching is via the project-wide JSONL append-log (`src/cache.py`).
"""

from __future__ import annotations

import os
from typing import Iterable, Literal

from groq import Groq
from openai import OpenAI

DEFAULT_MODEL_GROQ = "llama-3.3-70b-versatile"
DEFAULT_MODEL_TOGETHER = "meta-llama/Llama-3.3-70B-Instruct-Turbo"
DEFAULT_MODEL_QWEN = "Qwen/Qwen3-235B-A22B-Instruct-2507-tput"
DEFAULT_MODEL_MISTRAL = "mistralai/mistral-large-2411"
DEFAULT_MODEL_DEEPSEEK = "deepseek/deepseek-chat-v3-0324"
DEFAULT_SYSTEM = "You are a helpful general-purpose assistant. Answer the user concisely and accurately."


class GroqAgent:
    def __init__(
        self,
        model: str = DEFAULT_MODEL_GROQ,
        system_prompt: str = DEFAULT_SYSTEM,
        temperature: float = 0.0,
        max_tokens: int = 400,
    ) -> None:
        self.model = model
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.client = Groq(api_key=os.environ["GROQ_API_KEY"])

    def respond(self, user_prompt: str) -> dict:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        return {
            "model": self.model,
            "response": resp.choices[0].message.content,
            "input_tokens": resp.usage.prompt_tokens,
            "output_tokens": resp.usage.completion_tokens,
            "finish_reason": resp.choices[0].finish_reason,
        }


class TogetherAgent:
    """Together AI agent wrapper. Same Llama 3.3 70B model class as GroqAgent.

    Uses Together's OpenAI-compatible endpoint, so the OpenAI client library
    serves it without an additional SDK dependency.
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL_TOGETHER,
        system_prompt: str = DEFAULT_SYSTEM,
        temperature: float = 0.0,
        max_tokens: int = 400,
    ) -> None:
        self.model = model
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.client = OpenAI(
            api_key=os.environ["TOGETHER_API_KEY"],
            base_url="https://api.together.xyz/v1",
        )

    def respond(self, user_prompt: str) -> dict:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        return {
            "model": self.model,
            "response": resp.choices[0].message.content,
            "input_tokens": resp.usage.prompt_tokens,
            "output_tokens": resp.usage.completion_tokens,
            "finish_reason": resp.choices[0].finish_reason,
        }


class QwenAgent:
    """Qwen 2.5 72B Instruct Turbo agent on Together AI.

    Structurally identical to TogetherAgent; separated into its own class so
    callers can inspect `agent.model` and immediately see the model family
    without parsing the model string. Uses Together's OpenAI-compatible endpoint.

    Default model: Qwen/Qwen2.5-72B-Instruct-Turbo.
    Temperature 0, max_tokens 400 to match the Llama pilot setup.
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL_QWEN,
        system_prompt: str = DEFAULT_SYSTEM,
        temperature: float = 0.0,
        max_tokens: int = 400,
    ) -> None:
        self.model = model
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.client = OpenAI(
            api_key=os.environ["TOGETHER_API_KEY"],
            base_url="https://api.together.xyz/v1",
        )

    def respond(self, user_prompt: str) -> dict:
        """Send a single user turn and return a standardised result dict.

        Returns:
            dict with keys: model, response, input_tokens, output_tokens,
            finish_reason.
        """
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        return {
            "model": self.model,
            "response": resp.choices[0].message.content,
            "input_tokens": resp.usage.prompt_tokens,
            "output_tokens": resp.usage.completion_tokens,
            "finish_reason": resp.choices[0].finish_reason,
        }


class OpenRouterAgent:
    """OpenAI-compatible agent talking to OpenRouter.

    OpenRouter is a meta-provider that aggregates many model APIs behind a
    single OpenAI-compatible endpoint. Used for models that Together AI does
    not offer serverless: Mistral Large 2 (mistralai/mistral-large-2411) and
    DeepSeek V3 (deepseek/deepseek-chat-v3-0324). Same `respond(user_prompt)`
    interface as the other agents.

    Default model is Mistral Large 2; pass `model=DEFAULT_MODEL_DEEPSEEK` to
    target DeepSeek V3 instead.
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL_MISTRAL,
        system_prompt: str = DEFAULT_SYSTEM,
        temperature: float = 0.0,
        max_tokens: int = 400,
    ) -> None:
        self.model = model
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.client = OpenAI(
            api_key=os.environ["OPENROUTER_API_KEY"],
            base_url="https://openrouter.ai/api/v1",
        )

    def respond(self, user_prompt: str) -> dict:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        return {
            "model": self.model,
            "response": resp.choices[0].message.content,
            "input_tokens": resp.usage.prompt_tokens,
            "output_tokens": resp.usage.completion_tokens,
            "finish_reason": resp.choices[0].finish_reason,
        }


Provider = Literal["groq", "together", "qwen", "mistral", "deepseek"]


def make_agent(provider: Provider = "groq", **kwargs):
    """Factory that returns the appropriate agent for the given provider.

    Args:
        provider: one of "groq" (Llama 3.3 70B via Groq), "together" (Llama 3.3
            70B via Together AI), "qwen" (Qwen 3 235B-A22B via Together AI),
            "mistral" (Mistral Large 2 via OpenRouter), or "deepseek" (DeepSeek
            V3 via OpenRouter).
        **kwargs: passed through to the agent constructor (e.g. model, system_prompt).
    """
    if provider == "groq":
        return GroqAgent(**kwargs)
    if provider == "together":
        return TogetherAgent(**kwargs)
    if provider == "qwen":
        return QwenAgent(**kwargs)
    if provider == "mistral":
        kwargs.setdefault("model", DEFAULT_MODEL_MISTRAL)
        return OpenRouterAgent(**kwargs)
    if provider == "deepseek":
        kwargs.setdefault("model", DEFAULT_MODEL_DEEPSEEK)
        return OpenRouterAgent(**kwargs)
    raise ValueError(f"unknown provider: {provider!r}")
