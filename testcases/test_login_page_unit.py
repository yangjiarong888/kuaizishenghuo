import pytest

import pages.login.login_page as login_page_module
from pages.login.data import LoginData


pytestmark = pytest.mark.unit


class FakeDriver:
    def __init__(self):
        self.waits = []

    def implicitly_wait(self, value):
        self.waits.append(value)


def test_login_page_accepts_injected_driver_without_driver_manager(monkeypatch):
    fake = FakeDriver()

    def unexpected_get_driver(*args, **kwargs):
        raise AssertionError("DriverManager must not run for an injected driver")

    monkeypatch.setattr(
        login_page_module.DriverManager,
        "get_driver",
        unexpected_get_driver,
    )

    page = login_page_module.LoginPage(driver=fake)

    assert page.driver is fake
    assert page.wait._driver is fake
    assert fake.waits == [0]
    assert isinstance(page.data, LoginData)
