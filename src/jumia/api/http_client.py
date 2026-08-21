"""Jumia API HTTP 客户端（P3-2-B-1）：真实 HTTP 层，但禁止真实商品上传。

设计原则（红线）：
1. 默认 ``dry_run=True`` —— 只生成请求结构，不发送 HTTP。
2. 不发送商品创建请求（``POST /products``）；``create_product()`` 在 P3-2-B-1 仍被禁止。
3. token 仅从 ``JumiaAuth``（环境变量 / 配置）读取，**绝不硬编码**。
4. ``dry_run=False``（真实模式）且无 token 时抛 ``MissingCredential``，禁止运行。
5. 所有测试不联网：测试通过 ``transport`` 注入 mock，不访问真实服务器。

架构：
```
JumiaHttpClient
  ├── RequestBuilder   → 构建 PreparedRequest（headers / auth / body）
  ├── RetryHandler     → 对 429/500/502/503 指数退避重试
  ├── transport        → 实际发送 HTTP（默认 urllib，可注入 mock）
  └── ResponseParser   → 统一解析为 ParsedResponse
```

扩展点：
- ``transport`` 参数可注入自定义发送函数（测试用 mock），签名：
  ``(method, url, headers, body, timeout) -> (status_code, response_body, response_headers)``
- 真实模式 ``dry_run=False`` 时 ``request()`` 发送真实 HTTP；
  但 ``create_product()`` / ``update_product()`` / ``create_offer()`` 仍被禁止（P3-2-B-2）。
"""
from __future__ import annotations

import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Callable, Optional

from src.jumia.api.auth import JumiaAuth, MissingCredential
from src.jumia.api.request_builder import PreparedRequest, RequestBuilder
from src.jumia.api.response_parser import ParsedResponse, ResponseParser
from src.jumia.api.retry import RetryConfig, RetryHandler

# transport 类型：发送函数签名
TransportFunc = Callable[
    [str, str, dict, Optional[bytes], float],  # method, url, headers, body, timeout
    tuple,  # (status_code, response_body, response_headers)
]


def default_transport(
    method: str,
    url: str,
    headers: dict,
    body: Optional[bytes],
    timeout: float,
) -> tuple:
    """默认 HTTP transport：使用标准库 ``urllib.request`` 发送。

    返回 ``(status_code, response_body, response_headers)``。
    仅供 ``dry_run=False`` 时调用；测试不调用此函数。
    """
    req = urllib.request.Request(url=url, data=body, method=method)
    for key, val in headers.items():
        req.add_header(key, val)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return (
                resp.status,
                resp.read(),
                dict(resp.headers),
            )
    except urllib.error.HTTPError as e:
        return (
            e.code,
            e.read() if hasattr(e, "read") else b"",
            dict(e.headers) if hasattr(e, "headers") else {},
        )


@dataclass
class HttpClientConfig:
    """HTTP 客户端配置。"""

    dry_run: bool = True
    timeout: float = 30.0
    retry_count: int = 3
    base_url: str = ""


class JumiaHttpClient:
    """Jumia API HTTP 客户端。

    - ``dry_run=True``（默认）：``request()`` 只构建请求预览，不发送。
    - ``dry_run=False``：``request()`` 发送真实 HTTP（需 token + transport）。
    - 无论哪种模式，``create_product()`` 等商品上传方法在 P3-2-B-1 仍被禁止。
    """

    def __init__(
        self,
        auth: Optional[JumiaAuth] = None,
        base_url: str = "",
        dry_run: bool = True,
        timeout: float = 30.0,
        retry_config: Optional[RetryConfig] = None,
        transport: Optional[TransportFunc] = None,
        retry_count: Optional[int] = None,
        sleep_func: Optional[Callable[[float], None]] = None,
    ):
        self.auth = auth or JumiaAuth()
        self.dry_run = dry_run
        self.timeout = timeout
        self.base_url = base_url
        self.builder = RequestBuilder(self.auth, base_url)

        # retry_config 优先级：显式传入 > retry_count 参数 > 默认
        if retry_config is None:
            rc_count = retry_count if retry_count is not None else 3
            retry_config = RetryConfig(max_retries=rc_count)
        # sleep_func 优先级：显式传入 > dry_run 时用 noop > 默认 time.sleep
        if sleep_func is not None:
            _sleep = sleep_func
        elif dry_run:
            _sleep = self._noop_sleep
        else:
            _sleep = None  # RetryHandler 默认用 time.sleep
        self.retry = RetryHandler(
            config=retry_config,
            sleep_func=_sleep,
        )

        # transport：真实模式用 default_transport；测试可注入 mock
        self._transport = transport or default_transport

    @staticmethod
    def _noop_sleep(seconds: float) -> None:
        """dry-run 模式不等待。"""
        pass

    # ── 核心方法 ──────────────────────────────────────────────

    def request(
        self,
        method: str,
        endpoint: str,
        payload: Optional[dict] = None,
    ) -> ParsedResponse:
        """统一请求入口。

        - ``dry_run=True``：构建请求预览（``build_preview``），不发送 HTTP。
          token 缺失时标记 ``has_auth=False``，仍返回预览（不抛异常）。
        - ``dry_run=False``：构建带认证请求（``build``），无 token 时抛
          ``MissingCredential``；发送 HTTP + 重试 + 解析。
        """
        if self.dry_run:
            prepared = self.builder.build_preview(method, endpoint, payload)
            return ResponseParser.parse_dry_run(prepared.to_dict())

        # 真实模式：必须有 token
        prepared = self.builder.build(method, endpoint, payload)  # 缺 token → MissingCredential

        # 发送（带重试）
        def _send() -> tuple:
            return self._transport(
                prepared.method,
                prepared.url,
                prepared.headers,
                prepared.body,
                self.timeout,
            )

        retry_result = self.retry.execute_with_retry(_send)
        return ResponseParser.parse(
            status_code=retry_result.final_status_code,
            body=retry_result.final_body,
            headers=retry_result.final_headers,
        )

    # ── 便捷方法 ──────────────────────────────────────────────

    def get(self, endpoint: str) -> ParsedResponse:
        return self.request("GET", endpoint)

    def post(self, endpoint: str, payload: Optional[dict] = None) -> ParsedResponse:
        return self.request("POST", endpoint, payload)

    def put(self, endpoint: str, payload: Optional[dict] = None) -> ParsedResponse:
        return self.request("PUT", endpoint, payload)

    # ── 商品上传（P3-2-B-1 仍禁止） ────────────────────────────

    def create_product(self, payload: dict) -> ParsedResponse:
        """商品创建请求（POST /products）。

        P3-2-B-1：**禁止真实商品上传**。dry-run 返回预览，真实模式抛
        ``NotImplementedError``。
        """
        if self.dry_run:
            prepared = self.builder.build_preview("POST", "/products", payload)
            return ResponseParser.parse_dry_run(prepared.to_dict())
        raise NotImplementedError(
            "P3-2-B-1 禁止真实商品上传（create_product 真实模式未实现）。"
            "请等待 P3-2-B-2 实现真实上传。"
        )
