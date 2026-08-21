"""上架上传器（MVP 仅生成上架计划，不真正上传）。"""
from __future__ import annotations

from typing import Any, Dict, Tuple

from src.ai.providers.base import BaseAIProvider
from src.jumia.api_client import JumiaAPIClient
from src.jumia.product_mapper import build_listing
from src.models.product import Product


def upload(
    product: Product,
    client: JumiaAPIClient,
    provider: BaseAIProvider,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """把商品映射为 Listing，并通过 client 生成 dry-run 计划。"""
    listing = build_listing(product, provider)
    result = client.create_product(listing)
    return listing, result
