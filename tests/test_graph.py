from __future__ import annotations

import asyncio
import json
from pathlib import Path

from src.config import DATA_DIR
from src.data_repository import DataRepository
from src.graph import build_case_graph
from src.llm import LlmAuditClient
from src.config import Settings
from src.trace import TraceLogger


def test_graph_writes_one_valid_output(tmp_path: Path, monkeypatch) -> None:
    import src.graph as graph_module

    monkeypatch.setattr(graph_module, "OUTPUT_DIR", tmp_path / "output")
    trace = TraceLogger(tmp_path / "trace.jsonl", "test-run")
    repo = DataRepository.from_directory(DATA_DIR)
    graph = build_case_graph(repo, trace, LlmAuditClient(Settings(), trace))
    case_path = Path("input/EC_001.json").resolve()
    state = asyncio.run(graph.ainvoke({"case_path": str(case_path)}, {"configurable": {"thread_id": "test-1"}}))
    assert state["output_path"].endswith("EC_001.json")
    result = json.loads(Path(state["output_path"]).read_text(encoding="utf-8"))
    assert result["case_id"] == "EC_001"
