"""浏览器采集包：统一浏览器接口 + HTML 解析 + 字段提取。"""
from src.collector.browser.browser_client import (
    BrowserClient,
    CollectionError,
    PlaywrightBrowserClient,
    StaticHtmlClient,
)
from src.collector.browser.extractor import BaseExtractor, ContentExtractor, HtmlDoc
from src.collector.browser.playwright_adapter import PlaywrightAdapter

__all__ = [
    "BrowserClient",
    "CollectionError",
    "PlaywrightBrowserClient",
    "StaticHtmlClient",
    "BaseExtractor",
    "ContentExtractor",
    "HtmlDoc",
    "PlaywrightAdapter",
]
