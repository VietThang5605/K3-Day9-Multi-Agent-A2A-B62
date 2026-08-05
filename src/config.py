from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


ROOT_DIR = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT_DIR / "input"
DATA_DIR = ROOT_DIR / "data"
OUTPUT_DIR = ROOT_DIR / "output"
LOG_DIR = ROOT_DIR / "logging"

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODEL = "qwen/qwen3.5-9b"
MODEL_PARAMETER_SIZE = "9B"
MODEL_PROVIDER = "OpenRouter"
ALLOWED_MODELS = {OPENROUTER_MODEL: 9.0}

MODEL_REGISTRY = {
    "order_fulfillment_agent": {"mode": "llm_with_deterministic_tools", "model": OPENROUTER_MODEL},
    "payment_agent": {"mode": "llm_with_deterministic_tools", "model": OPENROUTER_MODEL},
    "policy_decision_agent": {"mode": "llm_with_deterministic_policy_engine", "model": OPENROUTER_MODEL},
    "verifier_agent": {"mode": "deterministic_only", "model": None},
}


@dataclass(frozen=True)
class Settings:
    use_llm: bool = False
    api_key: str | None = None
    max_concurrency: int = 4

    @classmethod
    def from_environment(cls, *, use_llm: bool, max_concurrency: int = 4) -> "Settings":
        api_key = os.getenv("OPENROUTER_API_KEY")
        if use_llm and not api_key:
            raise ValueError("OPENROUTER_API_KEY is required when --use-llm is enabled")
        if OPENROUTER_MODEL not in ALLOWED_MODELS or ALLOWED_MODELS[OPENROUTER_MODEL] > 10:
            raise ValueError("Configured model violates the <=10B parameter limit")
        return cls(use_llm=use_llm, api_key=api_key, max_concurrency=max_concurrency)
