"""Jumia Payload 校验：必须字段 + required_attributes 满足性。纯本地，可测试。"""
from __future__ import annotations

from typing import List, Optional

# 必须字段
REQUIRED_FIELDS = ("name", "category_id", "price", "currency")


def _has_value(value) -> bool:
    """判断字段/属性值是否非空（None / 空串 / 0 视为缺失）。"""
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (int, float)):
        return value != 0
    return True


def validate_payload(payload: dict, required_attributes: Optional[List[str]] = None) -> List[str]:
    """校验 payload，返回错误清单（空列表表示通过）。

    - 必须字段：name / category_id / price / currency
    - 必填属性：required_attributes 是否在 attributes 中满足
    """
    errors: List[str] = []
    for field in REQUIRED_FIELDS:
        if not _has_value(payload.get(field)):
            errors.append(f"缺少必须字段：{field}")

    req = required_attributes if required_attributes is not None else (payload.get("required_attributes") or [])
    attributes = payload.get("attributes") or {}
    for attr in req:
        if not _has_value(attributes.get(attr)):
            errors.append(f"缺少必填属性：{attr}")

    return errors
