"""Jumia 类目树：加载类目结构、查询类目、返回 category_id。

内置类目树是参考结构（可被真实 Jumia CategoryTree API 替换），不是假 API 数据。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class CategoryNode:
    id: str
    name: str
    parent_id: str = ""
    children: List["CategoryNode"] = field(default_factory=list)


# 内置类目树（parent_id 建立父子关系；根类目 parent_id 为空）
BUILTIN_CATEGORY_TREE: List[dict] = [
    {"id": "electronics", "name": "Electronics", "parent_id": ""},
    {"id": "electronics_audio", "name": "Audio & Headphones", "parent_id": "electronics"},
    {"id": "electronics_phones", "name": "Phones & Tablets", "parent_id": "electronics"},
    {"id": "fashion", "name": "Fashion", "parent_id": ""},
    {"id": "fashion_women", "name": "Women's Clothing", "parent_id": "fashion"},
    {"id": "fashion_shoes", "name": "Shoes", "parent_id": "fashion"},
    {"id": "home_kitchen", "name": "Home & Kitchen", "parent_id": ""},
    {"id": "home_fans", "name": "Fans & Cooling", "parent_id": "home_kitchen"},
    {"id": "beauty", "name": "Beauty", "parent_id": ""},
    {"id": "beauty_fragrance", "name": "Fragrance", "parent_id": "beauty"},
    {"id": "baby_products", "name": "Baby Products", "parent_id": ""},
    {"id": "general_merchandise", "name": "General Merchandise", "parent_id": ""},
]


class CategoryTree:
    """类目树：支持按 ID / 名称查询、子类目遍历、category_id 反查。"""

    def __init__(self, data: Optional[List[dict]] = None):
        data = data if data is not None else BUILTIN_CATEGORY_TREE
        self._nodes: Dict[str, CategoryNode] = {}
        for item in data:
            self._nodes[item["id"]] = CategoryNode(
                id=item["id"],
                name=item["name"],
                parent_id=item.get("parent_id", ""),
            )
        for node in self._nodes.values():
            if node.parent_id and node.parent_id in self._nodes:
                self._nodes[node.parent_id].children.append(node)

    def get(self, category_id: str) -> Optional[CategoryNode]:
        """按 ID 查询类目。"""
        return self._nodes.get(category_id)

    def get_by_name(self, name: str) -> Optional[CategoryNode]:
        """按名称查询类目（大小写不敏感）。"""
        target = (name or "").lower()
        for node in self._nodes.values():
            if node.name.lower() == target:
                return node
        return None

    def get_category_id(self, name: str) -> Optional[str]:
        """返回类目名称对应的 category_id。"""
        node = self.get_by_name(name)
        return node.id if node else None

    def children(self, category_id: str) -> List[CategoryNode]:
        node = self.get(category_id)
        return list(node.children) if node else []

    def list_categories(self) -> List[CategoryNode]:
        return list(self._nodes.values())

    def root_ids(self) -> List[str]:
        return [n.id for n in self._nodes.values() if not n.parent_id]
