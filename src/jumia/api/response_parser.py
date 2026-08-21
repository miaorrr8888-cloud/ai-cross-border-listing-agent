"""Jumia API 响应解析器：统一处理 success / error / http_status。

把 HTTP 状态码 + 原始响应体统一解析为 ``ParsedResponse``：
- 2xx → success=True，data 为 JSON 解析结果
- 4xx/5xx → success=False，error 为错误消息
- 非 JSON body → data=None，raw_body 保留原文

与 ``map_http_error()`` 配合：把状态码映射到业务异常类。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Optional

from src.jumia.api.errors import map_http_error


@dataclass
class ParsedResponse:
    """统一的 API 响应结构。"""

    success: bool
    http_status: int
    data: Optional[dict] = None
    error: Optional[str] = None
    raw_body: Optional[str] = None
    headers: dict = field(default_factory=dict)
    error_type: Optional[str] = None  # 对应的异常类名（如 AuthenticationError）

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "http_status": self.http_status,
            "data": self.data,
            "error": self.error,
            "raw_body": self.raw_body,
            "headers": dict(self.headers),
            "error_type": self.error_type,
        }


class ResponseParser:
    """Jumia API 响应解析器。"""

    @staticmethod
    def _decode_body(body) -> str:
        """把 body（bytes / str / None）统一解码为 str。"""
        if body is None:
            return ""
        if isinstance(body, bytes):
            return body.decode("utf-8", errors="replace")
        return str(body)

    @staticmethod
    def _try_parse_json(text: str) -> Optional[dict]:
        """尝试解析 JSON；失败返回 None（不抛异常）。"""
        if not text:
            return None
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
            # JSON 但不是 dict（list / str / number）
            return {"_raw": parsed}
        except (json.JSONDecodeError, ValueError):
            return None

    @staticmethod
    def _extract_error_message(text: str, data: Optional[dict]) -> str:
        """从响应体提取错误消息。"""
        if data:
            # 常见字段名：message / error / error_description / detail
            for key in ("message", "error", "error_description", "detail", "ErrorMessage"):
                val = data.get(key)
                if val:
                    return str(val)
        return text[:500] if text else "Unknown error"

    @classmethod
    def parse(cls, status_code: int, body=None, headers: Optional[dict] = None) -> ParsedResponse:
        """解析 HTTP 响应为 ``ParsedResponse``。

        - 2xx → success=True
        - 其他 → success=False，error_type 由 ``map_http_error()`` 决定
        """
        text = cls._decode_body(body)
        data = cls._try_parse_json(text)
        hdrs = dict(headers or {})
        is_success = 200 <= status_code < 300

        if is_success:
            return ParsedResponse(
                success=True,
                http_status=status_code,
                data=data,
                error=None,
                raw_body=text,
                headers=hdrs,
                error_type=None,
            )

        error_msg = cls._extract_error_message(text, data)
        exc_class = map_http_error(status_code)
        return ParsedResponse(
            success=False,
            http_status=status_code,
            data=data,
            error=error_msg,
            raw_body=text,
            headers=hdrs,
            error_type=exc_class.__name__,
        )

    @classmethod
    def parse_dry_run(cls, prepared_request: dict) -> ParsedResponse:
        """为 dry-run 模式构造预览响应（不发送 HTTP）。"""
        return ParsedResponse(
            success=False,
            http_status=0,
            data={"prepared_request": prepared_request},
            error="dry_run: request not sent",
            raw_body=None,
            headers={},
            error_type="DryRun",
        )
