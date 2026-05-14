"""登录用数据模型与类型别名。"""

import os
from dataclasses import dataclass, field
from typing import Optional, Tuple

Locator = Tuple[str, str]  # (by, value)


def _env_strip(key: str) -> Optional[str]:
    v = os.environ.get(key)
    if v is None:
        return None
    s = v.strip()
    return s or None


def default_login_phone() -> str:
    """优先环境变量 LOGIN_DEFAULT_PHONE；不在仓库内落盘真实账号。"""
    return _env_strip("LOGIN_DEFAULT_PHONE") or ""


def default_login_password() -> str:
    """优先环境变量 LOGIN_DEFAULT_PASSWORD。"""
    return _env_strip("LOGIN_DEFAULT_PASSWORD") or ""


def default_new_password() -> str:
    """忘记密码流程新密码；可用 LOGIN_DEFAULT_NEW_PASSWORD 覆盖。"""
    return _env_strip("LOGIN_DEFAULT_NEW_PASSWORD") or ""


@dataclass
class LoginData:
    phone: str = field(default_factory=default_login_phone)
    password: str = field(default_factory=default_login_password)
    customer_service_text: str = "你好，我需要语音验证码"
    new_password: str = field(default_factory=default_new_password)
    verification_code: Optional[str] = None

    def resolved_phone(self, override: Optional[str] = None) -> str:
        return (override if override is not None else self.phone or "").strip()

    def resolved_password(self, override: Optional[str] = None) -> str:
        return override if override is not None else (self.password or "")

    def resolved_new_password(self) -> str:
        return self.new_password or ""
