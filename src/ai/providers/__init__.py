"""AI Provider 包：统一入口与所有 Provider 导出。"""
from __future__ import annotations

from src.ai.providers.base import (
    BaseAIProvider,
    MockProvider,
    OpenAICompatibleProvider,
    get_provider,
)
from src.ai.providers.deepseek import DeepSeekProvider
from src.ai.providers.kimi import KimiProvider
from src.ai.providers.openai import OpenAIProvider

__all__ = [
    "BaseAIProvider",
    "OpenAICompatibleProvider",
    "MockProvider",
    "OpenAIProvider",
    "DeepSeekProvider",
    "KimiProvider",
    "get_provider",
]
