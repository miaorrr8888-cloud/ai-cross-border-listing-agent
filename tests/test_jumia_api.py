"""P3-1 Jumia API 接入层测试：payload 生成 / 缺字段检测 / token 缺失 / dry-run 流程（不联网、不真实上传）。"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.jumia.api import (
    JumiaAuth,
    JumiaClient,
    MissingCredential,
    build_inventory_payload,
    build_listing_payload,
    build_offer_payload,
    build_product_payload,
    build_product_update_payload,
    validate_payload,
)
from src.models.product import Product
from src.pipeline import run


def make_product(**overrides):
    base = dict(
        product_name="USB Desk Fan",
        title_en="USB Desk Fan",
        title_cn="USB桌面风扇",
        description="A quiet portable desk fan.",
        category_id="home_fans",
        sku="FAN-001",
        images=["https://img.example.com/fan1.jpg"],
        attributes={"brand": "CoolAir", "power": "5W"},
        cost_price=20.0,
        currency="USD",
        keywords=["fan"],
        language_versions={"en": {}, "fr": {}, "ar": {}},
    )
    base.update(overrides)
    return Product(**base)


class TestPayloadGeneration(unittest.TestCase):
    def test_product_payload(self):
        p = make_product()
        payload = build_product_payload(p)
        self.assertEqual(payload["name"], "USB Desk Fan")
        self.assertEqual(payload["category_id"], "home_fans")
        self.assertEqual(payload["attributes"]["brand"], "CoolAir")
        self.assertIn("https://img.example.com/fan1.jpg", payload["images"])
        self.assertIsInstance(payload["variants"], dict)

    def test_product_update_payload(self):
        p = make_product()
        payload = build_product_update_payload(p, seller_sku="FAN-001")
        self.assertEqual(payload["seller_sku"], "FAN-001")
        self.assertEqual(payload["name"], "USB Desk Fan")

    def test_offer_payload(self):
        p = make_product()
        p.attributes["_suggested_price"] = 22.73
        offer = build_offer_payload(p)
        self.assertEqual(offer["price"], 22.73)
        self.assertEqual(offer["currency"], "USD")
        self.assertEqual(offer["seller_sku"], "FAN-001")
        self.assertIn("stock", offer)

    def test_inventory_payload(self):
        inv = build_inventory_payload("FAN-001", 10)
        self.assertEqual(inv["seller_sku"], "FAN-001")
        self.assertEqual(inv["stock"], 10)
        self.assertEqual(inv["quantity"], 10)

    def test_listing_payload_structure(self):
        listing = build_listing_payload(make_product())
        self.assertIn("product", listing)
        self.assertIn("offer", listing)
        self.assertIn("inventory", listing)
        self.assertIn("combined", listing)
        # combined 应包含校验所需的 name/category_id/price/currency
        for f in ("name", "category_id", "price", "currency"):
            self.assertIn(f, listing["combined"])


class TestMissingFieldDetection(unittest.TestCase):
    def test_complete_payload_valid(self):
        listing = build_listing_payload(make_product())
        self.assertEqual(validate_payload(listing["combined"]), [])

    def test_missing_required_field(self):
        payload = {"name": "X", "category_id": "home_fans", "price": 10, "currency": "USD"}
        payload.pop("price")
        errors = validate_payload(payload)
        self.assertTrue(any("price" in e for e in errors))

    def test_missing_all_required_fields(self):
        errors = validate_payload({})
        self.assertEqual(len(errors), 4)  # name/category_id/price/currency

    def test_missing_required_attribute(self):
        # home_fans 必填 brand/power，这里 attributes 只有 brand
        payload = {
            "name": "X",
            "category_id": "home_fans",
            "price": 10,
            "currency": "USD",
            "required_attributes": ["brand", "power"],
            "attributes": {"brand": "CoolAir"},
        }
        errors = validate_payload(payload)
        self.assertTrue(any("power" in e for e in errors))
        self.assertFalse(any("brand" in e for e in errors))


class TestTokenMissing(unittest.TestCase):
    def test_empty_auth_raises_missing_credential(self):
        with self.assertRaises(MissingCredential):
            JumiaAuth().resolve()

    def test_config_without_token_raises(self):
        with self.assertRaises(MissingCredential):
            JumiaAuth.from_config({"jumia": {"api_key": "", "api_token": ""}}).resolve()

    def test_env_without_token(self):
        with self.assertRaises(MissingCredential):
            JumiaAuth.from_env().resolve()

    def test_explicit_token_resolves(self):
        self.assertEqual(JumiaAuth(api_key="real-key").resolve(), "real-key")


class TestDryRunFlow(unittest.TestCase):
    def test_authenticate_dry_run(self):
        self.assertEqual(JumiaClient().authenticate()["status"], "dry_run")

    def test_create_product_dry_run(self):
        res = JumiaClient().create_product(make_product())
        self.assertEqual(res["status"], "dry_run")
        self.assertIn("payload", res)
        self.assertIn("validation", res)
        # 不发送 HTTP：payload 中无任何真实请求痕迹
        self.assertIn("combined", res["payload"])

    def test_real_mode_authenticate_requires_token(self):
        with self.assertRaises(MissingCredential):
            JumiaClient(dry_run=False).authenticate()

    def test_real_mode_create_blocked_without_token(self):
        """真实模式无 token → 健康检查失败 → 返回 blocked（不再抛 NotImplementedError）。"""
        res = JumiaClient(dry_run=False).create_product(make_product())
        self.assertEqual(res["status"], "blocked")

    def test_pipeline_emits_payload_and_validation(self):
        cfg = {
            "app": {"dry_run": True},
            "ai": {"provider": "mock", "api_key": "", "model": ""},
            "pricing": {"default_commission_rate": 0.15, "default_target_margin": 0.30, "currency": "RMB"},
        }
        result = run(make_product(), cfg)
        self.assertIn("jumia_payloads", result)
        self.assertIn("payload_validation", result)
        self.assertIn("product", result["jumia_payloads"])
        self.assertIn("valid", result["payload_validation"])


if __name__ == "__main__":
    unittest.main()
