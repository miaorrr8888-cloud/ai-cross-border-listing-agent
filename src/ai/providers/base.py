"""AI Provider 统一架构（P1）。

统一接口：generate_text() / translate() / optimize_title()
默认 provider = mock（无网络、无 token、纯结构演示）。

真实 provider（openai / deepseek / kimi）在 **缺少 api_key 时显式报错**，
绝不静默发送、绝不预置假 token。接入真实模型只需在 config 填 api_key。
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Optional

from src.models.product import Product


class BaseAIProvider(ABC):
    name = "base"

    def __init__(self, api_key: str = "", model: str = "", base_url: str = ""):
        self.api_key = api_key or ""
        self.model = model or ""
        self.base_url = base_url or ""

    @abstractmethod
    def generate_text(self, prompt: str, **kwargs) -> str:
        """调用模型生成文本，返回字符串。"""
        ...

    def translate(self, text: str, target: str) -> str:
        """将文本翻译为目标语言（target 为语言代码，如 fr / ar / en）。"""
        if not text:
            return ""
        prompt = (
            "You are an e-commerce translator. Translate the following text into "
            f"{target} (language code). Return ONLY the translation, no quotes, "
            "no explanation.\n\n" + text
        )
        return self.generate_text(prompt)

    def optimize_title(self, title_cn: str, title_en: str = "") -> str:
        """基于商品标题生成优化后的英文标题。"""
        base = title_cn or title_en or ""
        if not base:
            return ""
        prompt = (
            "You are a cross-border e-commerce copywriter. Optimize the following "
            "product title for a Jumia listing. Return ONLY the optimized English "
            "title.\n\n" + base
        )
        return self.generate_text(prompt)


class OpenAICompatibleProvider(BaseAIProvider):
    """兼容 OpenAI Chat Completions 协议的 Provider（openai/deepseek/kimi 共用）。"""

    DEFAULT_BASE_URL = "https://api.openai.com/v1"
    DEFAULT_MODEL = "gpt-4o-mini"

    def generate_text(self, prompt: str, temperature: float = 0.3, **kwargs) -> str:
        if not self.api_key:
            raise RuntimeError(
                "调用真实模型需要配置 ai.api_key（请勿使用假 token）。"
            )
        return self._chat(prompt, temperature=temperature)

    def _chat(self, prompt: str, temperature: float = 0.3) -> str:
        import urllib.request

        url = (self.base_url or self.DEFAULT_BASE_URL).rstrip("/") + "/chat/completions"
        payload = {
            "model": self.model or self.DEFAULT_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"].strip()


class MockProvider(BaseAIProvider):
    """默认 Provider：不联网、不依赖 token，仅用于结构演示。"""

    name = "mock"

    def generate_text(self, prompt: str, **kwargs) -> str:
        return f"[MOCK-RESPONSE] {prompt[:40]}"

    def translate(self, text: str, target: str) -> str:
        if not text:
            return ""
        if target in ("en", "zh-CN"):
            return text  # 英文 / 中文视为已有，原样返回
        tag = {"fr": "FR", "ar": "AR"}.get(target, target.upper())
        return f"[{tag}-draft] {text}"

    def optimize_title(self, title_cn: str, title_en: str = "") -> str:
        from src.ai.title_optimizer import TitleOptimizer

        p = Product(title_cn=title_cn, title_en=title_en)
        TitleOptimizer(provider="mock").optimize(p)
        return p.title_en


def get_provider(
    name: str = "mock",
    api_key: str = "",
    model: str = "",
    base_url: str = "",
) -> BaseAIProvider:
    """工厂：根据名称返回对应 Provider 实例（默认 mock）。"""
    key = (name or "mock").lower()
    if key == "openai":
        from src.ai.providers.openai import OpenAIProvider

        return OpenAIProvider(api_key, model, base_url)
    if key == "deepseek":
        from src.ai.providers.deepseek import DeepSeekProvider

        return DeepSeekProvider(api_key, model, base_url)
    if key == "kimi":
        from src.ai.providers.kimi import KimiProvider

        return KimiProvider(api_key, model, base_url)
    # mock 或未知 -> 统一回退到 mock
    return MockProvider(api_key, model, base_url)
