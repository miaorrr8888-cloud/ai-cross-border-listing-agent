"""利润与利润率计算。"""
from __future__ import annotations


def profit(sale_price: float, total_cost: float) -> float:
    """利润 = 售价 - 总成本。"""
    return round(sale_price - total_cost, 2)


def margin(profit_amount: float, sale_price: float) -> float:
    """利润率 = 利润 / 售价（0~1）。售价<=0 时返回 0。"""
    if sale_price <= 0:
        return 0.0
    return round(profit_amount / sale_price, 4)
