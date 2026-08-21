"""商品价格提取。识别不到返回 None，绝不伪造。"""
from __future__ import annotations

import re
from typing import Optional

from src.collector.browser.extractor import BaseExtractor, HtmlDoc

_NUM_RE = re.compile(r"[\d,]+(?:\.\d+)?")
_CURRENCY_HINTS = {
    "¥": "CNY",
    "￥": "CNY",
    "cny": "CNY",
    "rmb": "CNY",
    "usd": "USD",
    "$": "USD",
    "€": "EUR",
    "eur": "EUR",
}


def _first_number(text: str) -> Optional[float]:
    m = _NUM_RE.search(text or "")
    if not m:
        return None
    return float(m.group(0).replace(",", ""))


def _infer_currency(text: str) -> Optional[str]:
    low = (text or "").lower()
    for hint, cur in _CURRENCY_HINTS.items():
        if hint in low:
            return cur
    return None


class PriceExtractor(BaseExtractor):
    """提取价格，返回 {'value': float, 'currency': str|None}；找不到返回 None。"""

    def extract(self, doc: HtmlDoc, base_url: str = "") -> Optional[dict]:
        amount = doc.meta.get("og:price:amount")
        currency = doc.meta.get("og:price:currency") or doc.meta.get("pricecurrency")

        text = amount
        if not text:
            node = doc.by_itemprop("price")
            text = doc.text_of(node) if node else ""
        if not text:
            node = doc.find(**{"class": "price"})
            text = doc.text_of(node) if node else ""

        value = _first_number(text)
        if value is None:
            return None

        cur = currency or _infer_currency(text) or _infer_currency(doc.html)
        return {"value": value, "currency": cur}
