"""上架前检查（Listing Score：评分 0~100 + 问题清单）。纯本地，无依赖。

P1 增强项：
- 标题长度（过短 / 过长）
- 描述长度（过短 / 过长）
- 图片数量
- 属性完整度
- 价格合理性（成本价、货币、建议售价是否低于成本）

P2-2 增强项：
- 是否有 category_id（是否映射到 Jumia 类目树）
- 必填属性是否完整（对照 required_attributes）
- 属性格式是否正确（必填属性值须为非空）
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from src.models.product import Product

TITLE_MIN = 10
TITLE_MAX = 120
DESC_MIN = 50
DESC_MAX = 2000
IMG_RECOMMENDED = 3
ATTR_MIN = 2


def _has_value(value) -> bool:
    """属性值是否非空（None / 空串视为缺失）。"""
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def check(product: Product) -> Tuple[float, List[str]]:
    """返回 (Listing Score 0~100, 问题清单)。"""
    issues: List[str] = []
    score = 100.0

    # 必填字段
    required = {
        "title_en": product.title_en,
        "product_name": product.product_name,
        "category": product.category,
        "brand": product.brand,
        "sku": product.sku,
    }
    for name, val in required.items():
        if not val:
            issues.append(f"缺少必填字段：{name}")
            score -= 15

    # P2-2：是否有 category_id
    if not product.category_id:
        issues.append("缺少 category_id（未映射到 Jumia 类目树）")
        score -= 5

    # P2-2：必填属性完整度 + 属性格式（值为空视为缺失）
    required_attrs = list(product.required_attributes)
    if required_attrs:
        missing = [a for a in required_attrs if not _has_value(product.attributes.get(a))]
        product.missing_attributes = missing
        if missing:
            issues.append(f"缺少类目必填属性：{', '.join(missing)}")
            score -= 10
    else:
        product.missing_attributes = []

    # 标题长度
    title = product.title_en or ""
    if title and len(title) < TITLE_MIN:
        issues.append(f"标题过短（<{TITLE_MIN}字符）")
        score -= 5
    elif title and len(title) > TITLE_MAX:
        issues.append(f"标题过长（>{TITLE_MAX}字符）")
        score -= 5

    # 描述长度
    desc = product.long_description or product.description or ""
    if not desc:
        issues.append("缺少商品描述")
        score -= 15
    elif len(desc) < DESC_MIN:
        issues.append(f"描述过短（<{DESC_MIN}字）")
        score -= 5
    elif len(desc) > DESC_MAX:
        issues.append(f"描述过长（>{DESC_MAX}字）")
        score -= 5

    # 图片数量
    if len(product.images) == 0:
        issues.append("无商品图片，建议至少 1 张")
        score -= 10
    elif len(product.images) < IMG_RECOMMENDED:
        issues.append(f"图片少于 {IMG_RECOMMENDED} 张，建议补充")

    # 属性完整度
    if len(product.attributes) < ATTR_MIN:
        issues.append(f"属性偏少，建议补充规格（颜色/尺寸等，至少 {ATTR_MIN} 项）")
        score -= 5

    # 关键词
    if len(product.keywords) == 0:
        issues.append("缺少关键词，影响搜索曝光")
        score -= 5

    # 多语言覆盖
    langs = set(product.language_versions.keys())
    for need in ("en", "fr", "ar"):
        if need not in langs:
            issues.append(f"缺少 {need} 语言版本")
            score -= 5

    # 价格合理性
    if not product.cost_price or product.cost_price <= 0:
        issues.append("未填写成本价，无法核算售价")
        score -= 10
    if not product.currency:
        issues.append("缺少货币单位")
        score -= 5

    sugg = product.attributes.get("_suggested_price")
    if sugg and product.cost_price and product.cost_price > 0:
        if sugg < product.cost_price * 1.1:
            issues.append("建议售价低于成本（< 成本 × 1.1）")
            score -= 10

    score = max(0.0, min(100.0, score))
    return score, issues
