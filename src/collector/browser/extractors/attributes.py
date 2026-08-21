"""商品属性提取（材质 / 规格 / 参数）。识别不到返回 None，绝不伪造。"""
from __future__ import annotations

from typing import List, Optional

from src.collector.browser.extractor import BaseExtractor, HtmlDoc

# 常见 itemprop 属性键
_ITEMPROP_KEYS = ("material", "brand", "model", "weight", "dimensions", "color", "size", "power", "capacity")


def _descendants(node, name: str) -> List:
    """递归收集后代中指定标签名的节点。"""
    out: List = []
    for child in node.children:
        if child.name == name:
            out.append(child)
        out.extend(_descendants(child, name))
    return out


class AttributeExtractor(BaseExtractor):
    """提取材质/规格/参数：schema.org itemprop + 规格表（<th>/<td> 键值对）。"""

    def extract(self, doc: HtmlDoc, base_url: str = "") -> Optional[dict]:
        result: dict = {}

        # 1) itemprop 属性
        for prop in _ITEMPROP_KEYS:
            node = doc.by_itemprop(prop)
            if node is not None:
                text = doc.text_of(node).strip()
                if text:
                    result[prop] = text

        # 2) 规格表：遍历 <table> 内的 <tr>，取每行 th/td 作为键值对
        for table in doc.find_all("table"):
            for tr in _descendants(table, "tr"):
                heads = _descendants(tr, "th")
                cells = _descendants(tr, "td")
                key = doc.text_of(heads[0]).strip() if heads else ""
                val = doc.text_of(cells[0]).strip() if cells else ""
                if not key and len(cells) >= 2:
                    key = doc.text_of(cells[0]).strip()
                    val = doc.text_of(cells[1]).strip()
                if key and val:
                    result.setdefault(key, val)

        return result or None
