"""商品标题提取。识别不到返回 None，绝不伪造。"""
from __future__ import annotations

from typing import Optional

from src.collector.browser.extractor import BaseExtractor, HtmlDoc


class TitleExtractor(BaseExtractor):
    """按优先级提取标题：og:title > <title> > <h1> > itemprop=name。"""

    def extract(self, doc: HtmlDoc, base_url: str = "") -> Optional[str]:
        for candidate in (doc.meta.get("og:title"), doc.title):
            if candidate and candidate.strip():
                return candidate.strip()

        h1 = doc.find("h1")
        if h1:
            text = doc.text_of(h1).strip()
            if text:
                return text

        name_node = doc.by_itemprop("name")
        if name_node:
            text = doc.text_of(name_node).strip()
            if text:
                return text

        return None
