"""Jumia 上传服务：单 SKU 真实上传闭环。

流程（``upload_product``）：
1. 构建 payload（product / offer / inventory）+ payload_validator 校验
2. upload_guard 检查（默认禁止，需显式启用）
3. create_product → POST /products（通过 ``http_client.post()``）
4. create_offer → POST /offers
5. update_inventory → PUT /inventory

返回 ``UploadResult{success, product_id, offer_id, inventory_status, errors}``。

安全规则：
- 默认 ``dry_run=true``：HTTP Client 返回预览，不发送。
- ``upload_guard.enabled=false``（默认）：禁止上传。
- 第一次真实模式最多 1 个 SKU。
- 不允许批量上传。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from src.jumia.api.errors import UploadDisabledError, UploadLimitExceededError
from src.jumia.api.inventory import build_inventory_payload, update_inventory
from src.jumia.api.offer import build_offer_payload, create_offer
from src.jumia.api.payload_validator import validate_payload
from src.jumia.api.product_create import build_product_payload, create_product
from src.jumia.api.upload_guard import UploadGuard
from src.models.product import Product


@dataclass
class UploadResult:
    """上传结果。"""

    success: bool = False
    product_id: Optional[str] = None
    offer_id: Optional[str] = None
    inventory_status: Optional[str] = None  # updated / failed / None
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "product_id": self.product_id,
            "offer_id": self.offer_id,
            "inventory_status": self.inventory_status,
            "errors": list(self.errors),
        }


class JumiaUploader:
    """Jumia 单 SKU 上传服务。

    依赖：
    - ``http_client``：``JumiaHttpClient`` 实例（dry-run 或真实模式）。
    - ``guard``：``UploadGuard`` 实例（默认禁止上传）。
    """

    def __init__(self, http_client, guard: Optional[UploadGuard] = None):
        self.http = http_client
        self.guard = guard or UploadGuard()

    def upload_product(self, product: Product) -> UploadResult:
        """执行单 SKU 上传流程。

        步骤：payload 构建 + 校验 → guard 检查 → create_product → create_offer → update_inventory。
        任意步骤失败则停止，返回已完成的步骤结果。
        """
        result = UploadResult()

        # ── 1. 构建 payload + 校验 ──────────────────────────
        prod_payload = build_product_payload(product)
        offer_payload = build_offer_payload(product)
        inv_payload = build_inventory_payload(
            product.sku or offer_payload["seller_sku"],
            offer_payload["stock"],
        )

        combined = dict(prod_payload)
        combined.update(offer_payload)
        errors = validate_payload(combined)
        if errors:
            result.errors = errors
            return result

        # ── 2. upload_guard 检查 ─────────────────────────────
        try:
            self.guard.check_allowed(1)
        except (UploadDisabledError, UploadLimitExceededError) as e:
            result.errors.append(str(e))
            return result

        # ── 3. create_product → POST /products ───────────────
        prod_resp = create_product(self.http, product)
        if not prod_resp.success:
            result.errors.append(
                f"商品创建失败 (HTTP {prod_resp.http_status}): {prod_resp.error}"
            )
            return result

        if prod_resp.data:
            result.product_id = (
                prod_resp.data.get("id")
                or prod_resp.data.get("product_id")
            )

        # ── 4. create_offer → POST /offers ──────────────────
        offer_resp = create_offer(self.http, product)
        if not offer_resp.success:
            result.errors.append(
                f"Offer 创建失败 (HTTP {offer_resp.http_status}): {offer_resp.error}"
            )
            return result

        if offer_resp.data:
            result.offer_id = (
                offer_resp.data.get("id")
                or offer_resp.data.get("offer_id")
            )

        # ── 5. update_inventory → PUT /inventory ─────────────
        inv_resp = update_inventory(
            self.http,
            product.sku or offer_payload["seller_sku"],
            offer_payload["stock"],
        )
        if not inv_resp.success:
            result.errors.append(
                f"库存更新失败 (HTTP {inv_resp.http_status}): {inv_resp.error}"
            )
            result.inventory_status = "failed"
            return result

        result.inventory_status = "updated"
        result.success = True
        return result
