from __future__ import annotations

from decimal import Decimal

from src.schemas import (
    AffectedEntities,
    Assessment,
    FinancialResolution,
    OrderFulfillmentFacts,
    PaymentFacts,
    RankedCause,
    ResolutionOutput,
    ResponsibleParty,
    RootCauseAnalysis,
)


def decide_policy(
    case_id: str, fulfillment: OrderFulfillmentFacts, payment: PaymentFacts
) -> ResolutionOutput:
    """Apply EC_POLICY_V1 in its documented priority order; no LLM determines money or liability."""
    paid = payment.payment_total_brl > Decimal("0.00")
    status = fulfillment.order_status
    if status == "canceled" and paid:
        issue, cause, refund, action, parties = (
            "canceled_order_paid", "ORDER_CANCELED_AFTER_PAYMENT", payment.payment_total_brl,
            "issue_full_refund", [ResponsibleParty(party_type="platform", party_id="OLIST_PLATFORM")],
        )
    elif status == "unavailable" and paid:
        issue, cause, refund, action, parties = (
            "unavailable_order_paid", "ORDER_UNAVAILABLE_AFTER_PAYMENT", payment.payment_total_brl,
            "issue_full_refund", [ResponsibleParty(party_type="platform", party_id="OLIST_PLATFORM")],
        )
    elif fulfillment.delivery_late and fulfillment.late_seller_ids:
        issue, cause, refund, action = (
            "late_delivery_seller", "SELLER_HANDOFF_AFTER_LIMIT", fulfillment.freight_total_brl, "refund_freight"
        )
        parties = [ResponsibleParty(party_type="seller", party_id=seller) for seller in fulfillment.late_seller_ids]
    elif fulfillment.delivery_late:
        issue, cause, refund, action, parties = (
            "late_delivery_logistics", "CARRIER_DELIVERED_AFTER_ESTIMATE", fulfillment.freight_total_brl,
            "refund_freight", [ResponsibleParty(party_type="logistics_provider", party_id="LOGISTICS_PROVIDER")],
        )
    elif payment.payment_row_count >= 2 and payment.payment_matches:
        issue, cause, refund, action, parties = (
            "valid_split_payment", "MULTIPLE_PAYMENTS_RECONCILED", Decimal("0.00"),
            "explain_valid_split_payment", [],
        )
    elif not fulfillment.delivery_late and payment.payment_matches:
        issue, cause, refund, action, parties = (
            "unsupported_late_claim", "DELIVERY_WITHIN_ESTIMATE", Decimal("0.00"),
            "reject_late_refund", [],
        )
    else:
        raise ValueError(f"No EC_POLICY_V1 rule applies to case {case_id}")

    evidence = [f"order:{fulfillment.order_id}"]
    evidence.extend(f"item:{item_id}" for item_id in fulfillment.item_ids)
    evidence.extend(f"payment:{payment_id}" for payment_id in payment.payment_ids)
    if issue == "late_delivery_seller":
        evidence.extend(f"seller:{seller}" for seller in fulfillment.late_seller_ids)
    evidence.append(f"policy:{cause}")
    return ResolutionOutput(
        case_id=case_id,
        assessment=Assessment(
            primary_issue=issue,
            case_status="action_required" if refund > 0 else "no_action",
            confidence=1.0,
        ),
        affected_entities=AffectedEntities(
            order_ids=[fulfillment.order_id], item_ids=fulfillment.item_ids,
            seller_ids=fulfillment.seller_ids, payment_ids=payment.payment_ids,
        ),
        root_cause_analysis=RootCauseAnalysis(
            ranked_causes=[RankedCause(cause_code=cause, rank=1)], responsible_parties=parties,
        ),
        evidence_ids=evidence[:10],
        financial_resolution=FinancialResolution(
            item_total_brl=fulfillment.item_total_brl, freight_total_brl=fulfillment.freight_total_brl,
            payment_total_brl=payment.payment_total_brl, recommended_refund_brl=refund,
        ),
        resolution_actions=[action],
    )
