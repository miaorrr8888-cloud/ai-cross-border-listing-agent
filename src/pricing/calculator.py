"""售价建议计算器。

公式（反向推导，保证目标利润率与平台佣金）：
    售价 = 总成本 / (1 - 佣金率 - 目标利润率)

示例：
    采购 20 RMB + 物流 15 RMB = 总成本 35
    佣金率 15% + 目标利润 30%  -> 售价 = 35 / 0.55 ≈ 63.64 RMB
"""
from __future__ import annotations

from dataclasses import dataclass

from src.pricing.cost import total_cost
from src.pricing.profit import margin, profit


@dataclass
class PricePlan:
    sale_price: float
    total_cost: float
    commission_rate: float
    commission_amount: float
    target_margin: float
    profit: float
    actual_margin: float
    currency: str


def recommend_price(
    purchase_price: float,
    shipping: float = 0.0,
    commission_rate: float = 0.15,
    target_margin: float = 0.30,
    currency: str = "RMB",
    other: float = 0.0,
) -> PricePlan:
    """根据成本/物流/佣金/目标利润，返回建议售价与明细。"""
    total = total_cost(purchase_price, shipping, other)
    denom = 1 - commission_rate - target_margin
    if denom <= 0:
        raise ValueError(f"利润率 + 佣金率 必须小于 1（当前合计 {denom:.2f}）")

    sale = total / denom
    commission_amount = round(sale * commission_rate, 2)
    prof = profit(sale, total)
    act = margin(prof, sale)
    return PricePlan(
        sale_price=round(sale, 2),
        total_cost=total,
        commission_rate=commission_rate,
        commission_amount=commission_amount,
        target_margin=target_margin,
        profit=prof,
        actual_margin=act,
        currency=currency,
    )
