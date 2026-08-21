"""DeepSeek Provider（兼容 OpenAI Chat Completions 协议）。"""
from __future__ import annotations

from src.ai.providers.base import OpenAICompatibleProvider


class DeepSeekProvider(OpenAICompatibleProvider):
    name = "deepseek"
    DEFAULT_BASE_URL = "https://api.deepseek.com/v1"
    DEFAULT_MODEL = "deepseek-chat"
