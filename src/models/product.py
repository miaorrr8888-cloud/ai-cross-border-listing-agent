"""统一商品模型 (Unified Product Schema)。

设计目标：
- 输入通用：不限制来源平台（1688 / 淘宝 / Amazon / 独立站 … 都可作为 source_platform）。
- 字段覆盖：基础信息、价格、Jumia 字段、多语言版本。
- 零外部依赖：使用标准库 dataclasses，方便新手阅读与扩展。

未来接入 Jumia API 时，本模型可直接作为请求体的数据来源。
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List


class Language(str, Enum):
    """支持的目标语言。"""

    ZH_CN = "zh-CN"
    EN = "en"
    FR = "fr"
    AR = "ar"

    @classmethod
    def values(cls) -> List[str]:
        return [lang.value for lang in cls]


@dataclass
class Product:
    # ---------- 基础信息 ----------
    source_url: str = ""            # 原始商品链接（任意平台）
    source_platform: str = "generic"  # 1688 / taobao / amazon / shopify / generic ...
    title_cn: str = ""             # 中文标题（如有）
    title_en: str = ""             # 英文标题（AI 优化后填充）
    description: str = ""          # 原始描述
    images: List[str] = field(default_factory=list)   # 图片 URL 列表
    sku: str = ""                  # 库存单位
    brand: str = ""                # 品牌
    attributes: Dict[str, Any] = field(default_factory=dict)  # 规格属性（颜色/尺寸…）

    # ---------- 采集层补充（P2-1 浏览器采集）----------
    price: float = 0.0             # 页面采集到的售价（区别于成本价）
    price_currency: str = ""       # 售价货币（如 CNY / USD）
    variants: Dict[str, Any] = field(default_factory=dict)  # 变体（颜色/尺寸/SKU）

    # ---------- 价格 ----------
    cost_price: float = 0.0        # 成本价
    currency: str = "USD"          # 货币（USD / CNY / EUR ...）

    # ---------- Jumia 类目智能（P2-2）----------
    category_id: str = ""          # Jumia 类目树中的类目 ID
    category_name: str = ""        # Jumia 类目名（规范名）
    category_confidence: float = 0.0  # 类目匹配置信度（0~1）
    required_attributes: List[str] = field(default_factory=list)  # 类目必填属性键
    missing_attributes: List[str] = field(default_factory=list)   # 缺失的必填属性键

    # ---------- Jumia 字段 ----------
    category: str = ""             # 建议类目（历史字段，与 category_name 对齐）
    product_name: str = ""         # Jumia 商品名（标题）
    short_description: str = ""    # 短描述
    long_description: str = ""     # 长描述
    keywords: List[str] = field(default_factory=list)  # 搜索关键词
    language_versions: Dict[str, Dict[str, str]] = field(default_factory=dict)  # {lang: {title, description}}

    def to_dict(self) -> Dict[str, Any]:
        """序列化为普通 dict（便于写入 JSON）。"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Product":
        """从 dict 构造，忽略模型未知字段，保证健壮性。"""
        known = set(cls.__dataclass_fields__.keys())
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)
