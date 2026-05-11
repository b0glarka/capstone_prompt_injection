"""Llama 3.3 70B agent wrappers for Defense B.

Two inference providers are supported:
  - GroqAgent:     Llama 3.3 70B Versatile on Groq. Free/on-demand has a 100K
                   tokens/day cap; Dev tier has higher quotas but was temporarily
                   closed to new signups as of 2026-05-11.
  - TogetherAgent: Llama 3.3 70B Instruct Turbo on Together AI. Pay-as-you-go,
                   no daily quota. ~$0.88/M tokens. Used as the Groq-quota
                   workaround for the 500-row pilot.

Both classes expose the same `respond(user_prompt) -> dict` interface, so the
pilot script can swap providers via a flag without other code changes.

Caching is via the project-wide JSONL append-log (`src/cache.py`).
"""

from __future__ import annotations

import os
from typing import Iterable, Literal

from groq import Groq
from openai import OpenAI

DEFAULT_MODEL_GROQ = "llama-3.3-70b-versatile"
DEFAULT_MODEL_TOGETHER = "meta-llama/Llama-3.3-70B-Instruct-Turbo"
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


Provider = Literal["groq", "together"]


def make_agent(provider: Provider = "groq", **kwargs) -> GroqAgent | TogetherAgent:
    """Factory that returns the appropriate agent for the given provider."""
    if provider == "groq":
        return GroqAgent(**kwargs)
    if provider == "together":
        return TogetherAgent(**kwargs)
    raise ValueError(f"unknown provider: {provider!r}")
