from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any


def jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    return value


class TraceLogger:
    """Append-only, secret-free JSONL execution trace required for submission."""

    def __init__(self, path: Path, run_id: str):
        self.path = path
        self.run_id = run_id
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("", encoding="utf-8")

    def event(self, event_type: str, *, case_id: str | None = None, **data: Any) -> None:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "run_id": self.run_id,
            "event_type": event_type,
            "case_id": case_id,
            **jsonable(data),
        }
        with self._lock, self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
