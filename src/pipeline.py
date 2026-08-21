"""可复用的 dry-run 流水线（被 main / batch 共用）。

任意输入（URL/JSON/Excel 行）-> Product -> AI 优化 -> 类目 -> 定价 ->
Jumia 映射 -> dry-run 上架计划 -> 上架前检查 -> 输出 dict。

全程 dry-run：不联网、不填假 token、不真正上传。
"""
from __future__ import annotations

from typing import Any, Dict

from src.ai.category_matcher import CategoryMatcher
from src.ai.providers import get_provider
from src.ai.title_optimizer import shorten
from src.jumia.api.payload_validator import validate_payload
from src.jumia.api.client import build_listing_payload
from src.jumia.api_client import JumiaAPIClient
from src.jumia.attribute_schema import AttributeSchema
from src.jumia.uploader import upload
from src.models.product import Product
from src.pricing.calculator import recommend_price
from src.validator.listing_check import check


def build_pipeline(cfg: dict):
    ai_cfg = cfg.get("ai", {})
    jumia_cfg = cfg.get("jumia", {})
    dry_run = cfg.get("app", {}).get("dry_run", True)
    provider = get_provider(
        ai_cfg.get("provider", "mock"),
        ai_cfg.get("api_key", ""),
        ai_cfg.get("model", ""),
    )
    matcher = CategoryMatcher(provider=ai_cfg.get("provider", "mock"))
    client = JumiaAPIClient(
        api_base_url=jumia_cfg.get("api_base_url", ""),
        api_key=jumia_cfg.get("api_key", ""),
        dry_run=dry_run,
    )
    return provider, matcher, client


def run(product: Product, cfg: dict) -> dict:
    provider, matcher, client = build_pipeline(cfg)
    pricing_cfg = cfg.get("pricing", {})

    # 1) AI 标题优化
    product.title_en = provider.optimize_title(product.title_cn, product.title_en)
    product.product_name = shorten(product.title_en, max_len=120)

    # 2) 类目匹配（两阶段：AI 商品理解 → Jumia 类目映射）
    match = matcher.match_detail(product)
    product.category_id = match.category_id
    product.category_name = match.category_name
    product.category = match.category_name  # 历史字段与 category_name 对齐
    product.category_confidence = round(match.confidence, 2)
    product.attributes.setdefault("_category_confidence", round(match.confidence, 2))

    # 2b) 属性 Schema：必填属性 + 缺失检测
    schema = AttributeSchema()
    product.required_attributes = schema.required(match.category_id)
    product.missing_attributes = schema.missing_required(match.category_id, product.attributes)

    # 3) 利润计算（如有成本价）
    price_plan = None
    if product.cost_price and product.cost_price > 0:
        plan = recommend_price(
            product.cost_price,
            shipping=0.0,
            commission_rate=pricing_cfg.get("default_commission_rate", 0.15),
            target_margin=pricing_cfg.get("default_target_margin", 0.30),
            currency=product.currency or pricing_cfg.get("currency", "RMB"),
        )
        product.attributes["_suggested_price"] = plan.sale_price
        price_plan = plan.__dict__

    # 4) Jumia 映射 + dry-run 上架计划
    listing, upload_result = upload(product, client, provider)

    # 4b) Jumia Payload 构建 + 校验（P3-1，dry-run，不发送请求）
    jumia_payload = build_listing_payload(product)
    payload_errors = validate_payload(jumia_payload["combined"])

    # 5) 上架前检查
    score, issues = check(product)

    return {
        "meta": {
            "dry_run": cfg.get("app", {}).get("dry_run", True),
            "source_url": product.source_url,
            "source_platform": product.source_platform,
        },
        "raw_product": product.to_dict(),
        "ai_optimized": {
            "title_en": product.title_en,
            "title_fr": product.language_versions.get("fr", {}).get("title", ""),
            "title_ar": product.language_versions.get("ar", {}).get("title", ""),
        },
        "jumia_listing": listing,
        "jumia_payloads": jumia_payload,
        "payload_validation": {"valid": not payload_errors, "errors": payload_errors},
        "category_suggestion": {
            "category_id": match.category_id,
            "category": match.category_name,
            "confidence": round(match.confidence, 2),
            "reason": match.reason,
        },
        "price_plan": price_plan,
        "listing_check": {"score": score, "issues": issues},
        "upload_result": upload_result,
    }
