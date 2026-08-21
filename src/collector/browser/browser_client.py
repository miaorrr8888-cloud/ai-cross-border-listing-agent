"""统一浏览器接口（BrowserClient）与内存/Playwright 两种实现。

接口：open_page / get_html / get_title / get_images / close。
- StaticHtmlClient：内存静态 HTML，用于 dry-run / 单元测试，不访问网络。
- PlaywrightBrowserClient：封装 Playwright，真实采集网页。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional


class CollectionError(RuntimeError):
    """浏览器采集失败时抛出的明确错误。"""


class BrowserClient(ABC):
    """统一浏览器接口。"""

    @abstractmethod
    def open_page(self, url: str) -> None:
        ...

    @abstractmethod
    def get_html(self) -> str:
        ...

    @abstractmethod
    def get_title(self) -> Optional[str]:
        ...

    @abstractmethod
    def get_images(self) -> List[str]:
        ...

    @abstractmethod
    def close(self) -> None:
        ...


class StaticHtmlClient(BrowserClient):
    """内存静态 HTML 客户端：显式提供 HTML，不联网、不造假（仅用于测试/离线解析）。"""

    def __init__(self, html: str = "", title: Optional[str] = None, images: Optional[List[str]] = None):
        self._html = html or ""
        self._title = title
        self._images = list(images) if images else []
        self._opened = False

    def open_page(self, url: str) -> None:
        self._opened = True

    def get_html(self) -> str:
        return self._html

    def get_title(self) -> Optional[str]:
        if self._title is not None:
            return self._title
        from src.collector.browser.extractor import HtmlDoc

        return HtmlDoc(self._html).title or None

    def get_images(self) -> List[str]:
        return list(self._images)

    def close(self) -> None:
        self._opened = False


class PlaywrightBrowserClient(BrowserClient):
    """封装 Playwright 的浏览器客户端。真实采集网页，headless 默认开启，不保存登录态。"""

    def __init__(self, headless: bool = True, timeout: int = 30000):
        self._headless = headless
        self._timeout = timeout
        self._adapter = None

    def open_page(self, url: str) -> None:
        from src.collector.browser.playwright_adapter import PlaywrightAdapter

        self._adapter = PlaywrightAdapter(headless=self._headless, timeout=self._timeout)
        self._adapter.open(url)

    def get_html(self) -> str:
        if self._adapter is None:
            raise CollectionError("尚未打开页面，请先调用 open_page(url)。")
        return self._adapter.html()

    def get_title(self) -> Optional[str]:
        if self._adapter is None:
            raise CollectionError("尚未打开页面。")
        return self._adapter.title()

    def get_images(self) -> List[str]:
        if self._adapter is None:
            raise CollectionError("尚未打开页面。")
        return self._adapter.images()

    def close(self) -> None:
        if self._adapter is not None:
            self._adapter.close()
            self._adapter = None
