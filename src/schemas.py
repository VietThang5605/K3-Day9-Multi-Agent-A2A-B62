from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CustomerRequest(StrictModel):
    language: str
    message: str
    claimed_order_id: str


class CaseInput(StrictModel):
    case_id: str
    opened_at: str
    customer_request: CustomerRequest
    policy_version: Literal["EC_POLICY_V1"]


class ItemFact(StrictModel):
    order_item_id: int
    seller_id: str
    shipping_limit_date: str
    price_brl: Decimal
    freight_brl: Decimal


class OrderFulfillmentFacts(StrictModel):
    order_id: str
    order_status: str
    delivered_carrier_date: str | None
    delivered_customer_date: str | None
    estimated_delivery_date: str | None
    item_ids: list[str] = Field(max_length=5)
    seller_ids: list[str] = Field(max_length=5)
    items: list[ItemFact] = Field(max_length=5)
    item_total_brl: Decimal
    freight_total_brl: Decimal
    delivery_late: bool
    late_seller_ids: list[str] = Field(max_length=3)
    source_refs: list[str] = Field(max_length=10)


class PaymentFacts(StrictModel):
    order_id: str
    payment_ids: list[str] = Field(max_length=5)
    payment_row_count: int
    payment_total_brl: Decimal
    reconciliation_delta_brl: Decimal
    payment_matches: bool
    source_refs: list[str] = Field(max_length=10)


class Assessment(StrictModel):
    primary_issue: Literal[
        "canceled_order_paid",
        "unavailable_order_paid",
        "late_delivery_seller",
        "late_delivery_logistics",
        "valid_split_payment",
        "unsupported_late_claim",
    ]
    case_status: Literal["action_required", "no_action"]
    confidence: float = Field(ge=0, le=1)


class AffectedEntities(StrictModel):
    order_ids: list[str] = Field(max_length=5)
    item_ids: list[str] = Field(max_length=5)
    seller_ids: list[str] = Field(max_length=5)
    payment_ids: list[str] = Field(max_length=5)


class RankedCause(StrictModel):
    cause_code: str
    rank: int = Field(ge=1)


class ResponsibleParty(StrictModel):
    party_type: str
    party_id: str


class RootCauseAnalysis(StrictModel):
    ranked_causes: list[RankedCause] = Field(max_length=3)
    responsible_parties: list[ResponsibleParty] = Field(max_length=3)


class FinancialResolution(StrictModel):
    currency: Literal["BRL"] = "BRL"
    item_total_brl: Decimal
    freight_total_brl: Decimal
    payment_total_brl: Decimal
    recommended_refund_brl: Decimal


class ResolutionOutput(StrictModel):
    case_id: str
    assessment: Assessment
    affected_entities: AffectedEntities
    root_cause_analysis: RootCauseAnalysis
    evidence_ids: list[str] = Field(max_length=10)
    financial_resolution: FinancialResolution
    resolution_actions: list[str] = Field(max_length=5)


class VerificationResult(StrictModel):
    passed: bool
    error_codes: list[str]
    error_messages: list[str]
