"""上传安全守卫：默认禁止上传，限制单次上传数量。

安全规则：
1. ``enabled=False``（默认）→ 上传被禁止，抛 ``UploadDisabledError``。
2. ``count > max_products`` → 抛 ``UploadLimitExceededError``。
3. 第一次真实模式最多 1 个 SKU（``max_products=1``）。
4. 不允许批量上传（``max_products`` 始终为小数）。

红线：
- 默认 ``enabled=False``，即使 ``dry_run=False`` 也禁止上传。
- 只有显式配置 ``upload.enabled=true`` 才允许。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.jumia.api.errors import UploadDisabledError, UploadLimitExceededError


@dataclass
class UploadGuardConfig:
    """上传守卫配置。"""

    enabled: bool = False       # 默认禁止上传
    max_products: int = 1      # 单次最大上传 SKU 数量


class UploadGuard:
    """上传安全守卫：检查上传是否被允许、数量是否超限。

    默认 ``enabled=False`` → 任何上传请求都会被阻止。
    """

    def __init__(self, config: Optional[UploadGuardConfig] = None):
        self.config = config or UploadGuardConfig()

    def check_allowed(self, count: int = 1) -> bool:
        """检查上传是否被允许。

        - ``enabled=False`` → 抛 ``UploadDisabledError``。
        - ``count > max_products`` → 抛 ``UploadLimitExceededError``。
        - 通过 → 返回 ``True``。
        """
        if not self.config.enabled:
            raise UploadDisabledError(
                "上传已被禁用（upload.enabled=false）。"
                "请在 config.upload.enabled=true 时启用，"
                "并确保已配置有效的 Jumia API 凭据。"
            )
        if count > self.config.max_products:
            raise UploadLimitExceededError(
                f"上传数量 {count} 超过限制 {self.config.max_products}。"
                f"当前最多支持 {self.config.max_products} 个 SKU，不允许批量上传。"
            )
        return True

    @classmethod
    def from_config(cls, cfg: Optional[dict]) -> "UploadGuard":
        """从配置字典创建守卫（``config.upload`` 段）。"""
        upload_cfg = (cfg or {}).get("upload", {}) or {}
        return cls(UploadGuardConfig(
            enabled=upload_cfg.get("enabled", False),
            max_products=upload_cfg.get("max_products", 1),
        ))
