"""标题优化（本地启发式，无需 API）。

MVP 阶段使用规则清洗 + 基础优化，保证 dry-run 可演示。
接入真实 LLM 后，在 config.ai.provider 切换实现，函数签名保持不变。
"""
from __future__ import annotations

import re

from src.models.product import Product


class TitleOptimizer:
    def __init__(self, provider: str = "mock"):
        self.provider = provider

    def optimize(self, product: Product) -> Product:
        """清洗并生成英文标题 / Jumia 商品名。"""
        base = product.title_cn or product.title_en or ""
        if not base:
            return product

        cleaned = self._clean(base)
        title_en = self._mock_title_en(cleaned)
        # mock 阶段无法真正翻译中文；若结果仍含中文，明确标记为草稿，避免误导。
        if self.provider == "mock" and _contains_cjk(title_en):
            title_en = f"[EN-draft] {title_en}"
        product.title_en = title_en
        product.product_name = self._shorten(title_en, max_len=120)
        return product

    @staticmethod
    def _clean(text: str) -> str:
        text = re.sub(r"\s+", " ", text).strip()
        text = text.strip(" -_|/")
        return text

    @staticmethod
    def _mock_title_en(text: str) -> str:
        """mock：去除中文括号、各单词首字母大写。真实实现可调用翻译/LLM。"""
        text = re.sub(r"[【】\[\]（）()]", " ", text)
        words = text.split()
        titled = " ".join(w[:1].upper() + w[1:] if w else w for w in words)
        return titled

    @staticmethod
    def _shorten(text: str, max_len: int = 120) -> str:
        if len(text) <= max_len:
            return text
        return text[:max_len].rsplit(" ", 1)[0] + " …"


def shorten(text: str, max_len: int = 120) -> str:
    """公开工具：按词截断到 max_len（供 pipeline 生成 product_name 复用）。"""
    return TitleOptimizer._shorten(text, max_len)


def _contains_cjk(text: str) -> bool:
    """判断文本是否含中日韩字符（用于检测是否仍为中文）。"""
    return bool(re.search(r"[\u4e00-\u9fff]", text))
