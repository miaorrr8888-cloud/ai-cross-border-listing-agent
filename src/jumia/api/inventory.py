"""Jumia Inventory Payload：库存更新结构。

P3-2-B-2 新增 ``update_inventory()`` 函数：通过 ``JumiaHttpClient.put()`` 发送真实请求。
"""
from __future__ import annotations


def build_inventory_payload(seller_sku: str, stock: int) -> dict:
    """生成库存更新 payload：seller_sku + stock（quantity 与 stock 保持一致）。"""
    qty = int(stock or 0)
    return {
        "seller_sku": seller_sku or "",
        "stock": qty,
        "quantity": qty,
    }


def update_inventory(http_client, seller_sku: str, stock: int):
    """发送库存更新请求：PUT /inventory。

    通过 ``http_client.put()`` 发送，返回 ``ParsedResponse``。
    - dry-run 模式：返回请求预览（不发送 HTTP）。
    - 真实模式：发送 HTTP 请求（需 token + transport）。
    """
    payload = build_inventory_payload(seller_sku, stock)
    return http_client.put("/inventory", payload)
