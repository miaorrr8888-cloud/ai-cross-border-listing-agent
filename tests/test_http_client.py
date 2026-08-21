"""P3-2-B-1 HTTP Client 层测试：请求构造 / token 缺失 / retry 逻辑 / response 解析 / dry-run 不发送。

所有测试不联网：通过注入 mock transport 避免真实 HTTP 调用。
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.jumia.api import (
    JumiaAuth,
    JumiaHttpClient,
    MissingCredential,
    ParsedResponse,
    PreparedRequest,
    RequestBuilder,
    ResponseParser,
    RetryConfig,
    RetryHandler,
    RetryResult,
)
from src.jumia.api.retry import RETRYABLE_STATUS_CODES


# ════════════════════════════════════════════════════════════
#  Mock transport：模拟 HTTP 发送，不联网
# ════════════════════════════════════════════════════════════

def make_mock_transport(status_code=200, body=b'{"ok": true}', headers=None):
    """创建 mock transport：返回固定响应。"""
    resp_body = body
    resp_headers = headers or {"Content-Type": "application/json"}

    def _transport(method, url, req_headers, req_body, timeout):
        return (status_code, resp_body, resp_headers)
    return _transport


def make_sequence_transport(responses):
    """创建按顺序返回不同响应的 mock transport。

    responses: [(status_code, body, headers), ...]
    """
    idx = [0]

    def _transport(method, url, req_headers, req_body, timeout):
        resp = responses[min(idx[0], len(responses) - 1)]
        idx[0] += 1
        return (resp[0], resp[1], resp[2] if len(resp) > 2 else {})
    return _transport


def make_call_recorder_transport(status_code=200, body=b'{"ok": true}'):
    """创建记录调用参数的 mock transport。"""
    calls = []
    resp_body = body

    def _transport(method, url, req_headers, req_body, timeout):
        calls.append({
            "method": method,
            "url": url,
            "headers": dict(req_headers),
            "body": req_body,
            "timeout": timeout,
        })
        return (status_code, resp_body, {})

    return _transport, calls


# ════════════════════════════════════════════════════════════
#  1. Request Builder 测试
# ════════════════════════════════════════════════════════════

class TestRequestBuilder(unittest.TestCase):
    """测试 RequestBuilder：headers / auth / body 构造。"""

    def test_build_get_request(self):
        auth = JumiaAuth(api_key="test-key-123")
        builder = RequestBuilder(auth, base_url="https://api.jumia.com")
        req = builder.build("GET", "/products")
        self.assertEqual(req.method, "GET")
        self.assertEqual(req.url, "https://api.jumia.com/products")
        self.assertTrue(req.has_auth)
        self.assertIn("Authorization", req.headers)
        self.assertEqual(req.headers["Authorization"], "Bearer test-key-123")
        self.assertIsNone(req.body)

    def test_build_post_with_payload(self):
        auth = JumiaAuth(api_key="test-key-123")
        builder = RequestBuilder(auth, base_url="https://api.jumia.com")
        payload = {"name": "Test Product", "price": 29.99}
        req = builder.build("POST", "/products", payload)
        self.assertEqual(req.method, "POST")
        self.assertIsNotNone(req.body)
        import json
        parsed = json.loads(req.body)
        self.assertEqual(parsed["name"], "Test Product")
        self.assertEqual(parsed["price"], 29.99)

    def test_build_put_request(self):
        auth = JumiaAuth(api_token="token-xyz")
        builder = RequestBuilder(auth, base_url="https://api.jumia.com")
        req = builder.build("PUT", "/products/SKU-001", {"price": 15.0})
        self.assertEqual(req.method, "PUT")
        self.assertTrue(req.has_auth)

    def test_build_no_base_url(self):
        auth = JumiaAuth(api_key="k")
        builder = RequestBuilder(auth, base_url="")
        req = builder.build("GET", "/categories")
        self.assertEqual(req.url, "/categories")

    def test_build_with_extra_headers(self):
        auth = JumiaAuth(api_key="k")
        builder = RequestBuilder(auth, base_url="https://api.jumia.com")
        req = builder.build("GET", "/products", extra_headers={"X-Request-ID": "abc"})
        self.assertEqual(req.headers["X-Request-ID"], "abc")
        self.assertIn("Authorization", req.headers)

    def test_build_without_auth_preview(self):
        """build_preview 无 token 时标记 has_auth=False，不抛异常。"""
        builder = RequestBuilder(JumiaAuth(), base_url="https://api.jumia.com")
        req = builder.build_preview("GET", "/products")
        self.assertFalse(req.has_auth)
        self.assertNotIn("Authorization", req.headers)

    def test_build_without_auth_preview_with_token(self):
        """build_preview 有 token 时标记 has_auth=True。"""
        builder = RequestBuilder(JumiaAuth(api_key="k"), base_url="https://api.jumia.com")
        req = builder.build_preview("GET", "/products")
        self.assertTrue(req.has_auth)
        self.assertIn("Authorization", req.headers)

    def test_build_requires_token(self):
        """build() 无 token 时抛 MissingCredential。"""
        builder = RequestBuilder(JumiaAuth(), base_url="https://api.jumia.com")
        with self.assertRaises(MissingCredential):
            builder.build("GET", "/products")

    def test_no_hardcoded_token(self):
        """验证 headers 中不含硬编码 token（token 仅来自 auth）。"""
        auth = JumiaAuth(api_key="my-secret-key")
        builder = RequestBuilder(auth, base_url="")
        req = builder.build("GET", "/test")
        # Authorization 值应包含 auth 提供的 token，而非代码硬编码
        self.assertEqual(req.headers["Authorization"], "Bearer my-secret-key")
        # 代码中不应出现硬编码的 token 值
        for val in req.headers.values():
            self.assertNotIn("hardcoded", str(val).lower())

    def test_prepared_request_to_dict(self):
        req = PreparedRequest(
            method="POST",
            url="https://api.jumia.com/products",
            headers={"Content-Type": "application/json"},
            body=b'{"name": "Test"}',
            has_auth=True,
        )
        d = req.to_dict()
        self.assertEqual(d["method"], "POST")
        self.assertEqual(d["url"], "https://api.jumia.com/products")
        self.assertIn("name", d["body"])


# ════════════════════════════════════════════════════════════
#  2. Token 缺失测试
# ════════════════════════════════════════════════════════════

class TestTokenMissing(unittest.TestCase):
    """测试无 token 时真实模式禁止运行。"""

    def test_real_mode_no_token_raises(self):
        """真实模式无 token → request() 抛 MissingCredential。"""
        client = JumiaHttpClient(
            auth=JumiaAuth(),
            dry_run=False,
            transport=make_mock_transport(200),
        )
        with self.assertRaises(MissingCredential):
            client.request("GET", "/products")

    def test_real_mode_no_token_raises_post(self):
        client = JumiaHttpClient(
            auth=JumiaAuth(),
            dry_run=False,
            transport=make_mock_transport(200),
        )
        with self.assertRaises(MissingCredential):
            client.post("/products", {"name": "X"})

    def test_dry_run_no_token_does_not_raise(self):
        """dry-run 模式无 token → 不抛异常，返回预览（has_auth=False）。"""
        client = JumiaHttpClient(
            auth=JumiaAuth(),
            dry_run=True,
        )
        resp = client.request("GET", "/products")
        self.assertFalse(resp.success)
        self.assertEqual(resp.http_status, 0)
        self.assertEqual(resp.error_type, "DryRun")

    def test_real_mode_with_token_works(self):
        """真实模式有 token → 正常发送（mock transport）。"""
        client = JumiaHttpClient(
            auth=JumiaAuth(api_key="real-key"),
            dry_run=False,
            transport=make_mock_transport(200, b'{"ok": true}'),
        )
        resp = client.request("GET", "/products")
        self.assertTrue(resp.success)
        self.assertEqual(resp.http_status, 200)

    def test_token_only_from_env_or_config(self):
        """验证 token 来源：环境变量。"""
        os.environ["JUMIA_API_KEY"] = "env-token-123"
        try:
            auth = JumiaAuth.from_env()
            self.assertEqual(auth.resolve(), "env-token-123")
        finally:
            del os.environ["JUMIA_API_KEY"]


# ════════════════════════════════════════════════════════════
#  3. Retry 逻辑测试
# ════════════════════════════════════════════════════════════

class TestRetryLogic(unittest.TestCase):
    """测试 RetryHandler：429/500/502/503 重试，其他不重试。"""

    def test_should_retry_429(self):
        handler = RetryHandler(RetryConfig(max_retries=3), sleep_func=lambda s: None)
        self.assertTrue(handler.should_retry(429, 0))

    def test_should_retry_500(self):
        handler = RetryHandler(RetryConfig(max_retries=3), sleep_func=lambda s: None)
        self.assertTrue(handler.should_retry(500, 0))

    def test_should_retry_502(self):
        handler = RetryHandler(RetryConfig(max_retries=3), sleep_func=lambda s: None)
        self.assertTrue(handler.should_retry(502, 0))

    def test_should_retry_503(self):
        handler = RetryHandler(RetryConfig(max_retries=3), sleep_func=lambda s: None)
        self.assertTrue(handler.should_retry(503, 0))

    def test_should_not_retry_200(self):
        handler = RetryHandler(RetryConfig(max_retries=3), sleep_func=lambda s: None)
        self.assertFalse(handler.should_retry(200, 0))

    def test_should_not_retry_404(self):
        handler = RetryHandler(RetryConfig(max_retries=3), sleep_func=lambda s: None)
        self.assertFalse(handler.should_retry(404, 0))

    def test_should_not_retry_401(self):
        handler = RetryHandler(RetryConfig(max_retries=3), sleep_func=lambda s: None)
        self.assertFalse(handler.should_retry(401, 0))

    def test_should_not_retry_beyond_max(self):
        """超过 max_retries 不再重试。"""
        handler = RetryHandler(RetryConfig(max_retries=2), sleep_func=lambda s: None)
        self.assertFalse(handler.should_retry(429, 2))
        self.assertFalse(handler.should_retry(429, 3))

    def test_exponential_backoff_delay(self):
        """验证指数退避：delay = base * 2^attempt，上限 max_delay。"""
        handler = RetryHandler(
            RetryConfig(max_retries=3, base_delay=1.0, max_delay=30.0, jitter=0.0),
            sleep_func=lambda s: None,
        )
        self.assertAlmostEqual(handler.compute_delay(0), 1.0)
        self.assertAlmostEqual(handler.compute_delay(1), 2.0)
        self.assertAlmostEqual(handler.compute_delay(2), 4.0)
        self.assertAlmostEqual(handler.compute_delay(3), 8.0)

    def test_delay_capped_at_max(self):
        """退避延迟不超过 max_delay。"""
        handler = RetryHandler(
            RetryConfig(max_retries=10, base_delay=10.0, max_delay=30.0, jitter=0.0),
            sleep_func=lambda s: None,
        )
        self.assertAlmostEqual(handler.compute_delay(10), 30.0)

    def test_retry_on_429_then_success(self):
        """429 → 重试 → 200 成功。"""
        transport = make_sequence_transport([
            (429, b'{"error": "rate limit"}', {}),
            (200, b'{"ok": true}', {}),
        ])
        client = JumiaHttpClient(
            auth=JumiaAuth(api_key="k"),
            dry_run=False,
            transport=transport,
            retry_config=RetryConfig(max_retries=3, jitter=0.0),
            sleep_func=lambda s: None,
        )
        resp = client.request("GET", "/products")
        self.assertTrue(resp.success)
        self.assertEqual(resp.http_status, 200)

    def test_retry_on_500_then_success(self):
        """500 → 重试 → 200 成功。"""
        transport = make_sequence_transport([
            (500, b'{"error": "server error"}', {}),
            (200, b'{"ok": true}', {}),
        ])
        client = JumiaHttpClient(
            auth=JumiaAuth(api_key="k"),
            dry_run=False,
            transport=transport,
            retry_config=RetryConfig(max_retries=3, jitter=0.0),
            sleep_func=lambda s: None,
        )
        resp = client.request("GET", "/products")
        self.assertTrue(resp.success)

    def test_retry_on_502_then_success(self):
        transport = make_sequence_transport([
            (502, b'{"error": "bad gateway"}', {}),
            (200, b'{"ok": true}', {}),
        ])
        client = JumiaHttpClient(
            auth=JumiaAuth(api_key="k"),
            dry_run=False,
            transport=transport,
            retry_config=RetryConfig(max_retries=3, jitter=0.0),
            sleep_func=lambda s: None,
        )
        resp = client.request("GET", "/products")
        self.assertTrue(resp.success)

    def test_retry_on_503_then_success(self):
        transport = make_sequence_transport([
            (503, b'{"error": "service unavailable"}', {}),
            (200, b'{"ok": true}', {}),
        ])
        client = JumiaHttpClient(
            auth=JumiaAuth(api_key="k"),
            dry_run=False,
            transport=transport,
            retry_config=RetryConfig(max_retries=3, jitter=0.0),
            sleep_func=lambda s: None,
        )
        resp = client.request("GET", "/products")
        self.assertTrue(resp.success)

    def test_no_retry_on_404(self):
        """404 不重试，直接返回错误。"""
        call_count = [0]
        def transport(method, url, req_headers, req_body, timeout):
            call_count[0] += 1
            return (404, b'{"error": "not found"}', {})
        client = JumiaHttpClient(
            auth=JumiaAuth(api_key="k"),
            dry_run=False,
            transport=transport,
            retry_config=RetryConfig(max_retries=3, jitter=0.0),
            sleep_func=lambda s: None,
        )
        resp = client.request("GET", "/products/999")
        self.assertFalse(resp.success)
        self.assertEqual(resp.http_status, 404)
        self.assertEqual(call_count[0], 1)  # 只调用一次

    def test_retry_exhausted_returns_last_error(self):
        """重试耗尽后返回最后一次错误响应。"""
        transport = make_mock_transport(503, b'{"error": "still down"}')
        client = JumiaHttpClient(
            auth=JumiaAuth(api_key="k"),
            dry_run=False,
            transport=transport,
            retry_config=RetryConfig(max_retries=2, jitter=0.0),
            sleep_func=lambda s: None,
        )
        resp = client.request("GET", "/products")
        self.assertFalse(resp.success)
        self.assertEqual(resp.http_status, 503)
        self.assertIn("still down", resp.error)

    def test_retry_count_matches_config(self):
        """重试次数 = max_retries（总请求数 = max_retries + 1）。"""
        call_count = [0]
        def transport(method, url, req_headers, req_body, timeout):
            call_count[0] += 1
            return (500, b'{"error": "server error"}', {})
        client = JumiaHttpClient(
            auth=JumiaAuth(api_key="k"),
            dry_run=False,
            transport=transport,
            retry_config=RetryConfig(max_retries=3, jitter=0.0),
            sleep_func=lambda s: None,
        )
        resp = client.request("GET", "/products")
        # max_retries=3 → 4 次请求（1 初始 + 3 重试）
        self.assertEqual(call_count[0], 4)

    def test_jitter_within_bounds(self):
        """jitter 使得 delay 在 ±jitter*delay 范围内波动。"""
        handler = RetryHandler(
            RetryConfig(max_retries=3, base_delay=2.0, max_delay=30.0, jitter=0.5),
            sleep_func=lambda s: None,
        )
        for _ in range(20):
            delay = handler.compute_delay(1)
            # base=2, attempt=1 → base_delay = 4.0; jitter ±2.0 → [2.0, 6.0]
            self.assertGreaterEqual(delay, 2.0 - 0.01)
            self.assertLessEqual(delay, 6.0 + 0.01)

    def test_retry_result_tracks_attempts(self):
        """RetryResult 记录每次尝试。"""
        transport = make_sequence_transport([
            (429, b'rate limit', {}),
            (500, b'server error', {}),
            (200, b'{"ok": true}', {}),
        ])
        client = JumiaHttpClient(
            auth=JumiaAuth(api_key="k"),
            dry_run=False,
            transport=transport,
            retry_config=RetryConfig(max_retries=3, jitter=0.0),
        )
        # 通过 retry handler 直接验证
        handler = RetryHandler(
            RetryConfig(max_retries=3, jitter=0.0),
            sleep_func=lambda s: None,
        )
        result = handler.execute_with_retry(lambda: transport("GET", "url", {}, None, 30))
        self.assertIsInstance(result, RetryResult)
        self.assertEqual(len(result.attempts), 3)
        self.assertEqual(result.attempts[0].status_code, 429)
        self.assertEqual(result.attempts[1].status_code, 500)
        self.assertEqual(result.attempts[2].status_code, 200)
        self.assertEqual(result.total_retries, 2)
        self.assertEqual(result.final_status_code, 200)

    def test_retryable_status_codes_set(self):
        """验证可重试状态码集合。"""
        self.assertEqual(RETRYABLE_STATUS_CODES, {429, 500, 502, 503})


# ════════════════════════════════════════════════════════════
#  4. Response Parser 测试
# ════════════════════════════════════════════════════════════

class TestResponseParser(unittest.TestCase):
    """测试 ResponseParser：success / error / http_status 解析。"""

    def test_parse_success_response(self):
        resp = ResponseParser.parse(200, b'{"ok": true, "data": [1, 2]}', {})
        self.assertTrue(resp.success)
        self.assertEqual(resp.http_status, 200)
        self.assertEqual(resp.data["ok"], True)
        self.assertEqual(resp.data["data"], [1, 2])
        self.assertIsNone(resp.error)
        self.assertIsNone(resp.error_type)

    def test_parse_success_no_body(self):
        resp = ResponseParser.parse(204, b"", {})
        self.assertTrue(resp.success)
        self.assertEqual(resp.http_status, 204)
        self.assertIsNone(resp.data)

    def test_parse_401_error(self):
        resp = ResponseParser.parse(401, b'{"message": "Unauthorized"}', {})
        self.assertFalse(resp.success)
        self.assertEqual(resp.http_status, 401)
        self.assertEqual(resp.error, "Unauthorized")
        self.assertEqual(resp.error_type, "AuthenticationError")

    def test_parse_403_error(self):
        resp = ResponseParser.parse(403, b'{"error": "Forbidden"}', {})
        self.assertFalse(resp.success)
        self.assertEqual(resp.http_status, 403)
        self.assertEqual(resp.error, "Forbidden")
        self.assertEqual(resp.error_type, "PermissionError")

    def test_parse_429_error(self):
        resp = ResponseParser.parse(429, b'{"error": "Too Many Requests"}', {})
        self.assertFalse(resp.success)
        self.assertEqual(resp.http_status, 429)
        self.assertEqual(resp.error_type, "RateLimitError")

    def test_parse_500_error(self):
        resp = ResponseParser.parse(500, b'{"error": "Internal Server Error"}', {})
        self.assertFalse(resp.success)
        self.assertEqual(resp.http_status, 500)
        self.assertEqual(resp.error_type, "JumiaAPIError")

    def test_parse_non_json_error(self):
        """非 JSON 响应体也能解析。"""
        resp = ResponseParser.parse(502, b"Bad Gateway", {})
        self.assertFalse(resp.success)
        self.assertEqual(resp.http_status, 502)
        self.assertIn("Bad Gateway", resp.error)

    def test_parse_string_body(self):
        """str 类型的 body 也能解析。"""
        resp = ResponseParser.parse(200, '{"ok": true}', {})
        self.assertTrue(resp.success)
        self.assertEqual(resp.data["ok"], True)

    def test_parse_none_body(self):
        resp = ResponseParser.parse(200, None, {})
        self.assertTrue(resp.success)
        self.assertIsNone(resp.data)

    def test_parse_preserves_headers(self):
        resp = ResponseParser.parse(200, b'{"ok": true}', {"X-Request-ID": "abc"})
        self.assertEqual(resp.headers["X-Request-ID"], "abc")

    def test_parse_dry_run(self):
        """dry-run 预览响应。"""
        resp = ResponseParser.parse_dry_run({"method": "GET", "url": "/products"})
        self.assertFalse(resp.success)
        self.assertEqual(resp.http_status, 0)
        self.assertEqual(resp.error_type, "DryRun")
        self.assertIn("prepared_request", resp.data)

    def test_parsed_response_to_dict(self):
        resp = ParsedResponse(
            success=True,
            http_status=200,
            data={"ok": True},
            error=None,
        )
        d = resp.to_dict()
        self.assertTrue(d["success"])
        self.assertEqual(d["http_status"], 200)


# ════════════════════════════════════════════════════════════
#  5. Dry-Run 不发送测试
# ════════════════════════════════════════════════════════════

class TestDryRunNoSend(unittest.TestCase):
    """测试 dry-run 模式不发送 HTTP。"""

    def test_dry_run_request_returns_preview(self):
        """dry-run request() 返回预览，不调用 transport。"""
        transport_called = [False]

        def transport(method, url, headers, body, timeout):
            transport_called[0] = True
            return (200, b'{}', {})

        client = JumiaHttpClient(
            auth=JumiaAuth(api_key="k"),
            dry_run=True,
            transport=transport,
        )
        resp = client.request("GET", "/products")
        self.assertFalse(resp.success)
        self.assertEqual(resp.http_status, 0)
        self.assertEqual(resp.error_type, "DryRun")
        self.assertFalse(transport_called[0], "dry-run 模式不应调用 transport")

    def test_dry_run_get(self):
        client = JumiaHttpClient(auth=JumiaAuth(api_key="k"), dry_run=True)
        resp = client.get("/categories")
        self.assertEqual(resp.http_status, 0)
        self.assertEqual(resp.error_type, "DryRun")

    def test_dry_run_post(self):
        client = JumiaHttpClient(auth=JumiaAuth(api_key="k"), dry_run=True)
        resp = client.post("/products", {"name": "Test"})
        self.assertEqual(resp.http_status, 0)
        self.assertEqual(resp.error_type, "DryRun")
        # 预览中应包含请求结构
        self.assertIn("prepared_request", resp.data)
        prepared = resp.data["prepared_request"]
        self.assertEqual(prepared["method"], "POST")
        self.assertIn("/products", prepared["url"])

    def test_dry_run_put(self):
        client = JumiaHttpClient(auth=JumiaAuth(api_key="k"), dry_run=True)
        resp = client.put("/products/SKU-001", {"price": 29.99})
        self.assertEqual(resp.http_status, 0)
        self.assertEqual(resp.error_type, "DryRun")

    def test_dry_run_create_product(self):
        """dry-run create_product() 返回预览，不发送。"""
        client = JumiaHttpClient(auth=JumiaAuth(api_key="k"), dry_run=True)
        resp = client.create_product({"name": "Test", "price": 29.99})
        self.assertFalse(resp.success)
        self.assertEqual(resp.http_status, 0)
        self.assertEqual(resp.error_type, "DryRun")
        self.assertIn("prepared_request", resp.data)

    def test_dry_run_no_token_still_works(self):
        """dry-run 无 token 也能生成预览。"""
        client = JumiaHttpClient(auth=JumiaAuth(), dry_run=True)
        resp = client.request("GET", "/products")
        self.assertEqual(resp.http_status, 0)
        # 预览中 has_auth=False
        prepared = resp.data["prepared_request"]
        self.assertFalse(prepared["has_auth"])

    def test_dry_run_preview_includes_headers(self):
        """预览中包含 headers 信息。"""
        client = JumiaHttpClient(auth=JumiaAuth(api_key="k"), dry_run=True)
        resp = client.request("POST", "/products", {"name": "X"})
        prepared = resp.data["prepared_request"]
        self.assertIn("Content-Type", prepared["headers"])
        self.assertIn("Authorization", prepared["headers"])

    def test_dry_run_preview_includes_body(self):
        """预览中包含 body。"""
        client = JumiaHttpClient(auth=JumiaAuth(api_key="k"), dry_run=True)
        resp = client.post("/products", {"name": "Test Product", "price": 19.99})
        prepared = resp.data["prepared_request"]
        self.assertIsNotNone(prepared["body"])
        import json
        body = json.loads(prepared["body"])
        self.assertEqual(body["name"], "Test Product")

    def test_dry_run_no_sleep(self):
        """dry-run 模式不执行 sleep（sleep_func 为 noop）。"""
        sleep_called = [False]

        def tracking_sleep(seconds):
            sleep_called[0] = True

        # dry-run 时 sleep_func 固定为 _noop_sleep，不使用传入的
        client = JumiaHttpClient(
            auth=JumiaAuth(api_key="k"),
            dry_run=True,
        )
        client.request("GET", "/products")
        # dry-run 不发送 HTTP，不会触发 retry/sleep
        self.assertFalse(sleep_called[0])


# ════════════════════════════════════════════════════════════
#  6. HTTP Client 集成测试（mock transport）
# ════════════════════════════════════════════════════════════

class TestHttpClientIntegration(unittest.TestCase):
    """HTTP Client 端到端集成（mock transport，不联网）。"""

    def test_get_success(self):
        transport, calls = make_call_recorder_transport(200, b'{"products": []}')
        client = JumiaHttpClient(
            auth=JumiaAuth(api_key="k"),
            dry_run=False,
            transport=transport,
        )
        resp = client.get("/products")
        self.assertTrue(resp.success)
        self.assertEqual(resp.http_status, 200)
        # 验证 transport 被调用
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["method"], "GET")
        self.assertIn("/products", calls[0]["url"])
        self.assertIn("Authorization", calls[0]["headers"])

    def test_post_with_payload(self):
        transport, calls = make_call_recorder_transport(201, b'{"id": "PROD-001"}')
        client = JumiaHttpClient(
            auth=JumiaAuth(api_key="k"),
            dry_run=False,
            transport=transport,
        )
        resp = client.post("/products", {"name": "Test", "price": 29.99})
        self.assertTrue(resp.success)
        self.assertEqual(resp.http_status, 201)
        self.assertEqual(resp.data["id"], "PROD-001")
        # 验证 body 被发送
        self.assertIsNotNone(calls[0]["body"])

    def test_put_update(self):
        transport, calls = make_call_recorder_transport(200, b'{"ok": true}')
        client = JumiaHttpClient(
            auth=JumiaAuth(api_key="k"),
            dry_run=False,
            transport=transport,
        )
        resp = client.put("/products/SKU-001", {"price": 19.99})
        self.assertTrue(resp.success)
        self.assertEqual(calls[0]["method"], "PUT")

    def test_timeout_passed_to_transport(self):
        transport, calls = make_call_recorder_transport(200)
        client = JumiaHttpClient(
            auth=JumiaAuth(api_key="k"),
            dry_run=False,
            transport=transport,
            timeout=5.0,
        )
        client.get("/products")
        self.assertEqual(calls[0]["timeout"], 5.0)

    def test_real_mode_create_product_forbidden(self):
        """真实模式 create_product() 仍被禁止（P3-2-B-1）。"""
        client = JumiaHttpClient(
            auth=JumiaAuth(api_key="k"),
            dry_run=False,
            transport=make_mock_transport(200),
        )
        with self.assertRaises(NotImplementedError):
            client.create_product({"name": "Test"})

    def test_base_url_concatenation(self):
        transport, calls = make_call_recorder_transport(200)
        client = JumiaHttpClient(
            auth=JumiaAuth(api_key="k"),
            base_url="https://sellercenter.jumia.com/api",
            dry_run=False,
            transport=transport,
        )
        client.get("/products")
        self.assertEqual(calls[0]["url"], "https://sellercenter.jumia.com/api/products")


if __name__ == "__main__":
    unittest.main()
