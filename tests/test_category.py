"""P2-2 类目智能测试：类目查询 / 商品匹配 / 属性检查 / 缺失属性检测（纯本地，不联网）。"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.ai.category_matcher import CategoryMatcher as AiCategoryMatcher
from src.jumia.attribute_schema import (
    get_optional_attributes,
    get_required_attributes,
)
from src.jumia.category import (
    AttributeSchema,
    CategoryMatcher,
    CategoryTree,
    JumiaCategoryMatch,
)
from src.models.product import Product
from src.validator.listing_check import check


class TestCategoryTree(unittest.TestCase):
    def setUp(self):
        self.tree = CategoryTree()

    def test_get_by_id(self):
        self.assertEqual(self.tree.get("electronics").name, "Electronics")

    def test_get_by_name(self):
        self.assertEqual(self.tree.get_by_name("Fashion").id, "fashion")

    def test_get_category_id(self):
        self.assertEqual(self.tree.get_category_id("Electronics"), "electronics")
        self.assertEqual(self.tree.get_category_id("Audio & Headphones"), "electronics_audio")

    def test_children(self):
        ids = [c.id for c in self.tree.children("electronics")]
        self.assertIn("electronics_audio", ids)
        self.assertIn("electronics_phones", ids)

    def test_root_ids(self):
        self.assertIn("electronics", self.tree.root_ids())


class TestCategoryMatching(unittest.TestCase):
    def setUp(self):
        self.matcher = CategoryMatcher()

    def test_fan_maps_to_home_fans(self):
        p = Product(title_cn="USB桌面风扇", title_en="USB desk fan")
        m = self.matcher.match(p)
        self.assertIsInstance(m, JumiaCategoryMatch)
        self.assertEqual(m.category_id, "home_fans")
        self.assertEqual(m.category_name, "Fans & Cooling")
        self.assertGreater(m.confidence, 0)
        self.assertTrue(m.reason)

    def test_earphone_maps_to_audio(self):
        m = self.matcher.match(Product(title_en="Wireless earphone"))
        self.assertEqual(m.category_id, "electronics_audio")

    def test_unrecognized_falls_back(self):
        m = self.matcher.match(Product(title_en="some random thing"))
        self.assertEqual(m.category_id, "general_merchandise")
        self.assertEqual(m.confidence, 0.0)

    def test_ai_matcher_backward_compat(self):
        m = AiCategoryMatcher()
        name, conf = m.match(Product(title_en="Wireless earphone"))
        self.assertEqual(name, "Audio & Headphones")
        self.assertGreater(conf, 0)
        detail = m.match_detail(Product(title_en="Wireless earphone"))
        self.assertEqual(detail.category_id, "electronics_audio")


class TestAttributeSchema(unittest.TestCase):
    def setUp(self):
        self.schema = AttributeSchema()

    def test_fashion_attributes(self):
        self.assertEqual(self.schema.required("fashion"), ["size", "color", "material"])

    def test_electronics_attributes(self):
        self.assertEqual(self.schema.required("electronics"), ["brand", "model", "power"])
        self.assertIn("color", self.schema.optional("electronics"))

    def test_unknown_category_empty(self):
        self.assertEqual(self.schema.required("nonexistent"), [])

    def test_module_level_helpers(self):
        self.assertEqual(get_required_attributes("fashion"), ["size", "color", "material"])
        self.assertIn("gender", get_optional_attributes("fashion"))


class TestMissingAttributes(unittest.TestCase):
    def setUp(self):
        self.schema = AttributeSchema()

    def test_missing_required_detection(self):
        missing = self.schema.missing_required("fashion", {"color": "red"})
        self.assertEqual(sorted(missing), ["material", "size"])

    def test_no_missing_when_complete(self):
        attrs = {"size": "M", "color": "red", "material": "cotton"}
        self.assertEqual(self.schema.missing_required("fashion", attrs), [])

    def test_listing_check_reports_missing(self):
        p = Product(
            title_en="A dress",
            product_name="A dress",
            category="Fashion",
            category_id="fashion",
            brand="B",
            sku="S",
            required_attributes=["size", "color", "material"],
            attributes={"color": "red"},  # 缺 size / material
        )
        score, issues = check(p)
        joined = " ".join(issues)
        self.assertIn("缺少类目必填属性", joined)
        self.assertIn("size", joined)
        self.assertIn("material", joined)
        # check 应把缺失属性回填到 product.missing_attributes
        self.assertEqual(sorted(p.missing_attributes), ["material", "size"])


if __name__ == "__main__":
    unittest.main()
