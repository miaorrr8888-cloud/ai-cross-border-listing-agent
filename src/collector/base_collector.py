"""采集器基类与解析结果（P1 真实输入层）。

设计约束（重要）：
- 无法抓取真实网页时，统一返回状态 ``needs_browser_plugin``，并给出明确提示。
- **绝不生成假数据**：没有真实来源就不编造标题/价格/图片。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from src.models.product import Product

# 解析状态常量
OK = "ok"
NEEDS_BROWSER = "needs_browser_plugin"
UNSUPPORTED = "unsupported"


@dataclass
class ParseResult:
    status: str
    platform: str = "generic"
    product: Optional[Product] = None
    message: str = ""


class BaseCollector(ABC):
    platform: str = "generic"

    def supports(self, url: str) -> bool:
        return self.platform in (url or "").lower()

    @abstractmethod
    def collect(self, url: str) -> ParseResult:
        """采集单个商品 URL，返回 ParseResult。"""
        ...

    def needs_browser(self, url: str, extra: str = "") -> ParseResult:
        """统一返回「需要浏览器采集插件」状态，不生成任何假数据。"""
        msg = (
            "需要浏览器采集插件：当前环境无法抓取真实网页，未生成任何假数据。"
            "请安装采集插件，或使用 --input 提供商品 JSON / Excel 继续。"
        )
        if extra:
            msg = f"{extra} {msg}"
        return ParseResult(status=NEEDS_BROWSER, platform=self.platform, message=msg)
