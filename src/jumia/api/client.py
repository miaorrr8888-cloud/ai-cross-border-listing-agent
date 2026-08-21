"""Jumia Seller API 客户端（P3-2-B-2：单 SKU 真实上传闭环）。

- dry_run=True（默认）：组装 payload + 校验，返回计划，不联网、不需要 token。
  同时通过 ``JumiaHttpClient`` 生成请求预览（展示 WOULD 发送的 URL / headers / body）。
- dry_run=False（真实模式）：通过 ``live_upload()`` 执行上传流程：
  Health Check → UploadGuard → JumiaUploader。
  无 token 时健康检查返回 blocked；guard 默认禁止上传。

红线：
1. 默认 dry_run=True。
2. 真实上传需 ``upload.enabled=true`` + 有效 token。
3. Token 只从环境变量 / 配置读取。
4. 无 token 禁止运行（健康检查返回 blocked）。
5. 所有测试不联网。
"""
from __future__ import annotations

from typing import Optional

from src.jumia.api.auth import JumiaAuth
from src.jumia.api.health import check_health
from src.jumia.api.http_client import JumiaHttpClient
from src.jumia.api.inventory import build_inventory_payload
from src.jumia.api.offer import build_offer_payload
from src.jumia.api.payload_validator import validate_payload
from src.jumia.api.product_create import build_product_payload
from src.jumia.api.upload_guard import UploadGuard
from src.jumia.api.uploader import JumiaUploader
from src.jumia.category.attribute_schema import AttributeSchema
from src.models.product import Product


def build_listing_payload(product: Product, attribute_schema: Optional[AttributeSchema] = None) -> dict:
    """组装完整 Listing payload：product + offer + inventory + 校验用合并字段。

    - product：name / description / category_id / attributes / images / variants
    - offer：price / currency / stock / seller_sku
    - inventory：库存更新结构
    - combined：合并 product + offer + required_attributes，供 payload_validator 直接校验
    """
    prod = build_product_payload(product)
    offer = build_offer_payload(product)
    inv = build_inventory_payload(product.sku or "", offer["stock"])

    combined = dict(prod)
    combined.update(offer)

    schema = attribute_schema or AttributeSchema()
    combined["required_attributes"] = schema.required(prod.get("category_id", ""))

    return {
        "product": prod,
        "offer": offer,
        "inventory": inv,
        "combined": combined,
    }


class JumiaClient:
    """Jumia Seller API 客户端。

    - dry-run：构建 payload + 校验 + 请求预览（不发送 HTTP）。
    - 真实模式：通过 ``live_upload()`` 执行上传流程（Health Check → Guard → Uploader）。
    """

    def __init__(
        self,
        auth: Optional[JumiaAuth] = None,
        dry_run: bool = True,
        base_url: str = "",
        http_client: Optional[JumiaHttpClient] = None,
        http_timeout: float = 30.0,
        retry_count: int = 3,
        upload_guard: Optional[UploadGuard] = None,
    ):
        self.auth = auth or JumiaAuth()
        self.dry_run = dry_run
        self.base_url = base_url or ""
        # HTTP 客户端：dry_run 时不发送，真实模式时发送
        self.http = http_client or JumiaHttpClient(
            auth=self.auth,
            base_url=self.base_url,
            dry_run=dry_run,
            timeout=http_timeout,
            retry_count=retry_count,
        )
        # 上传守卫：默认禁止上传
        self.upload_guard = upload_guard or UploadGuard()

    def authenticate(self) -> dict:
        """dry-run 无需 token；真实模式必须能解析到 token，否则抛 MissingCredential。"""
        if self.dry_run:
            return {"status": "dry_run", "authenticated": False, "message": "dry-run 模式，无需 token"}
        token = self.auth.resolve()  # 缺失 → MissingCredential
        return {"status": "ok", "authenticated": True, "token_loaded": bool(token)}

    def create_product(self, product: Product) -> dict:
        """dry-run：组装 payload + 校验 + 请求预览（不发送 HTTP）。

        真实模式（dry_run=False）：通过 ``live_upload()`` 执行上传流程。
        """
        listing = build_listing_payload(product)
        errors = validate_payload(listing["combined"])

        if self.dry_run:
            # 生成请求预览（不发送）
            http_response = self.http.create_product(listing["combined"])
            return {
                "status": "dry_run",
                "endpoint": "POST /products",
                "payload": listing,
                "validation": {"valid": not errors, "errors": errors},
                "http_preview": http_response.to_dict(),
            }

        # 真实模式：通过 live_upload 执行上传
        return self.live_upload(product)

    def live_upload(self, product: Product) -> dict:
        """真实上传入口：Health Check → Guard → Uploader。

        安全规则：
        - dry_run=True → 返回 dry-run 预览（不上传）。
        - dry_run=False → 健康检查通过后，经 UploadGuard 检查，再执行上传。
        - upload_guard.enabled=false → 禁止上传，返回 failed。
        - 无 token → 健康检查返回 blocked。
        """
        if self.dry_run:
            return self.create_product(product)

        # 1. Health check
        health = check_health(self.auth, dry_run=False)
        if health.auth_status != "ok":
            return {
                "status": "blocked",
                "reason": f"健康检查失败: {health.message or health.auth_status}",
                "upload_result": None,
            }

        # 2. Guard + Uploader
        uploader = JumiaUploader(self.http, self.upload_guard)
        result = uploader.upload_product(product)

        return {
            "status": "success" if result.success else "failed",
            "upload_result": result.to_dict(),
        }

    # ── HTTP Client 真实模式接口 ───────────────────────────────

    def send_request(self, method: str, endpoint: str, payload: Optional[dict] = None) -> dict:
        """通过 ``JumiaHttpClient`` 发送请求。

        - dry-run：返回请求预览（不发送）。
        - 真实模式：发送 HTTP + 重试 + 解析（需 token）。

        注意：本方法可用于健康检查 / 类目查询 / 账户查询等非上传端点；
        商品上传请用 ``create_product()`` / ``live_upload()``。
        """
        response = self.http.request(method, endpoint, payload)
        return response.to_dict()

    def get(self, endpoint: str) -> dict:
        """GET 请求便捷方法。"""
        return self.http.get(endpoint).to_dict()

    def post(self, endpoint: str, payload: Optional[dict] = None) -> dict:
        """POST 请求便捷方法（非商品上传端点）。"""
        return self.http.post(endpoint, payload).to_dict()

    def put(self, endpoint: str, payload: Optional[dict] = None) -> dict:
        """PUT 请求便捷方法。"""
        return self.http.put(endpoint, payload).to_dict()
