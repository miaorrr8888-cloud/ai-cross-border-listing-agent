"""1688 采集器（P1：无真实抓取能力，返回 needs_browser_plugin）。

说明：
- 1688 商品页通常需要登录态 / 有反爬，无法在无头环境直接抓取。
- 因此本采集器**不抓取、不编造**，明确告知需要浏览器采集插件。
- 未来接入真实抓取时，只需在此实现 ``collect`` 的真实逻辑（复用 ParseResult）。
"""
from __future__ import annotations

from src.collector.base_collector import BaseCollector, NEEDS_BROWSER, ParseResult


class Collector1688(BaseCollector):
    platform = "1688"

    def supports(self, url: str) -> bool:
        return "1688.com" in (url or "").lower()

    def collect(self, url: str) -> ParseResult:
        return self.needs_browser(
            url,
            extra="1688 商品需要浏览器采集插件才能抓取（登录态 / 反爬）。",
        )
