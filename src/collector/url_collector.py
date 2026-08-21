"""URL 采集器（MVP dry-run：只识别来源平台，不抓取页面）。

设计说明：
- 输入是「任意商品 URL」，不限制 1688。通过域名识别平台。
- MVP 不联网抓取，仅生成占位商品，预留真实解析器接口：
  未来在 `collect()` 中根据 source_platform 调用对应解析器，
  返回包含标题/图片/价格的完整 Product。
"""
from __future__ import annotations

from urllib.parse import urlparse

from src.models.product import Product

# 域名关键字 -> 平台名。可自由扩展。
PLATFORM_MAP = {
    "1688.com": "1688",
    "taobao.com": "taobao",
    "tmall.com": "tmall",
    "aliexpress.com": "aliexpress",
    "amazon.": "amazon",
    "shopify.com": "shopify",
    "ebay.com": "ebay",
}


def detect_platform(url: str) -> str:
    """根据 URL 域名识别来源平台；未知返回 generic。"""
    host = (urlparse(url).netloc or "").lower()
    for key, name in PLATFORM_MAP.items():
        if key in host:
            return name
    return "generic"


def collect(url: str, dry_run: bool = True) -> Product:
    """从 URL 生成一个 Product。

    dry_run=True（默认）：不抓取，仅记录 URL + 平台 + 占位标题。
    dry_run=False（未来）：调用真实解析器填充标题/图片/价格。
    """
    platform = detect_platform(url)
    product = Product(source_url=url, source_platform=platform)
    if dry_run:
        # MVP 占位：接入真实解析器后此标题会自动被真实数据覆盖
        product.title_cn = "示例商品（dry-run 占位，接入解析器后自动填充）"
    return product
