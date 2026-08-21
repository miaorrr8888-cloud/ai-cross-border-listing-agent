"""批量处理与输入层测试（无网络、不生成假数据）。"""
import csv
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.collector.excel_collector import (
    batch_generate,
    from_csv,
    from_json,
    read_products,
)
from src.collector.url_parser import NEEDS_BROWSER, UNSUPPORTED, parse_url
from src.models.product import Product
from src.pipeline import run


class TestInputLayerNoFakeData(unittest.TestCase):
    def test_url_returns_needs_browser_plugin(self):
        res = parse_url("https://www.1688.com/offer/123.html")
        self.assertEqual(res.status, NEEDS_BROWSER)
        self.assertIsNone(res.product)  # 绝不生成假数据
        self.assertTrue(res.message)

    def test_unknown_platform_returns_unsupported(self):
        # P2-1：不支持平台返回 unsupported
        res = parse_url("https://shop.unknown.example.com/x")
        self.assertEqual(res.status, UNSUPPORTED)
        self.assertIsNone(res.product)


class TestReaders(unittest.TestCase):
    def test_from_json(self):
        products = from_json(os.path.join(ROOT, "examples", "sample_product.json"))
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0].sku, "EARBUD-BT-001")

    def test_from_csv(self):
        csv_path = os.path.join(ROOT, "examples", "batch_sample.csv")
        products = from_csv(csv_path)
        self.assertGreaterEqual(len(products), 2)
        self.assertTrue(products[0].sku)
        self.assertTrue(products[0].images)  # 图片被解析

    def test_read_products_dispatch(self):
        p = read_products(os.path.join(ROOT, "examples", "sample_product.json"))
        self.assertEqual(len(p), 1)


class TestBatchGenerate(unittest.TestCase):
    def test_batch_writes_per_sku(self):
        products = [
            Product(sku="A-1", title_cn="蓝牙耳机", cost_price=20.0, currency="RMB",
                    images=["https://x/a.jpg"], attributes={"color": "黑"}),
            Product(sku="A-2", title_cn="数据线", cost_price=5.0, currency="RMB",
                    images=["https://x/b.jpg"], attributes={"length": "1m"}),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            summary = batch_generate(products, {}, out_dir=tmp)
            self.assertEqual(len(summary), 2)
            for s in summary:
                self.assertTrue(os.path.exists(s["path"]))
                # 校验写入内容是合法 JSON 且含 listing_check
                with open(s["path"], "r", encoding="utf-8") as f:
                    import json
                    data = json.load(f)
                self.assertIn("listing_check", data)
                self.assertIn("price_plan", data)


class TestExcelOptional(unittest.TestCase):
    def test_from_excel_if_openpyxl(self):
        try:
            from openpyxl import Workbook
        except ImportError:
            self.skipTest("openpyxl 未安装，跳过 Excel 测试（pip install openpyxl）")
        with tempfile.TemporaryDirectory() as tmp:
            xlsx = os.path.join(tmp, "batch.xlsx")
            wb = Workbook()
            ws = wb.active
            ws.append(["sku", "title", "images", "price", "currency"])
            ws.append(["X-1", "无线鼠标", "https://x/m.jpg", "12", "RMB"])
            wb.save(xlsx)
            products = read_products(xlsx)
            self.assertEqual(len(products), 1)
            self.assertEqual(products[0].sku, "X-1")
            self.assertEqual(products[0].cost_price, 12.0)


if __name__ == "__main__":
    unittest.main()
