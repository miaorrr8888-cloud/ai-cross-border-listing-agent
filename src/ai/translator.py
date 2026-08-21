"""多语言生成（本地 mock，无需 API）。

支持：zh-CN / en / fr / ar。
MVP 用占位生成，明确标记为 draft，便于审阅「结构」是否正确；
接入真实翻译 / LLM 后，替换 _translate_real 即可，调用方无感知。
"""
from __future__ import annotations

from src.models.product import Language


class Translator:
    def __init__(self, provider: str = "mock"):
        self.provider = provider

    def translate(self, text: str, target: str) -> str:
        if not text:
            return ""
        if self.provider == "mock":
            return self._mock(text, target)
        return self._translate_real(text, target)

    @staticmethod
    def _mock(text: str, target: str) -> str:
        if target in (Language.EN.value, Language.ZH_CN.value):
            return text  # 英文 / 中文视为已有，原样返回
        tag = {"fr": "FR", "ar": "AR"}.get(target, target.upper())
        return f"[{tag}-draft] {text}"

    @staticmethod
    def _translate_real(text: str, target: str) -> str:
        raise NotImplementedError(
            "真实翻译需要配置 ai.provider 与 api_key，MVP 未启用。"
        )
