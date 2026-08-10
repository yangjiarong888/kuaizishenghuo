from types import SimpleNamespace

import pytest

import pages.shipping_page as shipping_page_module

from pages.shipping_page import ShippingPage


class FakeElement:
    def __init__(self, driver, text="", on_click=None):
        self.driver = driver
        self.text = text
        self.on_click = on_click

    def is_displayed(self):
        return True

    def is_enabled(self):
        return True

    def click(self):
        self.driver.clicks.append(self.text)
        if self.on_click:
            self.on_click()


class FakeShippingDriver:
    def __init__(self):
        self.screen = "app_home"
        self.clicks = []
        self.page_source = "筷子生活 首页 国际货运"
        self.current_activity = "com.bs.feifubao.MainActivity"
        self.entry_action = self._show_shipping_home
        self.delivery_action = self._show_delivery_orders
        self.home_action = self._show_shipping_home
        self.entry_available = True
        self.delivery_available = True
        self.home_available = True

    @staticmethod
    def _text_selector(label):
        return f'//*[@text="{label}" or @content-desc="{label}"]'

    def find_elements(self, by, value):
        if (
            self.screen == "app_home"
            and self.entry_available
            and value == self._text_selector("国际货运")
        ):
            return [FakeElement(self, "国际货运", self.entry_action)]
        if (
            self.screen == "shipping_home"
            and self.delivery_available
            and value == self._text_selector("配送订单")
        ):
            return [FakeElement(self, "配送订单", self.delivery_action)]
        if self.screen == "delivery_orders" and self.home_available and value in {
            self._text_selector("国际货运"),
            self._text_selector("首页"),
        }:
            return [FakeElement(self, "首页", self.home_action)]
        return []

    def _show_shipping_home(self):
        self.screen = "shipping_home"
        self.page_source = "国际货运 寄件菲律宾 寄件全球 配送订单"

    def _show_delivery_orders(self):
        self.screen = "delivery_orders"
        self.page_source = "配送订单 全部 待付款 待收货 已完成 已取消"


def _record_capture(monkeypatch):
    calls = []

    def capture(driver, stage, artifacts_dir, include_screenshot=True):
        calls.append((driver, stage, artifacts_dir, include_screenshot))
        return SimpleNamespace(
            screenshot=f"artifacts/{stage}.png" if include_screenshot else None,
            page_source=f"artifacts/{stage}.xml",
        )

    monkeypatch.setattr(shipping_page_module, "capture_failure", capture)
    return calls


def test_enter_from_app_home_clicks_international_shipping():
    driver = FakeShippingDriver()

    assert ShippingPage(driver).enter_from_app_home() is True
    assert driver.clicks == ["国际货运"]
    assert driver.screen == "shipping_home"


def test_shipping_tabs_switch_both_directions():
    driver = FakeShippingDriver()
    driver._show_shipping_home()
    page = ShippingPage(driver)

    assert page.switch_to_delivery_orders() is True
    assert driver.screen == "delivery_orders"
    assert page.switch_to_shipping_home() is True
    assert driver.screen == "shipping_home"


def test_navigation_failures_capture_non_sensitive_diagnostics(monkeypatch):
    monkeypatch.setattr(shipping_page_module.AppConfig, "WAIT_TIMEOUT", 0)
    calls = _record_capture(monkeypatch)
    driver = FakeShippingDriver()
    page = ShippingPage(driver)

    driver._show_shipping_home()
    driver.delivery_available = False
    assert page.switch_to_delivery_orders() is False
    driver.delivery_available = True
    driver.delivery_action = None
    assert page.switch_to_delivery_orders() is False

    driver._show_delivery_orders()
    driver.home_available = False
    assert page.switch_to_shipping_home() is False
    driver.home_available = True
    driver.home_action = None
    assert page.switch_to_shipping_home() is False

    assert [stage for _, stage, _, _ in calls] == [
        "shipping_delivery_tab_missing",
        "shipping_delivery_tab_timeout",
        "shipping_home_tab_missing",
        "shipping_home_tab_timeout",
    ]
    assert all(include_screenshot for *_, include_screenshot in calls)


def test_home_entry_click_exception_and_timeout_capture_failure(monkeypatch):
    monkeypatch.setattr(shipping_page_module.AppConfig, "WAIT_TIMEOUT", 0)
    calls = _record_capture(monkeypatch)
    driver = FakeShippingDriver()
    page = ShippingPage(driver)

    def raise_click_error():
        raise RuntimeError("password=do-not-log")

    driver.entry_action = raise_click_error
    assert page.enter_from_app_home() is False
    driver.entry_action = None
    assert page.enter_from_app_home() is False

    assert [stage for _, stage, _, _ in calls] == [
        "shipping_entry_click_failed",
        "shipping_entry_timeout",
    ]
    assert all(include_screenshot for *_, include_screenshot in calls)


@pytest.mark.parametrize(
    ("stage", "secret", "expected_stage"),
    [
        (
            "Payment Password=sup3rSecret/Retry",
            "sup3rSecret",
            "payment_password_redacted_retry",
        ),
        ("Login Token superToken/Retry", "superToken", "login_token_redacted_retry"),
        ("Order Secret: extraSecret/Retry", "extraSecret", "order_secret_redacted_retry"),
        (
            "Checkout Pay_Password=123456/Retry",
            "123456",
            "checkout_pay_password_redacted_retry",
        ),
        (
            "Refresh Access_Token:abc/Retry",
            "abc",
            "refresh_access_token_redacted_retry",
        ),
    ],
)
def test_capture_shipping_failure_redacts_stage_secrets_and_hides_sensitive_screenshots(
    monkeypatch, stage, secret, expected_stage
):
    calls = _record_capture(monkeypatch)
    logged = []
    monkeypatch.setattr(shipping_page_module.logger, "error", lambda *args: logged.append(args))
    driver = FakeShippingDriver()

    ShippingPage(driver).capture_shipping_failure(stage, sensitive=True)

    assert calls[0][0] is driver
    assert calls[0][1] == expected_stage
    assert calls[0][3] is False
    assert secret not in calls[0][1]
    assert secret not in repr(logged[0][2:])
