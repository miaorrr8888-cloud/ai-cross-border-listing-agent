"""BrowserProductCollector：用浏览器采集真实网页，填充统一 Product Schema。

输入：商品 URL（或离线 HTML，用于测试/解析）。
输出：ParseResult，其中 product 为填充了 source_url / source_platform /
      title / images / price / attributes / variants 的 Product 对象。

约束：识别不到就返回 None（不伪造）；采集失败抛 CollectionError（明确错误）。
"""
from __future__ import annotations

from typing import Optional

from src.collector.base_collector import OK, UNSUPPORTED, BaseCollector, ParseResult
from src.collector.browser import (
    BrowserClient,
    CollectionError,
    ContentExtractor,
    HtmlDoc,
    PlaywrightBrowserClient,
    StaticHtmlClient,
)
from src.collector.url_parser import SUPPORTED_BROWSER_PLATFORMS, detect_platform
from src.models.product import Product


class BrowserProductCollector(BaseCollector):
    platform = "browser"

    def __init__(self, browser_client: Optional[BrowserClient] = None, config: Optional[dict] = None):
        self._browser_client = browser_client
        self._config = config or {}

    def supports(self, url: str) -> bool:
        return detect_platform(url) in SUPPORTED_BROWSER_PLATFORMS

    def collect(self, url: str, html: Optional[str] = None) -> ParseResult:
        platform = detect_platform(url)
        if platform not in SUPPORTED_BROWSER_PLATFORMS:
            return ParseResult(
                status=UNSUPPORTED,
                platform=platform,
                message=(
                    f"暂不支持平台「{platform}」的浏览器采集"
                    f"（当前支持：{', '.join(sorted(SUPPORTED_BROWSER_PLATFORMS))}）。"
                ),
            )

        client = self._resolve_client(html)
        try:
            if html is None:
                client.open_page(url)

            doc = HtmlDoc(client.get_html(), base_url=url)
            extracted = ContentExtractor().extract_all(doc, base_url=url)

            price = extracted.get("price") or {}
            product = Product(
                source_url=url,
                source_platform=platform,
                title_cn=extracted.get("title") or "",
                title_en=extracted.get("title") or "",
                images=extracted.get("images") or [],
                price=price.get("value") or 0.0,
                price_currency=price.get("currency") or "",
                attributes=extracted.get("attributes") or {},
                variants=extracted.get("variants") or {},
            )
            return ParseResult(status=OK, platform=platform, product=product, message="浏览器采集成功。")
        except CollectionError:
            raise
        except Exception as e:  # 采集失败必须返回明确错误
            raise CollectionError(f"浏览器采集失败（{platform} {url}）：{e}") from e
        finally:
            try:
                client.close()
            except Exception:
                pass

    def _resolve_client(self, html: Optional[str]) -> BrowserClient:
        if self._browser_client is not None:
            return self._browser_client
        if html is not None:
            return StaticHtmlClient(html=html)
        browser_cfg = self._config.get("browser", {})
        return PlaywrightBrowserClient(
            headless=browser_cfg.get("headless", True),
            timeout=browser_cfg.get("timeout", 30000),
        )
