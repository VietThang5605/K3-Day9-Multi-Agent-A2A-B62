from __future__ import annotations

from typing import TypedDict


class CaseGraphState(TypedDict, total=False):
    case_path: str
    case: dict
    case_id: str
    order_id: str
    order_fulfillment_facts: dict
    payment_facts: dict
    candidate_resolution: dict
    verification: dict
    output_path: str
    error: str
