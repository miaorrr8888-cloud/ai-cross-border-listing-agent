"""OpenAI Provider（兼容 Chat Completions 协议）。"""
from __future__ import annotations

from src.ai.providers.base import OpenAICompatibleProvider


class OpenAIProvider(OpenAICompatibleProvider):
    name = "openai"
    DEFAULT_BASE_URL = "https://api.openai.com/v1"
    DEFAULT_MODEL = "gpt-4o-mini"
