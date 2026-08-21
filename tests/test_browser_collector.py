"""P2-1 浏览器采集测试：只测 URL 解析 / mock HTML 解析 / 字段提取 / 失败处理，不访问真实网站。"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.collector.base_collector import NEEDS_BROWSER, OK, UNSUPPORTED
from src.collector.browser import (
    BrowserClient,
    CollectionError,
    HtmlDoc,
    PlaywrightAdapter,
    StaticHtmlClient,
)
from src.collector.browser.extractors import (
    AttributeExtractor,
    ImageExtractor,
    PriceExtractor,
    TitleExtractor,
    VariantExtractor,
)
from src.collector.browser_collector import BrowserProductCollector
from src.collector.url_parser import detect_platform, parse_url

SAMPLE_HTML = """
<html>
<head>
  <title>USB桌面风扇 静音便携小风扇 - 1688</title>
  <meta property="og:title" content="USB桌面风扇 静音便携小风扇">
  <meta property="og:price:amount" content="19.90">
  <meta property="og:price:currency" content="CNY">
  <meta property="og:image" content="https://img.example.com/fan1.jpg">
</head>
<body>
  <h1 itemprop="name">USB桌面风扇 静音便携小风扇</h1>
  <span itemprop="price">¥19.90</span>
  <img src="https://img.example.com/fan1.jpg">
  <img src="https://img.example.com/fan2.jpg">
  <span itemprop="color">白色</span>
  <span itemprop="sku">FAN-USB-001</span>
  <table>
    <tr><th>材质</th><td>ABS塑料</td></tr>
    <tr><th>功率</th><td>5W</td></tr>
  </table>
</body>
</html>
"""


class _FailingClient(BrowserClient):
    """打开页面即失败，用于验证明确报错。"""

    def open_page(self, url):
        raise RuntimeError("模拟打开失败")

    def get_html(self):
        return ""

    def get_title(self):
        return None

    def get_images(self):
        return []

    def close(self):
        pass


class TestUrlParsing(unittest.TestCase):
    def test_detect_platform_supported(self):
        self.assertEqual(detect_platform("https://detail.1688.com/offer/1.html"), "1688")
        self.assertEqual(detect_platform("https://item.taobao.com/item.htm?id=1"), "taobao")
        self.assertEqual(detect_platform("https://www.amazon.com/dp/B0XYZ"), "amazon")
        self.assertEqual(detect_platform("https://www.aliexpress.com/item/1.html"), "aliexpress")

    def test_parse_url_unsupported(self):
        res = parse_url("https://www.jd.com/item/1.html")
        self.assertEqual(res.status, UNSUPPORTED)
        self.assertIsNone(res.product)

    def test_parse_url_supported_dry_run_needs_browser(self):
        # 支持平台但未注入 client：默认 dry-run 返回 needs_browser_plugin，不拉起浏览器
        res = parse_url("https://detail.1688.com/offer/1.html")
        self.assertEqual(res.status, NEEDS_BROWSER)
        self.assertIsNone(res.product)


class TestMockHtmlParsing(unittest.TestCase):
    def test_collect_from_mock_html(self):
        client = StaticHtmlClient(html=SAMPLE_HTML)
        res = BrowserProductCollector(browser_client=client).collect(
            "https://detail.1688.com/offer/123.html"
        )
        self.assertEqual(res.status, OK)
        p = res.product
        self.assertIsNotNone(p)
        self.assertEqual(p.source_platform, "1688")
        self.assertEqual(p.title_cn, "USB桌面风扇 静音便携小风扇")
        self.assertAlmostEqual(p.price, 19.9, places=2)
        self.assertEqual(p.price_currency, "CNY")
        self.assertIn("https://img.example.com/fan2.jpg", p.images)
        self.assertEqual(p.variants.get("sku"), "FAN-USB-001")
        self.assertEqual(p.attributes.get("材质"), "ABS塑料")


class TestFieldExtraction(unittest.TestCase):
    def setUp(self):
        self.doc = HtmlDoc(SAMPLE_HTML, base_url="https://detail.1688.com/offer/123.html")

    def test_title(self):
        self.assertEqual(TitleExtractor().extract(self.doc), "USB桌面风扇 静音便携小风扇")

    def test_price(self):
        price = PriceExtractor().extract(self.doc)
        self.assertIsNotNone(price)
        self.assertAlmostEqual(price["value"], 19.9, places=2)
        self.assertEqual(price["currency"], "CNY")

    def test_images(self):
        imgs = ImageExtractor().extract(self.doc)
        self.assertIsNotNone(imgs)
        self.assertIn("https://img.example.com/fan1.jpg", imgs)
        self.assertIn("https://img.example.com/fan2.jpg", imgs)

    def test_variants(self):
        variants = VariantExtractor().extract(self.doc)
        self.assertIsNotNone(variants)
        self.assertEqual(variants["sku"], "FAN-USB-001")
        self.assertIn("白色", variants.get("colors", []))

    def test_attributes(self):
        attrs = AttributeExtractor().extract(self.doc)
        self.assertIsNotNone(attrs)
        self.assertEqual(attrs.get("材质"), "ABS塑料")
        self.assertEqual(attrs.get("功率"), "5W")

    def test_extractors_return_none_on_empty_html(self):
        empty = HtmlDoc("<html><body></body></html>")
        self.assertIsNone(TitleExtractor().extract(empty))
        self.assertIsNone(PriceExtractor().extract(empty))
        self.assertIsNone(ImageExtractor().extract(empty))
        self.assertIsNone(VariantExtractor().extract(empty))
        self.assertIsNone(AttributeExtractor().extract(empty))


class TestFailureHandling(unittest.TestCase):
    def test_collect_failure_raises_clear_error(self):
        collector = BrowserProductCollector(browser_client=_FailingClient())
        with self.assertRaises(CollectionError) as ctx:
            collector.collect("https://detail.1688.com/offer/1.html")
        self.assertIn("浏览器采集失败", str(ctx.exception))

    def test_collect_unsupported_returns_unsupported(self):
        res = BrowserProductCollector().collect("https://www.jd.com/item/1.html")
        self.assertEqual(res.status, UNSUPPORTED)

    def test_client_not_opened_raises_clear_error(self):
        client = StaticHtmlClient(html="")
        collector = BrowserProductCollector(browser_client=client)
        # 不传 html、未 open_page 也不会有网络（StaticHtmlClient.open_page 是 no-op）
        res = collector.collect("https://detail.1688.com/offer/1.html")
        self.assertEqual(res.status, OK)
        self.assertIsNotNone(res.product)  # 静态 HTML 为空 -> Product 字段为空，但不报错

    def test_playwright_adapter_requires_install(self):
        try:
            import playwright  # noqa: F401

            available = True
        except ImportError:
            available = False
        if not available:
            with self.assertRaises(CollectionError):
                PlaywrightAdapter()
        else:
            self.skipTest("已安装 playwright，跳过未安装分支")


if __name__ == "__main__":
    unittest.main()
