"""One-call smoke test for each LLM API used in the project.

Prints PASS / FAIL per provider, the model name, and a short response excerpt
or error. Does NOT print the API key. Total spend is well under $0.01.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(dotenv_path=REPO_ROOT / ".env")

PING = "Reply with the single word: pong."

results: list[tuple[str, str, str]] = []  # (provider, status, detail)


def _short(text: str, n: int = 80) -> str:
    text = (text or "").strip().replace("\n", " ")
    return text if len(text) <= n else text[:n] + "..."


# Groq - Llama 3.3 70B Versatile
try:
    from groq import Groq

    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": PING}],
        max_tokens=10,
        temperature=0,
    )
    out = resp.choices[0].message.content
    results.append(("Groq (llama-3.3-70b-versatile)", "PASS", _short(out)))
except Exception as e:
    results.append(("Groq (llama-3.3-70b-versatile)", "FAIL", _short(repr(e))))


# Anthropic - Claude Sonnet 4.6
try:
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=10,
        messages=[{"role": "user", "content": PING}],
    )
    out = resp.content[0].text if resp.content else ""
    results.append(("Anthropic (claude-sonnet-4-6)", "PASS", _short(out)))
except Exception as e:
    results.append(("Anthropic (claude-sonnet-4-6)", "FAIL", _short(repr(e))))


# OpenAI - GPT-4o
try:
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": PING}],
        max_tokens=10,
        temperature=0,
    )
    out = resp.choices[0].message.content
    results.append(("OpenAI (gpt-4o)", "PASS", _short(out)))
except Exception as e:
    results.append(("OpenAI (gpt-4o)", "FAIL", _short(repr(e))))


# Print summary
width = max(len(p) for p, _, _ in results)
print("\nAPI smoke test results")
print("-" * (width + 60))
for provider, status, detail in results:
    print(f"  {provider:<{width}}  [{status}]  {detail}")
print()

failed = [r for r in results if r[1] == "FAIL"]
sys.exit(0 if not failed else 1)
