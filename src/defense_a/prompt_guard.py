"""Meta Prompt Guard 2 86M classifier wrapper.

Model: meta-llama/Llama-Prompt-Guard-2-86M
Backbone: mDeBERTa-v3-base, 86M parameters, multi-language.

Labels (from model config):
  - LABEL_0 = benign / safe
  - LABEL_1 = injection / malicious

This wrapper exposes a `predict` method that returns the same record schema as
`src.defense_a.deberta.DebertaInjectionDetector` so downstream metrics code is
classifier-agnostic.
"""

from __future__ import annotations

import os
from typing import Iterable

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

DEFAULT_MODEL = "meta-llama/Llama-Prompt-Guard-2-86M"
INJECTION_LABEL_ID = 1  # LABEL_1 per model config


def _autodetect_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


class PromptGuard2Detector:
    """Batched inference wrapper around Meta Prompt Guard 2."""

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        device: str | None = None,
        max_length: int = 512,
        batch_size: int = 16,
    ) -> None:
        self.model_name = model_name
        self.device = device or _autodetect_device()
        self.max_length = max_length
        self.batch_size = batch_size

        token = os.environ.get("HF_TOKEN")
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, token=token)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name, token=token)
        self.model.to(self.device)
        self.model.eval()

        self.id2label = self.model.config.id2label
        self.injection_label_id = INJECTION_LABEL_ID

    @torch.no_grad()
    def predict(self, prompts: Iterable[str]) -> list[dict]:
        prompts = list(prompts)
        out: list[dict] = []
        for start in range(0, len(prompts), self.batch_size):
            batch = prompts[start : start + self.batch_size]
            enc = self.tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=self.max_length,
                return_tensors="pt",
            ).to(self.device)
            logits = self.model(**enc).logits
            probs = torch.softmax(logits, dim=-1).cpu()
            pred_ids = probs.argmax(dim=-1).tolist()
            for i, pred_id in enumerate(pred_ids):
                out.append(
                    {
                        "label": "INJECTION" if pred_id == self.injection_label_id else "SAFE",
                        "label_id": int(pred_id),
                        "injection_score": float(probs[i, self.injection_label_id]),
                        "score": float(probs[i, pred_id]),
                    }
                )
        return out
