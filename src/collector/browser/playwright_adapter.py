"""Playwright 封装（headless / 等待加载 / 异常处理 / 不保存登录信息）。

Playwright 为可选依赖：未安装时在实例化阶段抛出明确的 CollectionError，
绝不静默失败、绝不伪造采集结果。
"""
from __future__ import annotations

from typing import List, Optional

from src.collector.browser.browser_client import CollectionError


class PlaywrightAdapter:
    """封装 Playwright 同步 API，管理浏览器生命周期。"""

    def __init__(self, headless: bool = True, timeout: int = 30000):
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as e:
            raise CollectionError(
                "未安装 Playwright，无法真实采集网页。请先执行："
                "pip install playwright && playwright install chromium。"
                "（未安装时不返回任何假数据，而是明确报错。）"
            ) from e

        self._sync_playwright = sync_playwright
        self._headless = headless
        self._timeout = timeout
        self._pw = None
        self._browser = None
        self._context = None
        self._page = None

    def open(self, url: str) -> None:
        try:
            self._pw = self._sync_playwright().start()
            self._browser = self._pw.chromium.launch(headless=self._headless)
            # 使用一次性 context，不持久化 cookie / localStorage / 登录态
            self._context = self._browser.new_context()
            self._page = self._context.new_page()
            self._page.goto(url, wait_until="load", timeout=self._timeout)
            # 等待页面稳定加载（网络空闲）
            self._page.wait_for_load_state("networkidle", timeout=self._timeout)
        except Exception as e:
            self.close()
            raise CollectionError(f"浏览器打开页面失败（{url}）：{e}") from e

    def html(self) -> str:
        return self._page.content()

    def title(self) -> Optional[str]:
        return self._page.title()

    def images(self) -> List[str]:
        return self._page.eval_on_selector_all(
            "img",
            "els => els.map(e => e.src || (e.getAttribute('srcset') || '').split(' ')[0]).filter(Boolean)",
        )

    def close(self) -> None:
        for closer in (
            lambda: self._context and self._context.close(),
            lambda: self._browser and self._browser.close(),
            lambda: self._pw and self._pw.stop(),
        ):
            try:
                closer()
            except Exception:
                pass
        self._page = None
        self._context = None
        self._browser = None
        self._pw = None
