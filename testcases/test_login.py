"""
使用 pytest 的登录相关用例（App 无邮箱登录，已移除邮箱/注册占位用例）。
"""
import allure
import pytest

from commons.driver import DriverManager
from pages.login_page import LoginPage


pytestmark = pytest.mark.device


@allure.feature("登录功能测试")
class TestLogin:
    @pytest.fixture(autouse=True)
    def setup(self):
        """测试前准备"""
        self.login_page = LoginPage(session_name="login_test")
        yield
        DriverManager().close_driver("login_test")

    @allure.story("忘记密码测试")
    def test_forget_password(self):
        """测试忘记密码功能"""
        with allure.step("1. 点击忘记密码"):
            result = self.login_page.forget_password()

        with allure.step("2. 验证跳转到忘记密码页面"):
            assert result, "忘记密码流程未返回成功"
