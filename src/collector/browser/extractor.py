"""浏览器采集的 HTML 解析基础设施（纯标准库，零第三方依赖）。

提供一个轻量 HtmlDoc 文档模型 + BaseExtractor 抽象 + ContentExtractor 编排器。
所有字段提取器都基于 HtmlDoc 查询，**识别不到就返回 None，绝不伪造值**。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from html.parser import HTMLParser
from typing import Any, Dict, Iterator, List, Optional


class _Node:
    __slots__ = ("name", "attrs", "text", "children")

    def __init__(self, name: str, attrs):
        self.name = name.lower()
        self.attrs = {k.lower(): v for k, v in dict(attrs).items()}
        self.text: List[str] = []
        self.children: List["_Node"] = []


class _DocParser(HTMLParser):
    """把 HTML 解析成轻量树 + meta 映射 + <title> 文本 + <base> 链接。"""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = _Node("#root", [])
        self._stack: List[_Node] = [self.root]
        self.meta: Dict[str, str] = {}
        self.base_href = ""
        self._title_parts: List[str] = []
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        node = _Node(tag, attrs)
        self._stack[-1].children.append(node)
        self._stack.append(node)

        low = tag.lower()
        d = node.attrs
        if low == "meta":
            key = d.get("property") or d.get("name") or d.get("itemprop")
            if key and d.get("content") is not None:
                self.meta[key.lower()] = d["content"]
        elif low == "base":
            if d.get("href"):
                self.base_href = d["href"]
        elif low == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        low = tag.lower()
        if low == "title":
            self._in_title = False
        # 弹栈：移除到最近的同名开标签
        if len(self._stack) > 1:
            for i in range(len(self._stack) - 1, 0, -1):
                if self._stack[i].name == low:
                    del self._stack[i:]
                    break

    def handle_data(self, data):
        if self._in_title:
            self._title_parts.append(data)
        if self._stack:
            self._stack[-1].text.append(data)


def _node_text(node: _Node) -> str:
    """递归拼接节点文本并压缩空白。"""
    parts = list(node.text)
    for c in node.children:
        parts.append(_node_text(c))
    return " ".join("".join(parts).split())


class HtmlDoc:
    """由 HTML 字符串构建的轻量文档模型：可遍历、可按属性查询。"""

    def __init__(self, html: str, base_url: str = ""):
        parser = _DocParser()
        parser.feed(html or "")
        self.html = html or ""
        self.meta = parser.meta
        self.title = "".join(parser._title_parts).strip()
        self.base_href = parser.base_href
        self.base_url = base_url
        self.root = parser.root

    def iter(self) -> Iterator[_Node]:
        stack = list(reversed(self.root.children))
        while stack:
            node = stack.pop()
            yield node
            stack.extend(reversed(node.children))

    def find(self, name: Optional[str] = None, **attr_substrings) -> Optional[_Node]:
        for n in self.iter():
            if name is not None and n.name != name.lower():
                continue
            if self._match_attrs(n, attr_substrings):
                return n
        return None

    def find_all(self, name: Optional[str] = None, **attr_substrings) -> List[_Node]:
        out: List[_Node] = []
        for n in self.iter():
            if name is not None and n.name != name.lower():
                continue
            if self._match_attrs(n, attr_substrings):
                out.append(n)
        return out

    @staticmethod
    def _match_attrs(node: _Node, filters: Dict[str, str]) -> bool:
        for k, v in filters.items():
            val = node.attrs.get(k.lower(), "")
            if v.lower() not in val.lower():
                return False
        return True

    def by_itemprop(self, prop: str) -> Optional[_Node]:
        return self.find(itemprop=prop)

    def all_imgs(self) -> List[_Node]:
        return self.find_all("img")

    def text_of(self, node: Optional[_Node]) -> str:
        return _node_text(node) if node else ""


class BaseExtractor(ABC):
    """字段提取器基类：识别不到返回 None，绝不造假。"""

    @abstractmethod
    def extract(self, doc: HtmlDoc, base_url: str = "") -> Any:
        ...


class ContentExtractor:
    """编排五个字段提取器，输出结构化 dict（识别不到的字段为 None）。"""

    def __init__(self):
        from src.collector.browser.extractors import (
            AttributeExtractor,
            ImageExtractor,
            PriceExtractor,
            TitleExtractor,
            VariantExtractor,
        )

        self.extractors = {
            "title": TitleExtractor(),
            "price": PriceExtractor(),
            "images": ImageExtractor(),
            "variants": VariantExtractor(),
            "attributes": AttributeExtractor(),
        }

    def extract_all(self, doc: HtmlDoc, base_url: str = "") -> Dict[str, Any]:
        return {name: ex.extract(doc, base_url) for name, ex in self.extractors.items()}
