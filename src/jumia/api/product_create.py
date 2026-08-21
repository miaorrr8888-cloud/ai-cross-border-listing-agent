"""Jumia Product Payload 构建器：Product → payload（dry-run，不发送请求）。

P3-2-B-2 新增 ``create_product()`` 函数：通过 ``JumiaHttpClient.post()`` 发送真实请求。
"""
from __future__ import annotations

from src.models.product import Product


def build_product_payload(product: Product) -> dict:
    """把统一 Product 对象映射为 Jumia Product 创建 payload。

    字段：name / description / category_id / attributes / images / variants。
    缺失字段填空值（不伪造），由 payload_validator 负责校验。
    """
    return {
        "name": product.product_name or product.title_en or product.title_cn or "",
        "description": product.long_description or product.description or "",
        "category_id": product.category_id or "",
        "attributes": dict(product.attributes or {}),
        "images": list(product.images or []),
        "variants": dict(product.variants) if isinstance(product.variants, dict) else {},
    }


def create_product(http_client, product: Product):
    """发送商品创建请求：POST /products。

    通过 ``http_client.post()`` 发送，返回 ``ParsedResponse``。
    - dry-run 模式：返回请求预览（不发送 HTTP）。
    - 真实模式：发送 HTTP 请求（需 token + transport）。

    安全：上层应通过 ``JumiaUploader`` + ``UploadGuard`` 控制上传权限。
    """
    payload = build_product_payload(product)
    return http_client.post("/products", payload)
