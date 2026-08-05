from __future__ import annotations

from decimal import Decimal

from src.data_repository import DataRepository, money
from src.schemas import PaymentFacts


def build_payment_facts(repository: DataRepository, order_id: str) -> PaymentFacts:
    rows = repository.payments(order_id)
    item_rows = repository.items(order_id)
    payment_total = sum((money(row["payment_value"]) for row in rows), Decimal("0.00"))
    expected_total = sum((money(row["price"]) + money(row["freight_value"]) for row in item_rows), Decimal("0.00"))
    delta = abs(payment_total - expected_total)
    return PaymentFacts(
        order_id=order_id,
        payment_ids=[f"{order_id}:{row['payment_sequential']}" for row in rows],
        payment_row_count=len(rows),
        payment_total_brl=payment_total,
        reconciliation_delta_brl=delta,
        payment_matches=delta <= Decimal("0.10"),
        source_refs=[f"payment:{order_id}:{row['payment_sequential']}" for row in rows],
    )
