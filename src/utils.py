"""Shared helpers used across notebooks, scripts, and pipeline modules.

Patterns consolidated here:
- repo_root() walks up from any starting point to find the project root by `.git`
- env() loads `.env` from repo root and reports presence-only token status
- set_seed() seeds numpy + python random + torch (if available)
"""

from __future__ import annotations

import os
import random
from pathlib import Path

import numpy as np
from dotenv import load_dotenv


def repo_root(start: Path | None = None) -> Path:
    """Walk up from `start` (default: caller's CWD) until we find a `.git` directory.

    Raises if no `.git` ancestor exists.
    """
    here = (start or Path.cwd()).resolve()
    for parent in (here, *here.parents):
        if (parent / ".git").exists():
            return parent
    raise RuntimeError(f"could not locate repo root (no .git ancestor found from {here})")


KNOWN_TOKENS = ("HF_TOKEN", "GROQ_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY")


def env(report: bool = True, dotenv_path: Path | None = None) -> dict[str, bool]:
    """Load `.env` and return a presence-only map for known tokens.

    Never prints token values, even partial. Suitable for public-repo notebooks.
    Returns {token_name: True/False} so callers can branch on which APIs are usable.
    """
    path = dotenv_path or (repo_root() / ".env")
    load_dotenv(dotenv_path=path)
    status = {t: bool(os.getenv(t)) for t in KNOWN_TOKENS}
    if report:
        print("Token status:")
        for t, present in status.items():
            print(f"  {t}: {'set' if present else 'not set'}")
    return status


def set_seed(seed: int = 42, *, torch_seed: bool = True) -> None:
    """Seed numpy + python random; optionally seed torch + force deterministic flags."""
    random.seed(seed)
    np.random.seed(seed)
    if torch_seed:
        try:
            import torch
            torch.manual_seed(seed)
            if torch.cuda.is_available():
                torch.cuda.manual_seed_all(seed)
        except ImportError:
            pass
