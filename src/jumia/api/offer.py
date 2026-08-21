"""Jumia Offer Payload：价格 / 货币 / 库存 / seller_sku。

P3-2-B-2 新增 ``create_offer()`` 函数：通过 ``JumiaHttpClient.post()`` 发送真实请求。
"""
from __future__ import annotations

from typing import Optional

from src.models.product import Product


def _suggested_price(product: Product) -> float:
    """取建议售价：优先 _suggested_price（定价模块写入），其次采集售价，最后成本价。"""
    sugg = product.attributes.get("_suggested_price")
    if sugg:
        return float(sugg)
    if product.price:
        return float(product.price)
    return float(product.cost_price or 0.0)


def build_offer_payload(
    product: Product,
    sale_price: Optional[float] = None,
    stock: Optional[int] = None,
    currency: Optional[str] = None,
) -> dict:
    """生成 Offer payload（dry-run，不发送请求）。"""
    return {
        "price": sale_price if sale_price is not None else _suggested_price(product),
        "currency": currency or product.price_currency or product.currency or "USD",
        "stock": stock if stock is not None else int(product.attributes.get("stock", 0) or 0),
        "seller_sku": product.sku or "",
    }


def create_offer(
    http_client,
    product: Product,
    sale_price: Optional[float] = None,
    stock: Optional[int] = None,
    currency: Optional[str] = None,
):
    """发送 Offer 创建请求：POST /offers。

    通过 ``http_client.post()`` 发送，返回 ``ParsedResponse``。
    - dry-run 模式：返回请求预览（不发送 HTTP）。
    - 真实模式：发送 HTTP 请求（需 token + transport）。
    """
    payload = build_offer_payload(product, sale_price, stock, currency)
    return http_client.post("/offers", payload)
