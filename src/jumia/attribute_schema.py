"""属性 Schema 重导出：单一来源在 src/jumia/category/attribute_schema.py。

对外提供根据类目返回 required_attributes / optional_attributes / 缺失属性检测。
"""
from src.jumia.category.attribute_schema import (
    CATEGORY_ATTRIBUTES,
    AttributeSchema,
    get_optional_attributes,
    get_required_attributes,
)

__all__ = [
    "AttributeSchema",
    "CATEGORY_ATTRIBUTES",
    "get_required_attributes",
    "get_optional_attributes",
]
