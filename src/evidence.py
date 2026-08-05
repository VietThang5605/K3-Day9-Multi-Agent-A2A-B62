from __future__ import annotations

import re

from src.data_repository import DataRepository


_ORDER = re.compile(r"^order:([a-f0-9]{32})$")
_ITEM = re.compile(r"^item:([a-f0-9]{32}):(\d+)$")
_PAYMENT = re.compile(r"^payment:([a-f0-9]{32}):(\d+)$")
_SELLER = re.compile(r"^seller:([a-f0-9]{32})$")
_POLICY = re.compile(r"^policy:[A-Z_]+$")


def evidence_exists(evidence_id: str, repository: DataRepository) -> bool:
    if match := _ORDER.fullmatch(evidence_id):
        return match.group(1) in repository.orders
    if match := _ITEM.fullmatch(evidence_id):
        return any(str(row["order_item_id"]) == match.group(2) for row in repository.items_by_order.get(match.group(1), []))
    if match := _PAYMENT.fullmatch(evidence_id):
        return any(str(row["payment_sequential"]) == match.group(2) for row in repository.payments_by_order.get(match.group(1), []))
    if match := _SELLER.fullmatch(evidence_id):
        return match.group(1) in repository.seller_ids
    return bool(_POLICY.fullmatch(evidence_id))
