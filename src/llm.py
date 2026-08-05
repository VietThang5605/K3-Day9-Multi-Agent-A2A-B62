from __future__ import annotations

from typing import Any

from openai import AsyncOpenAI

from src.config import OPENROUTER_BASE_URL, OPENROUTER_MODEL, Settings
from src.trace import TraceLogger


class LlmAuditClient:
    """Optional OpenRouter call: it documents agent reasoning but cannot change policy output."""

    def __init__(self, settings: Settings, trace: TraceLogger):
        self.enabled = settings.use_llm
        self.trace = trace
        self.client = AsyncOpenAI(api_key=settings.api_key, base_url=OPENROUTER_BASE_URL) if self.enabled else None

    async def acknowledge(self, agent_name: str, case_id: str, facts: dict[str, Any]) -> None:
        if not self.client:
            return
        self.trace.event("model_started", case_id=case_id, agent_name=agent_name, model=OPENROUTER_MODEL)
        response = await self.client.chat.completions.create(
            model=OPENROUTER_MODEL,
            temperature=0,
            max_tokens=120,
            messages=[
                {"role": "system", "content": "You are an audit assistant. Return JSON only: {\"acknowledged\":true}. Do not infer policy."},
                {"role": "user", "content": f"Agent={agent_name}; verified input facts={facts}"},
            ],
            response_format={"type": "json_object"},
        )
        usage = response.usage
        self.trace.event(
            "model_completed", case_id=case_id, agent_name=agent_name, model=OPENROUTER_MODEL,
            prompt_tokens=getattr(usage, "prompt_tokens", None), completion_tokens=getattr(usage, "completion_tokens", None),
        )
