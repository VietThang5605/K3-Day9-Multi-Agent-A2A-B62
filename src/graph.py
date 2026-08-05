from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from src.agents.order_fulfillment import build_order_fulfillment_facts
from src.agents.payment import build_payment_facts
from src.agents.policy import decide_policy
from src.config import OUTPUT_DIR
from src.data_repository import DataRepository
from src.graph_state import CaseGraphState
from src.llm import LlmAuditClient
from src.schemas import CaseInput, OrderFulfillmentFacts, PaymentFacts, ResolutionOutput
from src.trace import TraceLogger, jsonable
from src.validator import verify_resolution


def build_case_graph(repository: DataRepository, trace: TraceLogger, llm: LlmAuditClient):
    """Build the hybrid graph: parallel fact agents → deterministic policy → independent verifier."""

    async def load_case(state: CaseGraphState) -> dict:
        case = CaseInput.model_validate(json.loads(Path(state["case_path"]).read_text(encoding="utf-8")))
        order_id = case.customer_request.claimed_order_id
        trace.event("case_started", case_id=case.case_id, case_path=state["case_path"], order_id=order_id)
        return {"case": case.model_dump(mode="python"), "case_id": case.case_id, "order_id": order_id}

    async def order_agent(state: CaseGraphState) -> dict:
        case_id, order_id = state["case_id"], state["order_id"]
        trace.event("agent_started", case_id=case_id, agent_name="order_fulfillment_agent")
        facts = build_order_fulfillment_facts(repository, order_id)
        await llm.acknowledge("order_fulfillment_agent", case_id, jsonable(facts.model_dump(mode="python")))
        trace.event("agent_completed", case_id=case_id, agent_name="order_fulfillment_agent", source_refs=facts.source_refs)
        return {"order_fulfillment_facts": facts.model_dump(mode="python")}

    async def payment_agent(state: CaseGraphState) -> dict:
        case_id, order_id = state["case_id"], state["order_id"]
        trace.event("agent_started", case_id=case_id, agent_name="payment_agent")
        facts = build_payment_facts(repository, order_id)
        await llm.acknowledge("payment_agent", case_id, jsonable(facts.model_dump(mode="python")))
        trace.event("agent_completed", case_id=case_id, agent_name="payment_agent", source_refs=facts.source_refs)
        return {"payment_facts": facts.model_dump(mode="python")}

    async def join_facts(state: CaseGraphState) -> dict:
        trace.event("facts_joined", case_id=state["case_id"])
        return {}

    async def policy_agent(state: CaseGraphState) -> dict:
        case_id = state["case_id"]
        trace.event("agent_started", case_id=case_id, agent_name="policy_decision_agent")
        fulfillment = OrderFulfillmentFacts.model_validate(state["order_fulfillment_facts"])
        payment = PaymentFacts.model_validate(state["payment_facts"])
        resolution = decide_policy(case_id, fulfillment, payment)
        await llm.acknowledge("policy_decision_agent", case_id, jsonable(resolution.model_dump(mode="python")))
        trace.event("agent_completed", case_id=case_id, agent_name="policy_decision_agent", issue=resolution.assessment.primary_issue)
        return {"candidate_resolution": resolution.model_dump(mode="python")}

    async def verifier_agent(state: CaseGraphState) -> dict:
        case_id = state["case_id"]
        trace.event("agent_started", case_id=case_id, agent_name="verifier_agent")
        result = verify_resolution(
            state["candidate_resolution"], state["order_fulfillment_facts"], state["payment_facts"], repository
        )
        trace.event("verification_completed", case_id=case_id, passed=result.passed, error_codes=result.error_codes)
        return {"verification": result.model_dump(mode="python")}

    def route_after_verifier(state: CaseGraphState) -> Literal["write_output", "record_failure"]:
        return "write_output" if state["verification"]["passed"] else "record_failure"

    async def write_output(state: CaseGraphState) -> dict:
        output = ResolutionOutput.model_validate(state["candidate_resolution"])
        path = OUTPUT_DIR / f"{output.case_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(jsonable(output.model_dump(mode="python")), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)
        trace.event("output_written", case_id=output.case_id, output_path=str(path))
        trace.event("case_completed", case_id=output.case_id, status="success")
        return {"output_path": str(path)}

    async def record_failure(state: CaseGraphState) -> dict:
        verification = state["verification"]
        error = "; ".join(verification["error_messages"])
        trace.event("case_completed", case_id=state["case_id"], status="failed", error_codes=verification["error_codes"])
        return {"error": error}

    builder = StateGraph(CaseGraphState)
    builder.add_node("load_case", load_case)
    builder.add_node("order_fulfillment_agent", order_agent)
    builder.add_node("payment_agent", payment_agent)
    builder.add_node("join_facts", join_facts)
    builder.add_node("policy_decision_agent", policy_agent)
    builder.add_node("verifier_agent", verifier_agent)
    builder.add_node("write_output", write_output)
    builder.add_node("record_failure", record_failure)
    builder.add_edge(START, "load_case")
    builder.add_edge("load_case", "order_fulfillment_agent")
    builder.add_edge("load_case", "payment_agent")
    builder.add_edge(["order_fulfillment_agent", "payment_agent"], "join_facts")
    builder.add_edge("join_facts", "policy_decision_agent")
    builder.add_edge("policy_decision_agent", "verifier_agent")
    builder.add_conditional_edges("verifier_agent", route_after_verifier)
    builder.add_edge("write_output", END)
    builder.add_edge("record_failure", END)
    return builder.compile(checkpointer=MemorySaver())
