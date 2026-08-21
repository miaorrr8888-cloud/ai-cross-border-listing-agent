"""通用 URL 解析框架（P2-1 升级：接入浏览器采集层）。

流程：URL → 识别平台 → BrowserCollector → Product Schema。

- 支持平台：1688 / 淘宝 / Amazon / AliExpress（浏览器采集）。
- 其他平台：返回 ``unsupported``。
- 默认 dry-run：``parse_url`` 不主动拉起浏览器；显式传 ``browser_client``
  或调用 ``collect_url`` 才触发真实采集。
- 采集失败抛 ``CollectionError``，绝不伪造商品数据。
"""
from __future__ import annotations

import importlib.util
import os
from typing import Optional
from urllib.parse import urlparse

from src.collector.base_collector import NEEDS_BROWSER, UNSUPPORTED, ParseResult
from src.collector.browser import BrowserClient, CollectionError
from src.models.product import Product

# 平台域名 -> 平台标识
PLATFORM_MAP = {
    "1688.com": "1688",
    "taobao.com": "taobao",
    "tmall.com": "tmall",
    "aliexpress.com": "aliexpress",
    "amazon.com": "amazon",
    "amazon.": "amazon",
    "shopify.com": "shopify",
}

# 浏览器采集支持的平台（P2-1 范围）
SUPPORTED_BROWSER_PLATFORMS = {"1688", "taobao", "amazon", "aliexpress"}


def detect_platform(url: str) -> str:
    """根据 URL 域名识别平台。无法识别时返回 'generic'。"""
    host = (urlparse(url).netloc or "").lower()
    for key, name in PLATFORM_MAP.items():
        if key in host:
            return name
    return "generic"


def _load_1688_collector():
    """1688_collector.py 以数字开头，无法用普通 import，改用 importlib 加载。"""
    path = os.path.join(os.path.dirname(__file__), "1688_collector.py")
    spec = importlib.util.spec_from_file_location("collector_1688_mod", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.Collector1688


def parse_url(
    url: str,
    config: Optional[dict] = None,
    browser_client: Optional[BrowserClient] = None,
) -> ParseResult:
    """解析商品 URL：识别平台并返回 ParseResult。

    - 支持平台 + 显式 ``browser_client`` → 走浏览器真实采集（返回 Product）。
    - 支持平台 + 无 ``browser_client`` → 返回 ``needs_browser_plugin``（dry-run 默认，
      不主动拉起浏览器）。
    - 其他平台 → 返回 ``unsupported``。
    """
    platform = detect_platform(url)

    if platform not in SUPPORTED_BROWSER_PLATFORMS:
        return ParseResult(
            status=UNSUPPORTED,
            platform=platform,
            message=(
                f"暂不支持平台「{platform}」的浏览器采集"
                f"（当前支持：{', '.join(sorted(SUPPORTED_BROWSER_PLATFORMS))}）。"
                "未生成任何假数据，请改用 --input 提供 JSON / Excel。"
            ),
        )

    if browser_client is not None:
        from src.collector.browser_collector import BrowserProductCollector

        return BrowserProductCollector(browser_client=browser_client, config=config).collect(url)

    return ParseResult(
        status=NEEDS_BROWSER,
        platform=platform,
        message=(
            f"平台「{platform}」已接入浏览器采集层（BrowserProductCollector）。"
            "默认 dry-run 不主动拉起浏览器；请显式传入 browser_client 或调用 collect_url() 真实采集。"
            "未生成任何假数据。"
        ),
    )


def collect_url(
    url: str,
    config: Optional[dict] = None,
    browser_client: Optional[BrowserClient] = None,
) -> ParseResult:
    """显式执行浏览器真实采集（支持平台 → Product；其他平台 → unsupported）。"""
    from src.collector.browser_collector import BrowserProductCollector

    return BrowserProductCollector(browser_client=browser_client, config=config).collect(url)


__all__ = [
    "PLATFORM_MAP",
    "SUPPORTED_BROWSER_PLATFORMS",
    "detect_platform",
    "parse_url",
    "collect_url",
    "BrowserProductCollector",
    "CollectionError",
]
