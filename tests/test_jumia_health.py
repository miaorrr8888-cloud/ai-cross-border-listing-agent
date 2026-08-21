"""P3-2-A Jumia 健康检查测试：token 缺失 / health report / error mapping / dry-run（不联网）。"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.jumia.api import (
    AuthenticationError,
    InvalidCategoryError,
    JumiaAPIError,
    JumiaAuth,
    JumiaHealthReport,
    MissingCredential,
    PermissionError,
    RateLimitError,
    check_health,
    get_attributes,
    get_categories,
    get_shop_info,
    map_http_error,
)


class TestTokenMissing(unittest.TestCase):
    def test_check_auth_without_token_raises(self):
        with self.assertRaises(MissingCredential):
            JumiaAuth().check_auth()

    def test_check_auth_with_token_returns_ok(self):
        result = JumiaAuth(api_key="real-key").check_auth()
        self.assertTrue(result["success"])
        self.assertIsNone(result["error"])
        self.assertTrue(result["message"])


class TestHealthReport(unittest.TestCase):
    def test_report_with_credential(self):
        report = check_health(JumiaAuth(api_key="real-key"), dry_run=True)
        self.assertIsInstance(report, JumiaHealthReport)
        self.assertEqual(report.auth_status, "ok")
        self.assertEqual(report.api_status, "dry_run")
        self.assertEqual(report.category_status, "dry_run")
        self.assertFalse(report.upload_enabled)

    def test_report_without_credential(self):
        report = check_health(JumiaAuth(), dry_run=True)
        self.assertEqual(report.auth_status, "missing_credential")
        self.assertTrue(report.message)
        self.assertFalse(report.upload_enabled)

    def test_report_from_config(self):
        report = check_health(config={"jumia": {"api_key": "k"}}, dry_run=True)
        self.assertEqual(report.auth_status, "ok")

    def test_report_to_dict(self):
        d = check_health(JumiaAuth()).to_dict()
        self.assertIn("auth_status", d)
        self.assertIn("upload_enabled", d)


class TestErrorMapping(unittest.TestCase):
    def test_exception_hierarchy(self):
        for exc in (AuthenticationError, PermissionError, RateLimitError, InvalidCategoryError):
            self.assertTrue(issubclass(exc, JumiaAPIError))

    def test_map_http_error(self):
        self.assertIs(map_http_error(401), AuthenticationError)
        self.assertIs(map_http_error(403), PermissionError)
        self.assertIs(map_http_error(429), RateLimitError)
        self.assertIs(map_http_error(500), JumiaAPIError)


class TestDryRunMode(unittest.TestCase):
    def test_get_categories_dry_run(self):
        result = get_categories()
        self.assertEqual(result["status"], "dry_run")
        self.assertIn("categories", result)

    def test_get_attributes_dry_run(self):
        result = get_attributes("fashion")
        self.assertEqual(result["status"], "dry_run")
        self.assertEqual(result["required_attributes"], ["size", "color", "material"])

    def test_get_attributes_invalid_category(self):
        with self.assertRaises(InvalidCategoryError):
            get_attributes("nonexistent")

    def test_get_shop_info_dry_run(self):
        result = get_shop_info()
        self.assertEqual(result["status"], "dry_run")
        self.assertIsNone(result["shop"]["shop_name"])  # 不假装真实数据

    def test_real_mode_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            get_categories(dry_run=False)
        with self.assertRaises(NotImplementedError):
            get_attributes("fashion", dry_run=False)
        with self.assertRaises(NotImplementedError):
            get_shop_info(dry_run=False)


if __name__ == "__main__":
    unittest.main()
