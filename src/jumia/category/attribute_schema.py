"""Jumia 类目属性 Schema：根据类目 ID 返回必填/选填属性 + 缺失属性检测。

示例（与任务对齐）：
- Fashion（时尚）: size / color / material
- Electronics（电子）: brand / model / power

这里的 CATEGORY_ATTRIBUTES 是内置参考数据（可被真实 Jumia 属性 API 替换），
不是假 API 数据；它只服务于本地 dry-run 的类目属性校验与补全提示。
"""
from __future__ import annotations

from typing import Dict, List, Optional

# 类目 ID -> {required: [...], optional: [...]}
CATEGORY_ATTRIBUTES: Dict[str, Dict[str, List[str]]] = {
    "electronics": {"required": ["brand", "model", "power"], "optional": ["warranty", "color"]},
    "electronics_audio": {"required": ["brand", "model"], "optional": ["color", "connectivity", "battery_life"]},
    "electronics_phones": {"required": ["brand", "model", "storage"], "optional": ["ram", "color", "network"]},
    "fashion": {"required": ["size", "color", "material"], "optional": ["gender", "style"]},
    "fashion_women": {"required": ["size", "color", "material"], "optional": ["gender", "style"]},
    "fashion_shoes": {"required": ["size", "color", "material"], "optional": ["gender", "heel_height"]},
    "home_kitchen": {"required": ["material", "dimensions"], "optional": ["color", "capacity"]},
    "home_fans": {"required": ["brand", "power"], "optional": ["color", "dimensions", "speed_levels"]},
    "beauty": {"required": ["brand", "volume"], "optional": ["skin_type", "scent"]},
    "beauty_fragrance": {"required": ["brand", "volume"], "optional": ["scent", "gender"]},
    "baby_products": {"required": ["age_range", "material"], "optional": ["gender", "color"]},
    "general_merchandise": {"required": [], "optional": []},
}


class AttributeSchema:
    """根据类目提供必填/选填属性，并做缺失属性检测。"""

    def __init__(self, data: Optional[Dict[str, Dict[str, List[str]]]] = None):
        self._data = data if data is not None else CATEGORY_ATTRIBUTES

    def required(self, category_id: str) -> List[str]:
        return list(self._data.get(category_id, {}).get("required", []))

    def optional(self, category_id: str) -> List[str]:
        return list(self._data.get(category_id, {}).get("optional", []))

    # 别名（与任务术语一致）
    def required_attributes(self, category_id: str) -> List[str]:
        return self.required(category_id)

    def optional_attributes(self, category_id: str) -> List[str]:
        return self.optional(category_id)

    def missing_required(self, category_id: str, attributes: dict) -> List[str]:
        """返回缺失的必填属性键（值为空/None 视为缺失）。"""
        missing: List[str] = []
        for key in self.required(category_id):
            val = attributes.get(key)
            if val is None or (isinstance(val, str) and not val.strip()):
                missing.append(key)
        return missing


def get_required_attributes(category_id: str, schema: Optional[AttributeSchema] = None) -> List[str]:
    return (schema or AttributeSchema()).required(category_id)


def get_optional_attributes(category_id: str, schema: Optional[AttributeSchema] = None) -> List[str]:
    return (schema or AttributeSchema()).optional(category_id)
