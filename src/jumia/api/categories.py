"""Jumia Category API 接口骨架（P3-2-A：dry-run 返回结构定义，不假装真实数据）。

真实 Category API 未接入；本阶段 ``get_categories()`` / ``get_attributes()`` 返回
明确标记 ``status=dry_run`` 的结构（来源为内置参考类目树/属性 Schema），
绝不冒充真实抓取的数据。
"""
from __future__ import annotations

from src.jumia.api.errors import InvalidCategoryError
from src.jumia.category.attribute_schema import AttributeSchema
from src.jumia.category.category_tree import CategoryTree

_tree = CategoryTree()
_schema = AttributeSchema()


def get_categories(dry_run: bool = True) -> dict:
    """返回类目结构（dry-run：内置参考类目树；真实模式未实现）。"""
    if not dry_run:
        raise NotImplementedError("真实 Category API 尚未实现（P3-2-A 仅 dry-run 结构）。")
    return {
        "status": "dry_run",
        "source": "builtin_category_tree",
        "categories": [
            {"category_id": n.id, "name": n.name, "parent_id": n.parent_id}
            for n in _tree.list_categories()
        ],
    }


def get_attributes(category_id: str, dry_run: bool = True) -> dict:
    """返回类目属性结构（dry-run：内置属性 Schema）。无效类目抛 InvalidCategoryError。"""
    if not dry_run:
        raise NotImplementedError("真实 Attribute API 尚未实现（P3-2-A 仅 dry-run 结构）。")
    if _tree.get(category_id) is None:
        raise InvalidCategoryError(f"无效类目：{category_id}")
    return {
        "status": "dry_run",
        "source": "builtin_attribute_schema",
        "category_id": category_id,
        "required_attributes": _schema.required(category_id),
        "optional_attributes": _schema.optional(category_id),
    }
