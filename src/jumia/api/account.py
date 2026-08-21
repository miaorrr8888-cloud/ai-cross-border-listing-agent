"""Jumia Account 查询骨架（P3-2-A：dry-run，不假装真实店铺信息）。"""
from __future__ import annotations


def get_shop_info(dry_run: bool = True) -> dict:
    """返回店铺信息结构（dry-run：结构定义，字段为 None，不含真实数据）。"""
    if not dry_run:
        raise NotImplementedError("真实 Account API 尚未实现（P3-2-A 仅 dry-run 骨架）。")
    return {
        "status": "dry_run",
        "shop": {
            "shop_id": None,
            "shop_name": None,
            "country": None,
            "currency": None,
        },
        "message": "dry-run 模式：仅返回结构定义，不包含真实店铺信息。",
    }
