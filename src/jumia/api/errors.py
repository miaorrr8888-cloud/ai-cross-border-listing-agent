"""Jumia API 错误定义与错误映射。

- 每个错误都是 ``JumiaAPIError`` 的子类，便于上层统一捕获。
- ``map_http_error(status_code)`` 把 HTTP 状态码映射到对应异常（供未来真实请求使用）。
"""
from __future__ import annotations


class JumiaAPIError(Exception):
    """Jumia API 基础异常。"""


class AuthenticationError(JumiaAPIError):
    """认证失败（token 缺失/无效/过期等）。"""


class PermissionError(JumiaAPIError):  # noqa: A001 —— 业务语义的权限不足异常
    """权限不足（无法访问对应资源）。"""


class RateLimitError(JumiaAPIError):
    """请求被限流（触发 Jumia 频率限制）。"""


class InvalidCategoryError(JumiaAPIError):
    """无效类目（category_id 不存在或不可用）。"""


class UploadDisabledError(JumiaAPIError):
    """上传已被禁用（upload.enabled=false）。"""


class UploadLimitExceededError(JumiaAPIError):
    """上传数量超过限制（upload.max_products）。"""


def map_http_error(status_code: int) -> type:
    """把 HTTP 状态码映射到异常类。未知状态码回退到 JumiaAPIError。"""
    mapping = {
        401: AuthenticationError,
        403: PermissionError,
        429: RateLimitError,
    }
    return mapping.get(status_code, JumiaAPIError)
