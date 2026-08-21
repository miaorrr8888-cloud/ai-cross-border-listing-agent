"""图片采集器（MVP：仅支持传入图片 URL 列表，不下载）。

未来版本：可根据商品页抓取图片并下载到本地 output/ 目录，
同时把本地路径写回 product.images。
"""
from __future__ import annotations

from typing import List

from src.models.product import Product


def collect_images(product: Product, image_urls: List[str]) -> Product:
    """把图片 URL 列表写入商品。"""
    product.images = list(image_urls)
    return product
