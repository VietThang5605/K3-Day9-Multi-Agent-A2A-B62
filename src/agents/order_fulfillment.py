from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from src.data_repository import DataRepository, money
from src.schemas import ItemFact, OrderFulfillmentFacts


def _after(left: str | None, right: str | None) -> bool:
    return bool(left and right and datetime.fromisoformat(left) > datetime.fromisoformat(right))


def build_order_fulfillment_facts(repository: DataRepository, order_id: str) -> OrderFulfillmentFacts:
    order = repository.order(order_id)
    rows = repository.items(order_id)
    items = [
        ItemFact(
            order_item_id=int(row["order_item_id"] or 0),
            seller_id=str(row["seller_id"]),
            shipping_limit_date=str(row["shipping_limit_date"]),
            price_brl=money(row["price"]),
            freight_brl=money(row["freight_value"]),
        )
        for row in rows
    ]
    carrier_date = order["order_delivered_carrier_date"]
    late_sellers = sorted({item.seller_id for item in items if _after(carrier_date, item.shipping_limit_date)})
    return OrderFulfillmentFacts(
        order_id=order_id,
        order_status=str(order["order_status"]),
        delivered_carrier_date=carrier_date,
        delivered_customer_date=order["order_delivered_customer_date"],
        estimated_delivery_date=order["order_estimated_delivery_date"],
        item_ids=[f"{order_id}:{item.order_item_id}" for item in items],
        seller_ids=sorted({item.seller_id for item in items}),
        items=items,
        item_total_brl=sum((item.price_brl for item in items), Decimal("0.00")),
        freight_total_brl=sum((item.freight_brl for item in items), Decimal("0.00")),
        delivery_late=_after(order["order_delivered_customer_date"], order["order_estimated_delivery_date"]),
        late_seller_ids=late_sellers,
        source_refs=["order:" + order_id] + [f"item:{order_id}:{item.order_item_id}" for item in items],
    )
