"""类目匹配（P2-2 升级：两阶段）。

阶段一：AI 商品理解（产品类型）—— 真实 LLM（provider 非 mock）或关键词确定性兜底。
阶段二：映射到 Jumia 类目树。

兼容说明：
- ``match(product) -> (category_name, confidence)`` 保留旧签名，供 pipeline 等调用方继续使用。
- ``match_detail(product) -> JumiaCategoryMatch`` 返回完整结构（category_id / name / confidence / reason）。
"""
from __future__ import annotations

from typing import Tuple

from src.jumia.category.category_matcher import JumiaCategoryMatch
from src.jumia.category.category_matcher import CategoryMatcher as JumiaCategoryMatcher
from src.models.product import Product


class CategoryMatcher:
    def __init__(self, provider: str = "mock"):
        self.provider = provider

        inner_provider = None
        if provider and provider != "mock":
            from src.ai.providers import get_provider

            inner_provider = get_provider(provider)

        self._inner = JumiaCategoryMatcher(provider=inner_provider)

    def match(self, product: Product) -> Tuple[str, float]:
        """返回 (category_name, confidence)，保持旧调用方兼容。"""
        m = self._inner.match(product)
        return m.category_name, m.confidence

    def match_detail(self, product: Product) -> JumiaCategoryMatch:
        """返回完整匹配结构（含 category_id 等）。"""
        return self._inner.match(product)
