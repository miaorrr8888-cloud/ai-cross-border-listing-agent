"""Jumia API 健康检查（P3-2-A：不联网、不真实上传）。

产出 ``JumiaHealthReport``：auth_status / api_status / category_status / upload_enabled。
本阶段 upload_enabled 恒为 False（禁止真实商品上传）。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

from src.jumia.api.auth import JumiaAuth, MissingCredential


@dataclass
class JumiaHealthReport:
    auth_status: str = "unknown"       # ok / missing_credential / error
    api_status: str = "unknown"        # dry_run / disabled / error
    category_status: str = "unknown"   # dry_run / ok / error
    upload_enabled: bool = False       # 是否允许真实上传（P3-2-A 恒为 False）
    message: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def check_health(
    auth: Optional[JumiaAuth] = None,
    dry_run: bool = True,
    config: Optional[dict] = None,
) -> JumiaHealthReport:
    """执行健康检查：仅校验凭据存在性，不联网、不发送商品请求。

    - auth：显式传入优先；否则从 config 读取；再否则用空 JumiaAuth。
    - dry_run：本阶段 API 连接均为 dry-run（不发起真实请求）。
    """
    auth = auth if auth is not None else JumiaAuth.from_config(config or {})

    report = JumiaHealthReport()

    # 1) 认证健康检查
    try:
        auth.check_auth()  # 无 token 抛 MissingCredential
        report.auth_status = "ok"
    except MissingCredential as e:
        report.auth_status = "missing_credential"
        report.message = str(e)

    # 2) API 连接状态：dry-run 下不建立真实连接
    report.api_status = "dry_run" if dry_run else "disabled"

    # 3) 类目状态：dry-run 用内置参考类目树
    report.category_status = "dry_run"

    # 4) 上传开关：P3-2-A 禁止真实上传
    report.upload_enabled = False

    return report
