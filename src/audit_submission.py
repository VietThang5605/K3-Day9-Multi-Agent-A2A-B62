from __future__ import annotations

import json
from pathlib import Path

from src.schemas import ResolutionOutput


def audit_submission(input_dir: Path, output_dir: Path, metadata_path: Path, trace_path: Path) -> list[str]:
    expected = {path.stem for path in input_dir.glob("EC_*.json")}
    actual = {path.stem for path in output_dir.glob("EC_*.json")}
    errors: list[str] = []
    if expected != actual:
        errors.append(f"Output case IDs differ: missing={sorted(expected - actual)}, extra={sorted(actual - expected)}")
    for path in output_dir.glob("EC_*.json"):
        try:
            ResolutionOutput.model_validate(json.loads(path.read_text(encoding="utf-8")))
        except Exception as exc:  # audit reports all invalid output files
            errors.append(f"{path.name}: {exc}")
    if not metadata_path.exists():
        errors.append("Missing logging/metadata.json")
    if not trace_path.exists() or not trace_path.read_text(encoding="utf-8").strip():
        errors.append("Missing or empty logging/trace.jsonl")
    return errors
