"""登录用数据模型与类型别名。"""

from dataclasses import dataclass
from typing import Optional, Tuple

Locator = Tuple[str, str]  # (by, value)


@dataclass
class LoginData:
    phone: str = "19860207026"
    password: str = "qqqyyyaaa"
    customer_service_text: str = "你好，我需要语音验证码"
    new_password: str = "qqqyyyaaa"
    verification_code: Optional[str] = None
