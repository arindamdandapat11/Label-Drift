from __future__ import annotations

import re
from typing import Any

import torch
from transformers import AutoConfig, AutoModelForCausalLM, AutoModelForSeq2SeqLM, AutoTokenizer


def parse_label(raw: str, labels: list[str]) -> str:
    cleaned = raw.strip().lower()
    cleaned = cleaned.replace("```json", " ").replace("```", " ")
    match = re.search(r'"label"\s*:\s*"([^"]+)"', cleaned)
    if match:
        cleaned = match.group(1).strip().lower()

    for label in sorted(labels, key=len, reverse=True):
        if re.search(rf"\b{re.escape(label.lower())}\b", cleaned):
            return label.lower()

    first = re.split(r"[\s,.:;]+", cleaned, maxsplit=1)[0]
    if first in {label.lower() for label in labels}:
        return first
    return "unknown"


class LocalClassifier:
    def __init__(self, model_name: str, max_new_tokens: int = 16, temperature: float = 0.0):
        self.model_name = model_name
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        self.config = AutoConfig.from_pretrained(model_name)
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        if getattr(self.config, "is_encoder_decoder", False):
            self.model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
        else:
            self.model = AutoModelForCausalLM.from_pretrained(model_name)

        self.model.to(self.device)
        self.model.eval()

    def generate(self, prompt: str) -> str:
        encoded = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=1024)
        encoded = {key: value.to(self.device) for key, value in encoded.items()}

        generate_kwargs: dict[str, Any] = {
            "max_new_tokens": self.max_new_tokens,
            "pad_token_id": self.tokenizer.pad_token_id,
        }
        if self.temperature and self.temperature > 0:
            generate_kwargs.update(do_sample=True, temperature=self.temperature)
        else:
            generate_kwargs["do_sample"] = False

        with torch.no_grad():
            output_ids = self.model.generate(**encoded, **generate_kwargs)

        if not getattr(self.config, "is_encoder_decoder", False):
            output_ids = output_ids[:, encoded["input_ids"].shape[1] :]

        return self.tokenizer.decode(output_ids[0], skip_special_tokens=True).strip()
