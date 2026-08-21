"""Jumia Product Update Payload 构建器：在创建 payload 基础上增加 seller_sku 定位目标商品。"""
from __future__ import annotations

from src.jumia.api.product_create import build_product_payload
from src.models.product import Product


def build_product_update_payload(product: Product, seller_sku: str = "") -> dict:
    """生成更新 payload：创建字段 + seller_sku（用于定位要更新的商品）。"""
    payload = build_product_payload(product)
    payload["seller_sku"] = seller_sku or product.sku or ""
    return payload
