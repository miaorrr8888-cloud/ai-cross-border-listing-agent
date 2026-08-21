"""Jumia 类目智能（P2-2）：类目树 + 两阶段匹配 + 属性 Schema。"""
from src.jumia.category.attribute_schema import (
    CATEGORY_ATTRIBUTES,
    AttributeSchema,
    get_optional_attributes,
    get_required_attributes,
)
from src.jumia.category.category_matcher import JumiaCategoryMatch, CategoryMatcher
from src.jumia.category.category_tree import BUILTIN_CATEGORY_TREE, CategoryNode, CategoryTree

__all__ = [
    "CategoryTree",
    "CategoryNode",
    "BUILTIN_CATEGORY_TREE",
    "CategoryMatcher",
    "JumiaCategoryMatch",
    "AttributeSchema",
    "CATEGORY_ATTRIBUTES",
    "get_required_attributes",
    "get_optional_attributes",
]
