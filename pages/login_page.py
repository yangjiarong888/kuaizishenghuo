"""兼容旧路径：`from pages.login_page import LoginPage, LoginData`。
python scripts/run_login.py --method password/phone/wechat/qq
"""
from pages.login.data import Locator, LoginData
from pages.login.login_page import LoginPage

__all__ = ["LoginPage", "LoginData", "Locator"]
