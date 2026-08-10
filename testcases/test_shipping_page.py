from types import SimpleNamespace

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
        self.page_source = "绛峰瓙鐢熸椿 棣栭〉 鍥介檯璐ц繍"
        self.current_activity = "com.bs.feifubao.MainActivity"

    def find_elements(self, by, value):
        if self.screen == "app_home" and "鍥介檯璐ц繍" in value:
            return [FakeElement(self, "鍥介檯璐ц繍", self._show_shipping_home)]
        if self.screen == "shipping_home" and "閰嶉€佽鍗�" in value:
            return [FakeElement(self, "閰嶉€佽鍗�", self._show_delivery_orders)]
        if self.screen == "delivery_orders" and (
            "鍥介檯璐ц繍" in value or "棣栭〉" in value
        ):
            return [FakeElement(self, "棣栭〉", self._show_shipping_home)]
        return []

    def _show_shipping_home(self):
        self.screen = "shipping_home"
        self.page_source = "鍥介檯璐ц繍 瀵勪欢鑿插緥瀹� 瀵勪欢鍏ㄧ悆 閰嶉€佽鍗�"

    def _show_delivery_orders(self):
        self.screen = "delivery_orders"
        self.page_source = "閰嶉€佽鍗� 鍏ㄩ儴 寰呬粯娆� 寰呮敹璐� 宸插畬鎴� 宸插彇娑�"


def test_enter_from_app_home_clicks_international_shipping():
    driver = FakeShippingDriver()

    assert ShippingPage(driver).enter_from_app_home() is True
    assert driver.clicks == ["鍥介檯璐ц繍"]
    assert driver.screen == "shipping_home"


def test_shipping_tabs_switch_both_directions():
    driver = FakeShippingDriver()
    driver._show_shipping_home()
    page = ShippingPage(driver)

    assert page.switch_to_delivery_orders() is True
    assert driver.screen == "delivery_orders"
    assert page.switch_to_shipping_home() is True
    assert driver.screen == "shipping_home"


def test_capture_shipping_failure_sanitizes_diagnostic_stage(monkeypatch):
    captured = {}

    def capture(driver, stage, artifacts_dir):
        captured.update(driver=driver, stage=stage, artifacts_dir=artifacts_dir)
        return SimpleNamespace(screenshot="screen.png", page_source="page.xml")

    monkeypatch.setattr(shipping_page_module, "capture_failure", capture, raising=False)
    driver = FakeShippingDriver()

    ShippingPage(driver).capture_shipping_failure("Login Token=SECRET/Retry")

    assert captured["driver"] is driver
    assert captured["stage"] == "login_token_secret_retry"
