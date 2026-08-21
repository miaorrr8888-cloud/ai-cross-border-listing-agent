"""Jumia API 请求构建器：组装 headers / auth / body，绝不硬编码 token。

职责：
- 接收 method + endpoint + payload + JumiaAuth，输出 ``PreparedRequest``。
- token 来源仅为 ``JumiaAuth``（环境变量 / 配置），缺失时抛 ``MissingCredential``。
- **禁止**在代码中硬编码任何 API Key / Token 值。

dry-run 场景可用 ``build_preview()`` 生成请求结构（无 token 时标记 ``has_auth=False``），
真实场景用 ``build()``（无 token 时抛异常）。
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from src.jumia.api.auth import JumiaAuth, MissingCredential

# 固定 header 模板（不含 token）
DEFAULT_CONTENT_TYPE = "application/json"
DEFAULT_ACCEPT = "application/json"
DEFAULT_USER_AGENT = "JumiaAIListingAgent/0.6.0"


@dataclass
class PreparedRequest:
    """构建好的请求结构。

    - dry-run 模式：可直接展示（``to_dict()``），不发送。
    - 真实模式：交给 ``urllib.request`` 发送。
    """

    method: str
    url: str
    headers: dict
    body: Optional[bytes] = None
    has_auth: bool = False

    def to_dict(self) -> dict:
        return {
            "method": self.method,
            "url": self.url,
            "headers": dict(self.headers),
            "body": self.body.decode("utf-8") if self.body else None,
            "has_auth": self.has_auth,
        }


class RequestBuilder:
    """Jumia API 请求构建器：组装 headers / auth / body。

    token 来自 ``JumiaAuth``（环境变量 / 配置），**绝不硬编码**。
    """

    def __init__(self, auth: JumiaAuth, base_url: str = ""):
        self.auth = auth
        self.base_url = base_url.rstrip("/") if base_url else ""

    # ── 内部工具 ──────────────────────────────────────────────

    def _resolve_token(self) -> str:
        """从 auth 获取 token；缺失时抛 ``MissingCredential``，绝不生成假值。"""
        return self.auth.resolve()

    def _build_url(self, endpoint: str) -> str:
        endpoint = endpoint.lstrip("/")
        if not self.base_url:
            return f"/{endpoint}"
        return f"{self.base_url}/{endpoint}"

    def _build_headers(self, token: Optional[str], extra: Optional[dict] = None) -> dict:
        headers = {
            "Content-Type": DEFAULT_CONTENT_TYPE,
            "Accept": DEFAULT_ACCEPT,
            "User-Agent": DEFAULT_USER_AGENT,
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if extra:
            headers.update(extra)
        return headers

    @staticmethod
    def _build_body(payload: Optional[dict]) -> Optional[bytes]:
        if payload is None:
            return None
        return json.dumps(payload, ensure_ascii=False).encode("utf-8")

    # ── 公开接口 ──────────────────────────────────────────────

    def build(
        self,
        method: str,
        endpoint: str,
        payload: Optional[dict] = None,
        extra_headers: Optional[dict] = None,
    ) -> PreparedRequest:
        """构建带认证的请求。token 缺失时抛 ``MissingCredential``。"""
        token = self._resolve_token()
        url = self._build_url(endpoint)
        headers = self._build_headers(token, extra_headers)
        body = self._build_body(payload)
        return PreparedRequest(
            method=method.upper(),
            url=url,
            headers=headers,
            body=body,
            has_auth=True,
        )

    def build_preview(
        self,
        method: str,
        endpoint: str,
        payload: Optional[dict] = None,
        extra_headers: Optional[dict] = None,
    ) -> PreparedRequest:
        """构建请求预览（dry-run 用）：token 缺失时标记 ``has_auth=False``，不抛异常。"""
        token = None
        try:
            token = self._resolve_token()
        except MissingCredential:
            token = None  # dry-run 下无 token 也允许生成预览
        url = self._build_url(endpoint)
        headers = self._build_headers(token, extra_headers)
        body = self._build_body(payload)
        return PreparedRequest(
            method=method.upper(),
            url=url,
            headers=headers,
            body=body,
            has_auth=bool(token),
        )
