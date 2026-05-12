"""兼容旧路径：`from pages.login_page import LoginPage, LoginData`。
python login.page.py --method password/phone/wechat/qq
"""
from pages.login import LoginData, Locator, LoginPage

__all__ = ["LoginPage", "LoginData", "Locator"]
