from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from src.config import MODEL_PARAMETER_SIZE, MODEL_PROVIDER, MODEL_REGISTRY, OPENROUTER_MODEL, Settings


def write_metadata(path: Path, run_id: str, settings: Settings, *, case_count: int, success_count: int) -> None:
    payload = {
        "run_id": run_id,
        "created_at": datetime.now(UTC).isoformat(),
        "runtime": {"python": "3.11", "orchestration": "LangGraph StateGraph", "trace_format": "JSONL"},
        "llm_enabled": settings.use_llm,
        "model": {"provider": MODEL_PROVIDER, "name": OPENROUTER_MODEL, "parameter_size": MODEL_PARAMETER_SIZE, "limit_billion_parameters": 10},
        "agent_model_registry": MODEL_REGISTRY,
        "cases": {"requested": case_count, "succeeded": success_count, "failed": case_count - success_count},
        "secrets_logged": False,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
