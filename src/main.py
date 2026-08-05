from __future__ import annotations

import argparse
import asyncio
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv

from src.audit_submission import audit_submission
from src.config import DATA_DIR, INPUT_DIR, LOG_DIR, OUTPUT_DIR, Settings
from src.data_repository import DataRepository
from src.graph import build_case_graph
from src.llm import LlmAuditClient
from src.metadata import write_metadata
from src.trace import TraceLogger


async def run_batch(*, input_dir: Path, use_llm: bool, max_concurrency: int) -> int:
    load_dotenv()
    settings = Settings.from_environment(use_llm=use_llm, max_concurrency=max_concurrency)
    case_paths = sorted(input_dir.glob("EC_*.json"))
    if not case_paths:
        raise ValueError(f"No EC_*.json cases found in {input_dir}")
    run_id = str(uuid.uuid4())
    OUTPUT_DIR.mkdir(exist_ok=True)
    LOG_DIR.mkdir(exist_ok=True)
    trace = TraceLogger(LOG_DIR / "trace.jsonl", run_id)
    trace.event("run_started", case_count=len(case_paths), llm_enabled=use_llm)
    repository = DataRepository.from_directory(DATA_DIR)
    llm = LlmAuditClient(settings, trace)
    graph = build_case_graph(repository, trace, llm)
    semaphore = asyncio.Semaphore(max_concurrency)

    async def run_case(path: Path) -> dict:
        async with semaphore:
            return await graph.ainvoke(
                {"case_path": str(path)},
                {"configurable": {"thread_id": f"{run_id}:{path.stem}"}},
            )

    results = await asyncio.gather(*(run_case(path) for path in case_paths), return_exceptions=True)
    succeeded = sum(1 for result in results if isinstance(result, dict) and result.get("output_path"))
    failures = [str(result) for result in results if isinstance(result, Exception)]
    for failure in failures:
        trace.event("pipeline_exception", error=failure)
    write_metadata(LOG_DIR / "metadata.json", run_id, settings, case_count=len(case_paths), success_count=succeeded)
    trace.event("run_completed", case_count=len(case_paths), success_count=succeeded, exception_count=len(failures))
    audit_errors = audit_submission(input_dir, OUTPUT_DIR, LOG_DIR / "metadata.json", LOG_DIR / "trace.jsonl")
    if audit_errors:
        for error in audit_errors:
            print(f"AUDIT ERROR: {error}")
        return 1
    print(f"Completed {succeeded}/{len(case_paths)} cases. Run ID: {run_id}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Olist EC_POLICY_V1 LangGraph batch runner")
    parser.add_argument("--input-dir", type=Path, default=INPUT_DIR)
    parser.add_argument("--use-llm", action="store_true", help="Require OPENROUTER_API_KEY and call the configured OpenRouter model")
    parser.add_argument("--max-concurrency", type=int, default=4)
    parser.add_argument("--audit-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.max_concurrency < 1:
        raise ValueError("--max-concurrency must be at least 1")
    if args.audit_only:
        errors = audit_submission(args.input_dir, OUTPUT_DIR, LOG_DIR / "metadata.json", LOG_DIR / "trace.jsonl")
        if errors:
            print("\n".join(f"AUDIT ERROR: {error}" for error in errors))
            return 1
        print("Audit passed")
        return 0
    return asyncio.run(run_batch(input_dir=args.input_dir, use_llm=args.use_llm, max_concurrency=args.max_concurrency))


if __name__ == "__main__":
    raise SystemExit(main())
