"""Jumia 认证：从环境变量/配置读取 token，缺失时返回 MissingCredential，绝不生成假 token。

凭据读取优先级（resolve()）：
1. 显式传入的 api_key
2. 显式传入的 api_token
3. 环境变量（JUMIA_API_KEY / JUMIA_API_TOKEN）
4. 配置文件（config.jumia.api_key / api_token）
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

ENV_API_KEY = "JUMIA_API_KEY"
ENV_API_TOKEN = "JUMIA_API_TOKEN"


class MissingCredential(Exception):
    """缺少认证凭据（token）时抛出的明确异常。"""


@dataclass
class JumiaAuth:
    api_key: str = ""
    api_token: str = ""

    def has_credential(self) -> bool:
        return bool(self.api_key or self.api_token)

    def resolve(self) -> str:
        """返回可用的凭据（api_key 优先）。缺失时抛 MissingCredential，绝不生成假 token。"""
        cred = self.api_key or self.api_token
        if not cred:
            raise MissingCredential(
                "缺少 Jumia API 凭据：请在环境变量（JUMIA_API_KEY / JUMIA_API_TOKEN）"
                "或 config.jumia.api_key / api_token 中提供。请勿使用假 token。"
            )
        return cred

    @classmethod
    def from_config(cls, cfg: Optional[dict]) -> "JumiaAuth":
        """从配置读取（config.jumia 段）。"""
        j = (cfg or {}).get("jumia", {}) or {}
        return cls(
            api_key=j.get("api_key", "") or "",
            api_token=j.get("api_token", "") or "",
        )

    @classmethod
    def from_env(cls) -> "JumiaAuth":
        """从环境变量读取。"""
        return cls(
            api_key=os.environ.get(ENV_API_KEY, "") or "",
            api_token=os.environ.get(ENV_API_TOKEN, "") or "",
        )

    def check_auth(self) -> dict:
        """认证健康检查：校验凭据是否已配置。

        返回 ``{"success": bool, "error": Optional[str], "message": str}``。
        没有 token 时抛 ``MissingCredential``（绝不生成假 token）。
        注意：本阶段只校验凭据存在性，不联网验证有效性。
        """
        if not self.has_credential():
            raise MissingCredential(
                "缺少 Jumia API 凭据，无法进行认证健康检查。"
                "请在环境变量（JUMIA_API_KEY / JUMIA_API_TOKEN）"
                "或 config.jumia.api_key / api_token 中提供。请勿使用假 token。"
            )
        return {
            "success": True,
            "error": None,
            "message": "凭据已配置（本阶段仅校验存在性，未联网验证有效性）。",
        }
