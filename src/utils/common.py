"""通用工具：配置加载、JSON 读写。"""
from __future__ import annotations

import json
import os
from typing import Any, Dict


def load_config(path: str) -> Dict[str, Any]:
    """加载 YAML 配置；缺少 pyyaml 或文件不存在时返回空 dict（使用代码默认值）。"""
    if not os.path.exists(path):
        return {}
    try:
        import yaml
    except ImportError:
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_json(obj: Any, path: str) -> None:
    """将对象写入 JSON 文件（自动创建父目录，保留中文）。"""
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
