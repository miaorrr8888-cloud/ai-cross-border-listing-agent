"""商品字段提取器集合（标题 / 价格 / 图片 / 变体 / 属性）。"""
from src.collector.browser.extractors.attributes import AttributeExtractor
from src.collector.browser.extractors.images import ImageExtractor
from src.collector.browser.extractors.price import PriceExtractor
from src.collector.browser.extractors.title import TitleExtractor
from src.collector.browser.extractors.variants import VariantExtractor

__all__ = [
    "TitleExtractor",
    "PriceExtractor",
    "ImageExtractor",
    "VariantExtractor",
    "AttributeExtractor",
]
