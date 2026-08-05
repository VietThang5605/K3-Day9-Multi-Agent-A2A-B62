from __future__ import annotations

from decimal import Decimal

from pydantic import ValidationError

from src.agents.policy import decide_policy
from src.data_repository import DataRepository
from src.evidence import evidence_exists
from src.schemas import OrderFulfillmentFacts, PaymentFacts, ResolutionOutput, VerificationResult


def verify_resolution(
    candidate: dict, fulfillment_data: dict, payment_data: dict, repository: DataRepository
) -> VerificationResult:
    errors: list[str] = []
    messages: list[str] = []
    try:
        output = ResolutionOutput.model_validate(candidate)
        fulfillment = OrderFulfillmentFacts.model_validate(fulfillment_data)
        payment = PaymentFacts.model_validate(payment_data)
    except ValidationError as exc:
        return VerificationResult(passed=False, error_codes=["JSON_SCHEMA"], error_messages=[str(exc)])

    if output.case_id == "":
        errors.append("CASE_ID")
        messages.append("case_id must not be empty")
    if any(not evidence_exists(ref, repository) for ref in output.evidence_ids):
        errors.append("EVIDENCE_NOT_FOUND")
        messages.append("Every evidence ID must resolve to an allowed source record")
    if not output.evidence_ids or not any(ref.startswith("policy:") for ref in output.evidence_ids):
        errors.append("POLICY_EVIDENCE")
        messages.append("A policy evidence ID is required")
    refund = output.financial_resolution.recommended_refund_brl
    if (refund > Decimal("0.00")) != (output.assessment.case_status == "action_required"):
        errors.append("ACTION_REQUIRED_INVARIANT")
        messages.append("action_required must be equivalent to a positive refund")
    if output.financial_resolution.currency != "BRL":
        errors.append("CURRENCY")
        messages.append("currency must be BRL")
    expected = decide_policy(output.case_id, fulfillment, payment)
    if output.model_dump(mode="json") != expected.model_dump(mode="json"):
        errors.append("POLICY_MISMATCH")
        messages.append("Candidate differs from deterministic EC_POLICY_V1 decision")
    return VerificationResult(passed=not errors, error_codes=errors, error_messages=messages)
