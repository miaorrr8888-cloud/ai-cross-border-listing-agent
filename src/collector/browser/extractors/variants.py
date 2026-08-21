"""商品变体提取（颜色 / 尺寸 / SKU）。识别不到返回 None，绝不伪造。"""
from __future__ import annotations

from typing import Optional

from src.collector.browser.extractor import BaseExtractor, HtmlDoc


class VariantExtractor(BaseExtractor):
    """提取颜色/尺寸/SKU：优先 schema.org itemprop，兜底 data-* 属性。"""

    def extract(self, doc: HtmlDoc, base_url: str = "") -> Optional[dict]:
        result: dict = {}

        for prop, key, is_list in (
            ("color", "colors", True),
            ("size", "sizes", True),
            ("sku", "sku", False),
        ):
            node = doc.by_itemprop(prop)
            if node is not None:
                text = doc.text_of(node).strip()
                if text:
                    if is_list:
                        result.setdefault(key, []).append(text)
                    else:
                        result[key] = text

        # 兜底：扫描 data-* 属性
        for node in doc.iter():
            for attr, val in node.attrs.items():
                if not val:
                    continue
                if attr in ("data-sku", "sku"):
                    result.setdefault("sku", val)
                elif attr in ("data-color",) or attr.endswith("color"):
                    result.setdefault("colors", []).append(val)
                elif attr in ("data-size",) or attr.endswith("size"):
                    result.setdefault("sizes", []).append(val)

        # 去重
        for key in ("colors", "sizes"):
            if key in result:
                result[key] = list(dict.fromkeys(result[key]))

        return result or None
