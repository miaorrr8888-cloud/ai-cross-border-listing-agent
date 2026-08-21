"""Jumia 类目匹配：两阶段。

阶段一（AI 商品理解）：把商品理解为规范「产品类型」（如 USB桌面风扇 → Portable Fan）。
    - 真实 LLM（provider 非 mock）时调用 LLM；
    - mock / 无 LLM 时用关键词确定性兜底。

阶段二（映射）：产品类型 → Jumia 类目树，返回 category_id / category_name / confidence / reason。

识别不到就回退到 General Merchandise（confidence 0），不伪造匹配。
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Optional

from src.jumia.category.attribute_schema import AttributeSchema
from src.jumia.category.category_tree import CategoryTree
from src.models.product import Product


@dataclass
class JumiaCategoryMatch:
    category_id: str
    category_name: str
    confidence: float
    reason: str

    def to_dict(self) -> dict:
        return asdict(self)


# 产品类型关键词（阶段一兜底）
PRODUCT_TYPE_KEYWORDS = {
    "Portable Fan": ["portable fan", "desk fan", "usb fan", "风扇", "桌面风扇", "小风扇"],
    "Earphones": ["earphone", "earbud", "headphone", "headset", "耳机", "蓝牙耳机"],
    "Smartphone": ["smartphone", "phone", "手机", "智能手机"],
    "Charger": ["charger", "power adapter", "充电器", "电源适配器"],
    "Cable": ["cable", "充电线", "数据线", "usb cable"],
    "Dress": ["dress", "连衣裙", "裙子"],
    "Shoes": ["shoe", "sneaker", "sandal", "鞋", "运动鞋"],
    "Perfume": ["perfume", "fragrance", "eau de toilette", "香水"],
    "Makeup": ["makeup", "cosmetic", "lipstick", "美妆", "口红", "化妆"],
}

# 产品类型 → Jumia 类目 ID（阶段二）
PRODUCT_TYPE_TO_CATEGORY = {
    "Portable Fan": "home_fans",
    "Earphones": "electronics_audio",
    "Smartphone": "electronics_phones",
    "Charger": "electronics",
    "Cable": "electronics",
    "Dress": "fashion_women",
    "Shoes": "fashion_shoes",
    "Perfume": "beauty_fragrance",
    "Makeup": "beauty",
}


class CategoryMatcher:
    """两阶段类目匹配器。"""

    def __init__(self, tree: Optional[CategoryTree] = None, provider=None, attribute_schema: Optional[AttributeSchema] = None):
        self.tree = tree or CategoryTree()
        self.provider = provider  # 可选 BaseAIProvider（真实 LLM）；None=mock
        self.attribute_schema = attribute_schema or AttributeSchema()

    def match(self, product: Product) -> JumiaCategoryMatch:
        text = self._build_text(product)

        # 阶段一：AI 商品理解 → 产品类型
        product_type = self._understand_product(product, text)

        if product_type:
            node = self.tree.get(PRODUCT_TYPE_TO_CATEGORY.get(product_type, ""))
            if node is not None:
                return JumiaCategoryMatch(
                    category_id=node.id,
                    category_name=node.name,
                    confidence=self._confidence(text, product_type),
                    reason=f"产品类型「{product_type}」→ 映射到 Jumia 类目「{node.name}」",
                )

        # 兜底：识别不到不伪造
        return JumiaCategoryMatch(
            category_id="general_merchandise",
            category_name="General Merchandise",
            confidence=0.0,
            reason="未能识别产品类型，回退到通用类目（不伪造匹配）",
        )

    # ---------- 阶段一：AI 商品理解 ----------
    def _understand_product(self, product: Product, text: str) -> str:
        # 1) 关键词确定性兜底（mock / 无 LLM 也可靠）
        ptype = self._classify_by_keywords(text)
        if ptype:
            return ptype
        # 2) 真实 LLM（非 mock）
        if self.provider is not None and getattr(self.provider, "name", "") != "mock":
            raw = self.provider.generate_text(self._llm_prompt(text))
            ptype = self._normalize_type(raw)
            if ptype:
                return ptype
        return ""

    def _classify_by_keywords(self, text: str) -> str:
        best, best_hits = "", 0
        for ptype, kws in PRODUCT_TYPE_KEYWORDS.items():
            hits = sum(1 for kw in kws if _kw_matches(kw, text))
            if hits > best_hits:
                best, best_hits = ptype, hits
        return best

    def _llm_prompt(self, text: str) -> str:
        types = "、".join(PRODUCT_TYPE_KEYWORDS.keys())
        return f"把以下商品归类为以下产品类型之一（只返回类型名，不要解释）：{types}。\n\n{text}"

    def _normalize_type(self, raw: str) -> str:
        raw = (raw or "").strip().strip("。.\"'“” ")
        low = raw.lower()
        for ptype in PRODUCT_TYPE_KEYWORDS:
            if low == ptype.lower() or ptype.lower() in low:
                return ptype
        return ""

    # ---------- 工具 ----------
    def _confidence(self, text: str, product_type: str) -> float:
        hits = sum(1 for kw in PRODUCT_TYPE_KEYWORDS.get(product_type, []) if _kw_matches(kw, text))
        return min(0.95, 0.5 + 0.15 * hits)

    @staticmethod
    def _build_text(product: Product) -> str:
        parts = [product.title_en, product.title_cn, product.description, " ".join(product.keywords)]
        return " ".join(filter(None, parts)).lower()


def _kw_matches(keyword: str, text: str) -> bool:
    """关键词命中：拉丁词用词边界，中日韩文用子串。"""
    kw = keyword.lower()
    if re.search(r"[\u4e00-\u9fff]", kw):
        return kw in text
    return bool(re.search(rf"\b{re.escape(kw)}\b", text))
