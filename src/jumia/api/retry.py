"""Jumia API 重试机制：对 429 / 500 / 502 / 503 实行指数退避。

策略：
- 429 Rate Limit：退避后重试
- 500 / 502 / 503 服务器错误：退避后重试
- 其他状态码：不重试，直接返回
- 退避公式：``base_delay * (2 ** attempt)``，加 jitter，上限 ``max_delay``
- 测试中可注入 ``sleep_func`` 避免真实等待
"""
from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Set

# 可重试的 HTTP 状态码
RETRYABLE_STATUS_CODES: Set[int] = {429, 500, 502, 503}

# 默认退避参数
DEFAULT_BASE_DELAY: float = 1.0
DEFAULT_MAX_DELAY: float = 30.0
DEFAULT_JITTER: float = 0.1
DEFAULT_MAX_RETRIES: int = 3


@dataclass
class RetryConfig:
    """重试配置。"""

    max_retries: int = DEFAULT_MAX_RETRIES
    base_delay: float = DEFAULT_BASE_DELAY
    max_delay: float = DEFAULT_MAX_DELAY
    jitter: float = DEFAULT_JITTER


@dataclass
class RetryAttempt:
    """单次请求 / 重试记录。"""

    attempt: int           # 第几次请求（0 = 首次）
    status_code: int       # 本次 HTTP 状态码
    delay: float = 0.0     # 本次退避秒数（0 = 未退避）
    will_retry: bool = False  # 是否会继续重试


@dataclass
class RetryResult:
    """重试执行结果。"""

    final_status_code: int
    final_body: Optional[bytes]
    final_headers: dict
    attempts: List[RetryAttempt] = field(default_factory=list)

    @property
    def total_retries(self) -> int:
        return len(self.attempts) - 1 if self.attempts else 0

    def to_dict(self) -> dict:
        return {
            "final_status_code": self.final_status_code,
            "total_retries": self.total_retries,
            "attempts": [
                {
                    "attempt": a.attempt,
                    "status_code": a.status_code,
                    "delay": round(a.delay, 3),
                    "will_retry": a.will_retry,
                }
                for a in self.attempts
            ],
        }


class RetryHandler:
    """重试处理器：对可重试状态码执行指数退避。

    ``send_func`` 签名：``() -> (status_code, body, headers)``
    """

    def __init__(
        self,
        config: Optional[RetryConfig] = None,
        sleep_func: Optional[Callable[[float], None]] = None,
    ):
        self.config = config or RetryConfig()
        self._sleep = sleep_func or time.sleep

    def should_retry(self, status_code: int, attempt: int) -> bool:
        """判断是否应该重试：状态码可重试且未超过最大重试次数。"""
        return (
            status_code in RETRYABLE_STATUS_CODES
            and attempt < self.config.max_retries
        )

    def compute_delay(self, attempt: int) -> float:
        """计算指数退避延迟：``base * 2^attempt``，加 jitter，上限 max_delay。"""
        delay = self.config.base_delay * (2 ** attempt)
        delay = min(delay, self.config.max_delay)
        if self.config.jitter > 0:
            jitter_amount = delay * self.config.jitter
            delay += random.uniform(-jitter_amount, jitter_amount)
        return max(0.0, delay)

    def execute_with_retry(
        self,
        send_func: Callable[[], tuple],
    ) -> RetryResult:
        """执行 ``send_func``，对可重试状态码自动退避重试。

        ``send_func`` 返回 ``(status_code, body, headers)``。
        """
        attempts: List[RetryAttempt] = []
        status_code = 0
        body: Optional[bytes] = None
        headers: dict = {}

        for attempt in range(self.config.max_retries + 1):
            status_code, body, headers = send_func()
            will_retry = self.should_retry(status_code, attempt)
            delay = 0.0
            if will_retry:
                delay = self.compute_delay(attempt)
                self._sleep(delay)
            attempts.append(RetryAttempt(
                attempt=attempt,
                status_code=status_code,
                delay=delay,
                will_retry=will_retry,
            ))
            if not will_retry:
                break

        return RetryResult(
            final_status_code=status_code,
            final_body=body,
            final_headers=headers,
            attempts=attempts,
        )
