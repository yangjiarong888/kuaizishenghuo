"""LoginPage：Mixin 组合，对外唯一页面对象。"""

from __future__ import annotations

from typing import Optional

from selenium.webdriver.support.ui import WebDriverWait

from commons.driver import DriverManager
from pages.login import constants as login_constants
from pages.login.data import LoginData
from pages.login.mixins import (
    LoginFindClickMixin,
    LoginNavigationPostLoginMixin,
    LoginOAuthMixin,
    LoginPasswordMixin,
    LoginSemanticsMixin,
    LoginSmsVoiceMixin,
    LoginStatePopupMixin,
)


class LoginPage(
    LoginSemanticsMixin,
    LoginFindClickMixin,
    LoginStatePopupMixin,
    LoginNavigationPostLoginMixin,
    LoginOAuthMixin,
    LoginSmsVoiceMixin,
    LoginPasswordMixin,
):
    """微信/QQ/谷歌、手机短信、账号密码、忘记密码等登录流程。"""

    LOGIN_HUB_LOCS = login_constants.LOGIN_HUB_LOCS
    _QQ_CLIENT_PACKAGES = login_constants.QQ_CLIENT_PACKAGES
    _QQ_OAUTH_BROWSER_PACKAGES = login_constants.QQ_OAUTH_BROWSER_PACKAGES
    _HOME_H5_TRAP_RES_ID_MARKERS = login_constants.HOME_H5_TRAP_RES_ID_MARKERS
    POST_LOGIN_VERIFY_WAIT_SEC: float = 5.0

    def __init__(self, session_name: str = "login_test", data: Optional[LoginData] = None):
        self.session_name = session_name
        self.driver = DriverManager().get_driver(session_name=session_name)
        try:
            self.driver.implicitly_wait(0)
        except Exception:
            pass
        self.wait = WebDriverWait(self.driver, 20)
        self.data = data or LoginData()
        self._suppress_click_gesture_until: float = 0.0
        self._phone_sms_login_active: bool = False
