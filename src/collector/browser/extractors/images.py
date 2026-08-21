"""商品图片提取。识别不到返回 None，绝不伪造。"""
from __future__ import annotations

from typing import List, Optional
from urllib.parse import urljoin

from src.collector.browser.extractor import BaseExtractor, HtmlDoc

# 明显非商品图（图标/logo/占位图/头像等）
_NOISE_MARKERS = ("icon", "logo", "sprite", "avatar", "spacer", "loading.gif", "blank.gif", "pixel")


class ImageExtractor(BaseExtractor):
    """收集商品图：og:image + 所有 <img src>（含 srcset 首候选），过滤噪声、解析相对路径。"""

    def extract(self, doc: HtmlDoc, base_url: str = "") -> Optional[List[str]]:
        raw: List[str] = []
        og = doc.meta.get("og:image")
        if og:
            raw.append(og)

        for img in doc.all_imgs():
            src = img.attrs.get("src") or ""
            if not src:
                srcset = img.attrs.get("srcset") or ""
                if srcset:
                    src = srcset.split(",")[0].strip().split(" ")[0]
            if src:
                raw.append(src)

        seen = set()
        out: List[str] = []
        for u in raw:
            u = u.strip()
            if not u or u.lower().startswith("data:"):
                continue
            if any(m in u.lower() for m in _NOISE_MARKERS):
                continue
            resolved = urljoin(base_url, u) if base_url else u
            if resolved in seen:
                continue
            seen.add(resolved)
            out.append(resolved)

        return out or None
