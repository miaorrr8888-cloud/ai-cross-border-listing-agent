"""AI Provider 架构测试（无网络、不依赖真实 token）。"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.ai.providers import (
    DeepSeekProvider,
    KimiProvider,
    MockProvider,
    OpenAIProvider,
    get_provider,
)
from src.ai.providers.base import BaseAIProvider, OpenAICompatibleProvider


class TestFactory(unittest.TestCase):
    def test_default_mock(self):
        self.assertIsInstance(get_provider(), MockProvider)
        self.assertIsInstance(get_provider("mock"), MockProvider)

    def test_real_providers(self):
        self.assertIsInstance(get_provider("openai"), OpenAIProvider)
        self.assertIsInstance(get_provider("deepseek"), DeepSeekProvider)
        self.assertIsInstance(get_provider("kimi"), KimiProvider)

    def test_unknown_falls_back_to_mock(self):
        self.assertIsInstance(get_provider("whatever"), MockProvider)

    def test_real_inherits_base(self):
        for name in ("openai", "deepseek", "kimi"):
            p = get_provider(name)
            self.assertIsInstance(p, BaseAIProvider)
            self.assertIsInstance(p, OpenAICompatibleProvider)


class TestMockProvider(unittest.TestCase):
    def test_translate_tags(self):
        m = MockProvider()
        self.assertEqual(m.translate("耳机", "en"), "耳机")
        self.assertTrue(m.translate("耳机", "fr").startswith("[FR-draft]"))
        self.assertTrue(m.translate("耳机", "ar").startswith("[AR-draft]"))
        self.assertEqual(m.translate("", "fr"), "")

    def test_optimize_title(self):
        m = MockProvider()
        out = m.optimize_title("无线蓝牙耳机 降噪")
        self.assertTrue(out)  # 复用 TitleOptimizer，含 [EN-draft] 标记


class TestRealProviderNeedsKey(unittest.TestCase):
    def test_no_key_raises(self):
        for name in ("openai", "deepseek", "kimi"):
            p = get_provider(name)  # 未传 api_key
            with self.assertRaises(RuntimeError):
                p.generate_text("hello")
            with self.assertRaises(RuntimeError):
                p.translate("耳机", "fr")
            with self.assertRaises(RuntimeError):
                p.optimize_title("无线蓝牙耳机")

    def test_key_and_model_passthrough(self):
        p = OpenAIProvider(api_key="x", model="gpt-4o")
        self.assertEqual(p.api_key, "x")
        self.assertEqual(p.model, "gpt-4o")
        self.assertEqual(p.DEFAULT_BASE_URL, "https://api.openai.com/v1")


class TestPromptBuilding(unittest.TestCase):
    """用假 provider 验证 translate / optimize_title 的提示词构造正确。"""

    class FakeProvider(OpenAICompatibleProvider):
        name = "fake"

        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            self.last_prompt = None

        def generate_text(self, prompt, **kwargs):
            self.last_prompt = prompt
            return "TRANSLATED"

    def test_translate_prompt_mentions_target(self):
        p = self.FakeProvider(api_key="x")
        out = p.translate("无线蓝牙耳机", "fr")
        self.assertEqual(out, "TRANSLATED")
        self.assertIn("fr", p.last_prompt)

    def test_optimize_prompt_mentions_jumia(self):
        p = self.FakeProvider(api_key="x")
        out = p.optimize_title("无线蓝牙耳机")
        self.assertEqual(out, "TRANSLATED")
        self.assertIn("Jumia", p.last_prompt)


if __name__ == "__main__":
    unittest.main()
