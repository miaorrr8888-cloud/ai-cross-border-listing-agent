"""Kimi（Moonshot）Provider（兼容 OpenAI Chat Completions 协议）。"""
from __future__ import annotations

from src.ai.providers.base import OpenAICompatibleProvider


class KimiProvider(OpenAICompatibleProvider):
    name = "kimi"
    DEFAULT_BASE_URL = "https://api.moonshot.cn/v1"
    DEFAULT_MODEL = "moonshot-v1-8k"
