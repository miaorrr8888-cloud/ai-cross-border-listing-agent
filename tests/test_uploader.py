"""P3-2-B-2 上传闭环测试：guard / mock 上传 / dry-run 不上传。

安全规则：
- 测试全部使用 mock transport，不访问真实 Jumia。
- 不发送真实 HTTP 请求。
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.jumia.api import (
    JumiaAuth,
    JumiaClient,
    JumiaHttpClient,
    JumiaUploader,
    MissingCredential,
    ParsedResponse,
    UploadDisabledError,
    UploadGuard,
    UploadGuardConfig,
    UploadLimitExceededError,
    UploadResult,
    create_offer,
    create_product,
    update_inventory,
)
from src.models.product import Product


# ════════════════════════════════════════════════════════════
#  辅助函数
# ════════════════════════════════════════════════════════════

def make_product(**overrides):
    """创建测试用 Product（字段完整，能通过 payload_validator）。"""
    base = dict(
        product_name="USB Desk Fan",
        title_en="USB Desk Fan",
        description="A quiet portable desk fan.",
        category_id="home_fans",
        sku="FAN-001",
        images=["https://img.example.com/fan1.jpg"],
        attributes={"brand": "CoolAir", "power": "5W"},
        cost_price=20.0,
        price=29.99,
        currency="USD",
    )
    base.update(overrides)
    return Product(**base)


def make_mock_transport(status_code=200, body=b'{"ok": true}', headers=None):
    """创建 mock transport：返回固定响应。"""
    resp_body = body
    resp_headers = headers or {"Content-Type": "application/json"}

    def _transport(method, url, req_headers, req_body, timeout):
        return (status_code, resp_body, resp_headers)
    return _transport


def make_endpoint_transport():
    """按 endpoint 返回不同响应的 mock transport（模拟 Jumia API）。"""
    def _transport(method, url, headers, body, timeout):
        if "/products" in url and method == "POST":
            return (201, b'{"id": "PROD-001", "name": "USB Desk Fan"}', {})
        elif "/offers" in url and method == "POST":
            return (201, b'{"id": "OFFER-001", "price": 29.99}', {})
        elif "/inventory" in url and method == "PUT":
            return (200, b'{"ok": true, "updated": true}', {})
        return (404, b'{"error": "not found"}', {})
    return _transport


def make_http_client(dry_run=False, transport=None):
    """创建带 mock transport 的 JumiaHttpClient。"""
    return JumiaHttpClient(
        auth=JumiaAuth(api_key="test-key"),
        dry_run=dry_run,
        transport=transport or make_endpoint_transport(),
        retry_config=None,
        sleep_func=lambda s: None,
    )


# ════════════════════════════════════════════════════════════
#  1. Guard Disabled 测试
# ════════════════════════════════════════════════════════════

class TestUploadGuardDisabled(unittest.TestCase):
    """测试 UploadGuard 禁用场景。"""

    def test_disabled_raises(self):
        """enabled=False → check_allowed 抛 UploadDisabledError。"""
        guard = UploadGuard(UploadGuardConfig(enabled=False))
        with self.assertRaises(UploadDisabledError):
            guard.check_allowed(1)

    def test_disabled_message_contains_hint(self):
        """错误消息包含启用提示。"""
        guard = UploadGuard(UploadGuardConfig(enabled=False))
        try:
            guard.check_allowed(1)
        except UploadDisabledError as e:
            self.assertIn("禁用", str(e))
            self.assertIn("enabled", str(e))

    def test_default_guard_disabled(self):
        """默认 UploadGuard（无参数）禁用。"""
        guard = UploadGuard()
        with self.assertRaises(UploadDisabledError):
            guard.check_allowed(1)

    def test_disabled_even_with_count_zero(self):
        """禁用状态下即使 count=0 也抛异常。"""
        guard = UploadGuard(UploadGuardConfig(enabled=False))
        with self.assertRaises(UploadDisabledError):
            guard.check_allowed(0)


# ════════════════════════════════════════════════════════════
#  2. Guard Limit 测试
# ════════════════════════════════════════════════════════════

class TestUploadGuardLimit(unittest.TestCase):
    """测试 UploadGuard 数量限制。"""

    def test_limit_exceeded(self):
        """count > max_products → 抛 UploadLimitExceededError。"""
        guard = UploadGuard(UploadGuardConfig(enabled=True, max_products=1))
        with self.assertRaises(UploadLimitExceededError):
            guard.check_allowed(2)

    def test_limit_exceeded_message(self):
        """错误消息包含数量信息。"""
        guard = UploadGuard(UploadGuardConfig(enabled=True, max_products=1))
        try:
            guard.check_allowed(5)
        except UploadLimitExceededError as e:
            self.assertIn("5", str(e))
            self.assertIn("1", str(e))

    def test_within_limit_allowed(self):
        """count <= max_products → 返回 True。"""
        guard = UploadGuard(UploadGuardConfig(enabled=True, max_products=1))
        self.assertTrue(guard.check_allowed(1))

    def test_custom_max_products(self):
        """自定义 max_products。"""
        guard = UploadGuard(UploadGuardConfig(enabled=True, max_products=5))
        self.assertTrue(guard.check_allowed(3))
        self.assertTrue(guard.check_allowed(5))
        with self.assertRaises(UploadLimitExceededError):
            guard.check_allowed(6)

    def test_first_time_max_one_sku(self):
        """第一次真实模式最多 1 个 SKU。"""
        guard = UploadGuard(UploadGuardConfig(enabled=True, max_products=1))
        self.assertTrue(guard.check_allowed(1))
        with self.assertRaises(UploadLimitExceededError):
            guard.check_allowed(2)


# ════════════════════════════════════════════════════════════
#  3. Guard from_config 测试
# ════════════════════════════════════════════════════════════

class TestUploadGuardFromConfig(unittest.TestCase):
    """测试 UploadGuard.from_config()。"""

    def test_from_config_disabled(self):
        guard = UploadGuard.from_config({"upload": {"enabled": False, "max_products": 1}})
        with self.assertRaises(UploadDisabledError):
            guard.check_allowed(1)

    def test_from_config_enabled(self):
        guard = UploadGuard.from_config({"upload": {"enabled": True, "max_products": 3}})
        self.assertTrue(guard.check_allowed(2))

    def test_from_empty_config(self):
        """空配置 → 默认禁用。"""
        guard = UploadGuard.from_config({})
        with self.assertRaises(UploadDisabledError):
            guard.check_allowed(1)

    def test_from_none_config(self):
        """None 配置 → 默认禁用。"""
        guard = UploadGuard.from_config(None)
        with self.assertRaises(UploadDisabledError):
            guard.check_allowed(1)

    def test_from_config_missing_upload_key(self):
        """配置缺少 upload 段 → 默认禁用。"""
        guard = UploadGuard.from_config({"app": {"dry_run": True}})
        with self.assertRaises(UploadDisabledError):
            guard.check_allowed(1)


# ════════════════════════════════════════════════════════════
#  4. Mock Product Upload 测试
# ════════════════════════════════════════════════════════════

class TestMockProductUpload(unittest.TestCase):
    """测试 create_product() 函数（mock transport）。"""

    def test_create_product_success(self):
        """mock POST /products → 201 → success=True。"""
        transport = make_mock_transport(201, b'{"id": "PROD-001"}')
        client = make_http_client(transport=transport)
        resp = create_product(client, make_product())
        self.assertTrue(resp.success)
        self.assertEqual(resp.http_status, 201)
        self.assertEqual(resp.data["id"], "PROD-001")

    def test_create_product_failure(self):
        """mock POST /products → 400 → success=False。"""
        transport = make_mock_transport(400, b'{"error": "bad request"}')
        client = make_http_client(transport=transport)
        resp = create_product(client, make_product())
        self.assertFalse(resp.success)
        self.assertEqual(resp.http_status, 400)

    def test_create_product_no_token_raises(self):
        """无 token → MissingCredential。"""
        client = JumiaHttpClient(
            auth=JumiaAuth(),
            dry_run=False,
            transport=make_mock_transport(200),
        )
        with self.assertRaises(MissingCredential):
            create_product(client, make_product())


# ════════════════════════════════════════════════════════════
#  5. Mock Offer Upload 测试
# ════════════════════════════════════════════════════════════

class TestMockOfferUpload(unittest.TestCase):
    """测试 create_offer() 函数（mock transport）。"""

    def test_create_offer_success(self):
        """mock POST /offers → 201 → success=True。"""
        transport = make_mock_transport(201, b'{"id": "OFFER-001"}')
        client = make_http_client(transport=transport)
        resp = create_offer(client, make_product())
        self.assertTrue(resp.success)
        self.assertEqual(resp.http_status, 201)
        self.assertEqual(resp.data["id"], "OFFER-001")

    def test_create_offer_failure(self):
        """mock POST /offers → 422 → success=False。"""
        transport = make_mock_transport(422, b'{"error": "validation failed"}')
        client = make_http_client(transport=transport)
        resp = create_offer(client, make_product())
        self.assertFalse(resp.success)


# ════════════════════════════════════════════════════════════
#  6. Inventory Update 测试
# ════════════════════════════════════════════════════════════

class TestInventoryUpdate(unittest.TestCase):
    """测试 update_inventory() 函数（mock transport）。"""

    def test_update_inventory_success(self):
        """mock PUT /inventory → 200 → success=True。"""
        transport = make_mock_transport(200, b'{"ok": true}')
        client = make_http_client(transport=transport)
        resp = update_inventory(client, "FAN-001", 10)
        self.assertTrue(resp.success)
        self.assertEqual(resp.http_status, 200)

    def test_update_inventory_failure(self):
        """mock PUT /inventory → 500 → success=False。"""
        transport = make_mock_transport(500, b'{"error": "server error"}')
        client = make_http_client(transport=transport)
        resp = update_inventory(client, "FAN-001", 10)
        self.assertFalse(resp.success)

    def test_update_inventory_no_sku(self):
        """空 SKU 也能发送请求（payload 中 seller_sku=""）。"""
        transport = make_mock_transport(200, b'{"ok": true}')
        client = make_http_client(transport=transport)
        resp = update_inventory(client, "", 5)
        self.assertTrue(resp.success)


# ════════════════════════════════════════════════════════════
#  7. 完整 Upload 流程测试
# ════════════════════════════════════════════════════════════

class TestFullUploadFlow(unittest.TestCase):
    """测试 JumiaUploader.upload_product() 完整流程（mock transport）。"""

    def test_full_upload_success(self):
        """完整上传：product → offer → inventory 全部成功。"""
        client = make_http_client()
        guard = UploadGuard(UploadGuardConfig(enabled=True, max_products=1))
        uploader = JumiaUploader(client, guard)

        result = uploader.upload_product(make_product())

        self.assertTrue(result.success)
        self.assertEqual(result.product_id, "PROD-001")
        self.assertEqual(result.offer_id, "OFFER-001")
        self.assertEqual(result.inventory_status, "updated")
        self.assertEqual(result.errors, [])

    def test_upload_guard_blocks(self):
        """guard 禁用 → 上传被阻止，不发送任何 HTTP。"""
        transport_called = [False]

        def transport(method, url, headers, body, timeout):
            transport_called[0] = True
            return (200, b'{}', {})

        client = make_http_client(transport=transport)
        guard = UploadGuard(UploadGuardConfig(enabled=False))
        uploader = JumiaUploader(client, guard)

        result = uploader.upload_product(make_product())

        self.assertFalse(result.success)
        self.assertTrue(result.errors)
        self.assertIn("禁用", result.errors[0])
        self.assertFalse(transport_called[0], "guard 禁止时不应调用 transport")

    def test_upload_validation_failure(self):
        """payload 校验失败 → 不上传。"""
        transport_called = [False]

        def transport(method, url, headers, body, timeout):
            transport_called[0] = True
            return (200, b'{}', {})

        client = make_http_client(transport=transport)
        guard = UploadGuard(UploadGuardConfig(enabled=True, max_products=1))
        uploader = JumiaUploader(client, guard)

        # 缺少 category_id 和 price
        result = uploader.upload_product(make_product(category_id="", price=0.0))

        self.assertFalse(result.success)
        self.assertTrue(result.errors)
        self.assertFalse(transport_called[0], "校验失败时不应调用 transport")

    def test_upload_product_creation_failure(self):
        """商品创建失败 → 不继续创建 offer。"""
        transport = make_mock_transport(400, b'{"error": "bad request"}')
        client = make_http_client(transport=transport)
        guard = UploadGuard(UploadGuardConfig(enabled=True, max_products=1))
        uploader = JumiaUploader(client, guard)

        result = uploader.upload_product(make_product())

        self.assertFalse(result.success)
        self.assertTrue(any("商品创建" in e for e in result.errors))
        self.assertIsNone(result.product_id)
        self.assertIsNone(result.offer_id)

    def test_upload_offer_failure(self):
        """商品创建成功但 offer 失败 → product_id 有值，offer_id 无值。"""
        def transport(method, url, headers, body, timeout):
            if "/products" in url:
                return (201, b'{"id": "PROD-001"}', {})
            elif "/offers" in url:
                return (400, b'{"error": "offer failed"}', {})
            return (200, b'{}', {})

        client = make_http_client(transport=transport)
        guard = UploadGuard(UploadGuardConfig(enabled=True, max_products=1))
        uploader = JumiaUploader(client, guard)

        result = uploader.upload_product(make_product())

        self.assertFalse(result.success)
        self.assertEqual(result.product_id, "PROD-001")
        self.assertIsNone(result.offer_id)
        self.assertTrue(any("Offer" in e for e in result.errors))

    def test_upload_inventory_failure(self):
        """product + offer 成功但 inventory 失败 → inventory_status=failed。"""
        def transport(method, url, headers, body, timeout):
            if "/products" in url:
                return (201, b'{"id": "PROD-001"}', {})
            elif "/offers" in url:
                return (201, b'{"id": "OFFER-001"}', {})
            elif "/inventory" in url:
                return (500, b'{"error": "inventory failed"}', {})
            return (404, b'{}', {})

        client = make_http_client(transport=transport)
        guard = UploadGuard(UploadGuardConfig(enabled=True, max_products=1))
        uploader = JumiaUploader(client, guard)

        result = uploader.upload_product(make_product())

        self.assertFalse(result.success)
        self.assertEqual(result.product_id, "PROD-001")
        self.assertEqual(result.offer_id, "OFFER-001")
        self.assertEqual(result.inventory_status, "failed")
        self.assertTrue(any("库存" in e for e in result.errors))

    def test_upload_result_to_dict(self):
        """UploadResult.to_dict() 序列化正确。"""
        result = UploadResult(
            success=True,
            product_id="PROD-001",
            offer_id="OFFER-001",
            inventory_status="updated",
            errors=[],
        )
        d = result.to_dict()
        self.assertTrue(d["success"])
        self.assertEqual(d["product_id"], "PROD-001")
        self.assertEqual(d["offer_id"], "OFFER-001")
        self.assertEqual(d["inventory_status"], "updated")
        self.assertEqual(d["errors"], [])

    def test_upload_result_empty(self):
        """空 UploadResult 序列化正确。"""
        result = UploadResult()
        d = result.to_dict()
        self.assertFalse(d["success"])
        self.assertIsNone(d["product_id"])
        self.assertIsNone(d["offer_id"])
        self.assertIsNone(d["inventory_status"])
        self.assertEqual(d["errors"], [])

    def test_upload_extracts_product_id_alternative_key(self):
        """响应中使用 product_id 键也能提取。"""
        transport = make_mock_transport(201, b'{"product_id": "ALT-001"}')
        client = make_http_client(transport=transport)
        guard = UploadGuard(UploadGuardConfig(enabled=True, max_products=1))
        uploader = JumiaUploader(client, guard)

        # 只测 product 创建步骤（offer 会失败因为 transport 固定返回 product 格式）
        result = uploader.upload_product(make_product())
        self.assertEqual(result.product_id, "ALT-001")


# ════════════════════════════════════════════════════════════
#  8. Dry-Run 不上传测试
# ════════════════════════════════════════════════════════════

class TestDryRunNoUpload(unittest.TestCase):
    """测试 dry-run 模式不发送 HTTP 请求。"""

    def test_dry_run_uploader_no_transport(self):
        """dry-run 模式 uploader 不调用 transport。"""
        transport_called = [False]

        def transport(method, url, headers, body, timeout):
            transport_called[0] = True
            return (200, b'{}', {})

        client = JumiaHttpClient(
            auth=JumiaAuth(api_key="k"),
            dry_run=True,
            transport=transport,
        )
        guard = UploadGuard(UploadGuardConfig(enabled=True, max_products=1))
        uploader = JumiaUploader(client, guard)

        result = uploader.upload_product(make_product())

        self.assertFalse(result.success)
        self.assertFalse(transport_called[0], "dry-run 模式不应调用 transport")

    def test_dry_run_client_create_product(self):
        """dry-run 模式 JumiaClient.create_product() 返回预览。"""
        client = JumiaClient(dry_run=True)
        res = client.create_product(make_product())
        self.assertEqual(res["status"], "dry_run")
        self.assertIn("http_preview", res)
        self.assertIn("payload", res)

    def test_dry_run_live_upload_returns_preview(self):
        """dry-run 模式 live_upload() 返回 dry-run 预览。"""
        client = JumiaClient(dry_run=True)
        res = client.live_upload(make_product())
        self.assertEqual(res["status"], "dry_run")

    def test_dry_run_live_upload_no_transport(self):
        """dry-run live_upload() 不调用 transport。"""
        transport_called = [False]

        def transport(method, url, headers, body, timeout):
            transport_called[0] = True
            return (200, b'{}', {})

        client = JumiaClient(
            dry_run=True,
            http_client=JumiaHttpClient(
                auth=JumiaAuth(api_key="k"),
                dry_run=True,
                transport=transport,
            ),
        )
        res = client.live_upload(make_product())
        self.assertEqual(res["status"], "dry_run")
        self.assertFalse(transport_called[0])


# ════════════════════════════════════════════════════════════
#  9. JumiaClient.live_upload() 集成测试
# ════════════════════════════════════════════════════════════

class TestLiveUploadIntegration(unittest.TestCase):
    """测试 JumiaClient.live_upload() 真实模式流程（mock transport）。"""

    def test_live_upload_blocked_no_token(self):
        """真实模式无 token → 健康检查 blocked。"""
        client = JumiaClient(dry_run=False)
        res = client.live_upload(make_product())
        self.assertEqual(res["status"], "blocked")

    def test_live_upload_blocked_guard_disabled(self):
        """真实模式有 token 但 guard 禁用 → failed。"""
        client = JumiaClient(
            auth=JumiaAuth(api_key="test-key"),
            dry_run=False,
            http_client=make_http_client(),
        )
        res = client.live_upload(make_product())
        self.assertEqual(res["status"], "failed")
        self.assertIsNotNone(res["upload_result"])
        self.assertFalse(res["upload_result"]["success"])
        self.assertTrue(res["upload_result"]["errors"])

    def test_live_upload_success(self):
        """真实模式有 token + guard 启用 → 上传成功。"""
        client = JumiaClient(
            auth=JumiaAuth(api_key="test-key"),
            dry_run=False,
            http_client=make_http_client(),
            upload_guard=UploadGuard(UploadGuardConfig(enabled=True, max_products=1)),
        )
        res = client.live_upload(make_product())
        self.assertEqual(res["status"], "success")
        self.assertTrue(res["upload_result"]["success"])
        self.assertEqual(res["upload_result"]["product_id"], "PROD-001")
        self.assertEqual(res["upload_result"]["offer_id"], "OFFER-001")
        self.assertEqual(res["upload_result"]["inventory_status"], "updated")

    def test_live_upload_create_product_delegates(self):
        """create_product() 真实模式委托给 live_upload()。"""
        client = JumiaClient(
            auth=JumiaAuth(api_key="test-key"),
            dry_run=False,
            http_client=make_http_client(),
            upload_guard=UploadGuard(UploadGuardConfig(enabled=True, max_products=1)),
        )
        res = client.create_product(make_product())
        self.assertEqual(res["status"], "success")
        self.assertTrue(res["upload_result"]["success"])


if __name__ == "__main__":
    unittest.main()
