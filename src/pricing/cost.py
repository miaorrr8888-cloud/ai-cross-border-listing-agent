"""成本核算：采购价 + 物流 + 其他费用。"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CostBreakdown:
    purchase_price: float
    shipping: float
    other: float
    total: float


def total_cost(purchase_price: float, shipping: float = 0.0, other: float = 0.0) -> float:
    """总成本 = 采购价 + 物流 + 其他费用。"""
    return round(purchase_price + shipping + other, 2)


def breakdown(purchase_price: float, shipping: float = 0.0, other: float = 0.0) -> CostBreakdown:
    return CostBreakdown(
        purchase_price=purchase_price,
        shipping=shipping,
        other=other,
        total=round(purchase_price + shipping + other, 2),
    )
