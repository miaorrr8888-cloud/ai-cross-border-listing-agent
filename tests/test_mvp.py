"""MVP 测试：不连接真实 Jumia API。

运行：pytest tests/   或   python -m unittest tests.test_mvp
"""
import os
import sys
import unittest

# 让 src 包可被导入（项目根目录加入 path）
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.ai.category_matcher import CategoryMatcher
from src.ai.providers import get_provider
from src.ai.title_optimizer import TitleOptimizer
from src.collector.url_collector import collect, detect_platform
from src.jumia.api_client import JumiaAPIClient
from src.jumia.product_mapper import build_listing
from src.jumia.uploader import upload
from src.models.product import Language, Product
from src.validator.listing_check import check


class TestProductSchema(unittest.TestCase):
    def test_from_dict_roundtrip(self):
        data = {"title_cn": "测试商品", "cost_price": 9.9, "currency": "USD"}
        p = Product.from_dict(data)
        self.assertEqual(p.title_cn, "测试商品")
        self.assertEqual(p.cost_price, 9.9)
        self.assertEqual(p.source_platform, "generic")  # 默认值生效
        d = p.to_dict()
        self.assertIn("language_versions", d)
        self.assertIn("attributes", d)

    def test_languages_enum(self):
        self.assertEqual(Language.FR.value, "fr")
        self.assertEqual(Language.AR.value, "ar")
        self.assertIn("zh-CN", Language.values())

    def test_unknown_fields_ignored(self):
        p = Product.from_dict({"title_cn": "x", "unknown_field": 1})
        self.assertEqual(p.title_cn, "x")
        self.assertFalse(hasattr(p, "unknown_field"))


class TestUrlInput(unittest.TestCase):
    def test_detect_platform(self):
        self.assertEqual(detect_platform("https://www.1688.com/x"), "1688")
        self.assertEqual(detect_platform("https://www.taobao.com/item"), "taobao")
        self.assertEqual(detect_platform("https://www.amazon.com/x"), "amazon")
        self.assertEqual(detect_platform("https://shop.example.com/x"), "generic")

    def test_collect_dry_run(self):
        p = collect("https://www.1688.com/offer/123", dry_run=True)
        self.assertEqual(p.source_platform, "1688")
        self.assertEqual(p.source_url, "https://www.1688.com/offer/123")
        self.assertTrue(p.title_cn)  # 占位标题已填

    def test_collect_no_fake_token(self):
        # 采集器不应产生任何凭证字段
        p = collect("https://www.1688.com/offer/123")
        self.assertFalse(hasattr(p, "api_key"))


class TestMultilingualOutput(unittest.TestCase):
    def test_translator_structure(self):
        provider = get_provider("mock")
        p = Product(title_cn="无线耳机", title_en="Wireless Earphone")
        listing = build_listing(p, provider)
        lv = listing["language_versions"]
        for lang in ("zh-CN", "en", "fr", "ar"):
            self.assertIn(lang, lv, f"缺少语言版本 {lang}")
        self.assertTrue(lv["fr"]["title"])
        self.assertTrue(lv["ar"]["title"])

    def test_title_optimizer(self):
        o = TitleOptimizer()
        p = Product(title_cn="无线蓝牙耳机  降噪")
        o.optimize(p)
        self.assertTrue(p.title_en)
        self.assertTrue(p.product_name)
        self.assertNotIn("  ", p.title_en)  # 多余空格被压缩

    def test_category_matcher(self):
        m = CategoryMatcher()
        p = Product(title_en="Wireless earphone", keywords=["earphone"])
        cat, score = m.match(p)
        self.assertEqual(cat, "Audio & Headphones")  # 两阶段：耳机 → Audio & Headphones
        self.assertGreater(score, 0)


class TestListingValidator(unittest.TestCase):
    def test_score_full(self):
        p = Product(
            title_en="Wireless Earphone",
            product_name="Wireless Earphone",
            category="Electronics",
            category_id="electronics",  # P2-2：已映射到类目树
            brand="SoundMax",
            sku="SKU1",
            images=["a.jpg", "b.jpg", "c.jpg"],
            long_description="x" * 60,
            keywords=["earphone"],
            attributes={"color": "black", "size": "M"},  # 属性完整
            language_versions={"en": {}, "fr": {}, "ar": {}},
            cost_price=10.0,
            currency="USD",
        )
        score, issues = check(p)
        self.assertGreaterEqual(score, 90)
        self.assertEqual(issues, [])

    def test_enhanced_checks(self):
        # 缺属性 / 标题过短 / 描述过短 / 无图 应被检出并扣分
        p = Product(
            title_en="X",
            product_name="X",
            category="Electronics",
            brand="B",
            sku="S",
            images=[],
            long_description="短",
            keywords=[],
            language_versions={"en": {}},
            cost_price=0.0,
            currency="",
        )
        score, issues = check(p)
        joined = " ".join(issues)
        self.assertIn("属性偏少", joined)
        self.assertIn("标题过短", joined)
        self.assertIn("描述过短", joined)
        self.assertIn("无商品图片", joined)
        self.assertIn("缺少货币单位", joined)
        self.assertLess(score, 100)

    def test_score_empty(self):
        p = Product()
        score, issues = check(p)
        self.assertLess(score, 100)
        self.assertTrue(issues)


class TestDryRunNoApi(unittest.TestCase):
    def test_api_client_dry_run(self):
        client = JumiaAPIClient(dry_run=True)
        self.assertEqual(client.authenticate()["status"], "dry_run")
        p = Product(title_en="X", title_cn="X")
        listing, res = upload(p, client, get_provider("mock"))
        self.assertEqual(res["status"], "dry_run")
        self.assertTrue(res["would_send"])
        self.assertIn("listing_preview", res)

    def test_api_client_real_raises(self):
        # 真实模式未实现，必须显式报错而不是悄悄发送
        client = JumiaAPIClient(dry_run=False)
        with self.assertRaises(NotImplementedError):
            client.authenticate()


if __name__ == "__main__":
    unittest.main()
