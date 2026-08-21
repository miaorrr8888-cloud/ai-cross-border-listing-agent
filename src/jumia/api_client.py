"""Jumia API 客户端（MVP 仅 dry-run 骨架，不联网、无假 token）。

未来接入真实 Jumia SellerCenter API 时：
1. 在 config.jumia 填写 api_base_url 与 api_key（不要硬编码）。
2. 把 _request 替换为真实 HTTP 调用（如 requests）。
3. 将 uploader 的 dry_run 切换为 False 即可真正上传。

注意：本文件绝不预置任何假 API Token。
"""
from __future__ import annotations

from typing import Any, Dict


class JumiaAPIClient:
    def __init__(
        self,
        api_base_url: str = "",
        api_key: str = "",
        dry_run: bool = True,
    ):
        self.api_base_url = api_base_url
        self.api_key = api_key
        self.dry_run = dry_run

    def authenticate(self) -> Dict[str, Any]:
        if self.dry_run:
            return {
                "status": "dry_run",
                "authenticated": False,
                "note": "MVP 默认 dry-run，不发起真实认证。",
            }
        # TODO: 真实实现时使用 api_key 调用 Jumia OAuth / SellerCenter 鉴权
        raise NotImplementedError("真实认证需在 config 配置 api_key 后实现。")

    def create_product(self, listing: Dict[str, Any]) -> Dict[str, Any]:
        if self.dry_run:
            return {
                "status": "dry_run",
                "action": "create_product",
                "would_send": True,
                "listing_preview": listing,
            }
        # TODO: 真实实现时 POST 到 Jumia SellerCenter API
        raise NotImplementedError("真实上传需在配置 api_key 并接好 HTTP 客户端后启用。")
