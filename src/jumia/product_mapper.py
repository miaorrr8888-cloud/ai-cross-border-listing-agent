"""将 Product 映射为 Jumia Listing 结构（纯数据转换，不联网）。

输出是后续 uploader / api_client 的请求体草稿。
"""
from __future__ import annotations

import re
from typing import Any, Dict

from src.ai.providers.base import BaseAIProvider
from src.models.product import Language, Product


def build_listing(product: Product, provider: BaseAIProvider) -> Dict[str, Any]:
    """构建 Jumia Listing dict，并回填 product 的多语言字段。"""
    # 长描述兜底
    if not product.long_description:
        product.long_description = product.description

    # 多语言版本
    product.language_versions = {
        Language.ZH_CN.value: {
            "title": product.title_cn,
            "description": product.description,
        },
        Language.EN.value: {
            "title": product.title_en,
            "description": product.long_description,
        },
    }
    # 翻译源使用干净的标题（去掉 mock 阶段的 [EN-draft] 标记），避免标签叠加
    src_title = product.title_en or product.title_cn
    src_title = re.sub(r"^\[EN-draft\]\s*", "", src_title)
    fr_title = provider.translate(src_title, Language.FR.value)
    ar_title = provider.translate(src_title, Language.AR.value)
    product.language_versions[Language.FR.value] = {"title": fr_title, "description": ""}
    product.language_versions[Language.AR.value] = {"title": ar_title, "description": ""}

    # Jumia 描述
    product.short_description = _short(product.long_description)

    return {
        "product_name": product.product_name or product.title_en,
        "category": product.category,
        "brand": product.brand,
        "sku": product.sku,
        "short_description": product.short_description,
        "long_description": product.long_description,
        "keywords": product.keywords,
        "images": product.images,
        "language_versions": product.language_versions,
        "price": {
            "cost_price": product.cost_price,
            "currency": product.currency,
        },
    }


def _short(text: str, max_len: int = 200) -> str:
    text = (text or "").strip()
    return text[:max_len] + ("…" if len(text) > max_len else "")
