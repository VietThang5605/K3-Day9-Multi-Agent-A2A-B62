from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

import pandas as pd


MONEY_QUANTUM = Decimal("0.01")


def money(value: Any) -> Decimal:
    """Convert a CSV value to BRL rounded to two decimal places."""
    return Decimal(str(value)).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def _clean(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    return str(value)


@dataclass(frozen=True)
class DataRepository:
    """Read-only indexed view of the four Olist source tables used by policy."""

    orders: dict[str, dict[str, str | None]]
    items_by_order: dict[str, list[dict[str, str | None]]]
    payments_by_order: dict[str, list[dict[str, str | None]]]
    seller_ids: frozenset[str]

    @classmethod
    def from_directory(cls, data_dir: Path) -> "DataRepository":
        def load(name: str) -> list[dict[str, str | None]]:
            frame = pd.read_csv(data_dir / name, dtype=str, keep_default_na=False)
            return [{key: _clean(value) for key, value in row.items()} for row in frame.to_dict("records")]

        order_rows = load("olist_orders_dataset.csv")
        item_rows = load("olist_order_items_dataset.csv")
        payment_rows = load("olist_order_payments_dataset.csv")
        seller_rows = load("olist_sellers_dataset.csv")
        items: dict[str, list[dict[str, str | None]]] = defaultdict(list)
        payments: dict[str, list[dict[str, str | None]]] = defaultdict(list)
        for row in item_rows:
            items[str(row["order_id"])].append(row)
        for row in payment_rows:
            payments[str(row["order_id"])].append(row)
        for rows in (items.values(), payments.values()):
            for group in rows:
                group.sort(key=lambda row: int(row.get("order_item_id") or row.get("payment_sequential") or 0))
        return cls(
            orders={str(row["order_id"]): row for row in order_rows},
            items_by_order=dict(items),
            payments_by_order=dict(payments),
            seller_ids=frozenset(str(row["seller_id"]) for row in seller_rows),
        )

    def order(self, order_id: str) -> dict[str, str | None]:
        try:
            return self.orders[order_id]
        except KeyError as exc:
            raise ValueError(f"Unknown order_id: {order_id}") from exc

    def items(self, order_id: str) -> list[dict[str, str | None]]:
        return self.items_by_order.get(order_id, [])

    def payments(self, order_id: str) -> list[dict[str, str | None]]:
        rows = self.payments_by_order.get(order_id, [])
        if not rows:
            raise ValueError(f"Order has no payment rows: {order_id}")
        return rows
