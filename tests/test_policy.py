from __future__ import annotations

import json
from pathlib import Path

from src.agents.order_fulfillment import build_order_fulfillment_facts
from src.agents.payment import build_payment_facts
from src.agents.policy import decide_policy
from src.config import DATA_DIR, INPUT_DIR
from src.data_repository import DataRepository
from src.schemas import CaseInput
from src.validator import verify_resolution


def test_all_official_cases_resolve_and_verify() -> None:
    repository = DataRepository.from_directory(DATA_DIR)
    paths = sorted(INPUT_DIR.glob("EC_*.json"))
    assert len(paths) == 50
    for path in paths:
        case = CaseInput.model_validate(json.loads(path.read_text(encoding="utf-8")))
        order_id = case.customer_request.claimed_order_id
        fulfillment = build_order_fulfillment_facts(repository, order_id)
        payment = build_payment_facts(repository, order_id)
        output = decide_policy(case.case_id, fulfillment, payment)
        verification = verify_resolution(output.model_dump(mode="python"), fulfillment.model_dump(mode="python"), payment.model_dump(mode="python"), repository)
        assert verification.passed, f"{case.case_id}: {verification.error_messages}"


def test_policy_distribution_and_refund_total() -> None:
    repository = DataRepository.from_directory(DATA_DIR)
    counts: dict[str, int] = {}
    refund_total = 0.0
    for path in sorted(INPUT_DIR.glob("EC_*.json")):
        case = CaseInput.model_validate(json.loads(path.read_text(encoding="utf-8")))
        order_id = case.customer_request.claimed_order_id
        output = decide_policy(case.case_id, build_order_fulfillment_facts(repository, order_id), build_payment_facts(repository, order_id))
        counts[output.assessment.primary_issue] = counts.get(output.assessment.primary_issue, 0) + 1
        refund_total += float(output.financial_resolution.recommended_refund_brl)
    assert counts == {
        "canceled_order_paid": 8, "unavailable_order_paid": 8, "late_delivery_seller": 8,
        "late_delivery_logistics": 8, "valid_split_payment": 9, "unsupported_late_claim": 9,
    }
    assert round(refund_total, 2) == 3429.64
