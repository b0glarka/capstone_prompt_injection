"""ProtectAI DeBERTa v3 prompt-injection classifier wrapper.

Model: ProtectAI/deberta-v3-base-prompt-injection-v2
Reference: https://huggingface.co/protectai/deberta-v3-base-prompt-injection-v2

The model returns one of two labels with a confidence score:
  - "SAFE"      (label_id 0)
  - "INJECTION" (label_id 1)

This wrapper exposes a `predict` method that returns a uniform record per prompt
including the binary label, raw label string, and the injection-class probability,
so downstream metrics (accuracy, ROC, threshold sweeps) can use either form.
"""

from __future__ import annotations

from typing import Iterable

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

DEFAULT_MODEL = "ProtectAI/deberta-v3-base-prompt-injection-v2"


def _autodetect_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


class DebertaInjectionDetector:
    """Batched inference wrapper around ProtectAI's DeBERTa v3 prompt-injection classifier."""

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

        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_name)
        self.model.to(self.device)
        self.model.eval()

        self.id2label = self.model.config.id2label
        self.injection_label_id = next(
            i for i, lbl in self.id2label.items() if lbl.upper() == "INJECTION"
        )

    @torch.no_grad()
    def predict(self, prompts: Iterable[str]) -> list[dict]:
        """Run inference on an iterable of prompts. Returns one dict per prompt:
            {
                "label": "INJECTION" | "SAFE",
                "label_id": 0 | 1,
                "injection_score": float,   # probability of class INJECTION
                "score": float,             # probability of the predicted class
            }
        """
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
                        "label": self.id2label[pred_id],
                        "label_id": int(pred_id),
                        "injection_score": float(probs[i, self.injection_label_id]),
                        "score": float(probs[i, pred_id]),
                    }
                )
        return out
