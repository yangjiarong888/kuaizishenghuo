import re
from types import SimpleNamespace

import pytest

import pages.shipping_address_mixin as shipping_address_mixin_module
import pages.shipping_page as shipping_page_module

from pages.shipping_page import ShippingPage
from pages.shipping_types import AddressData, AddressPolicy


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


class FakeAddressElement(FakeElement):
    def __init__(self, driver, text="", on_click=None, content_desc=""):
        super().__init__(driver, text, on_click)
        self.content_desc = content_desc

    def get_attribute(self, name):
        if name == "text":
            return self.text
        if name == "content-desc":
            return self.content_desc
        return ""


class FakeAddressField(FakeAddressElement):
    def __init__(self, driver, field):
        super().__init__(driver, field)
        self.field = field

    def clear(self):
        self.driver.address_form_values[self.field] = ""

    def send_keys(self, value):
        self.driver.address_form_values[self.field] = value


class FakeAddressShippingDriver(FakeShippingDriver):
    """A small address-book model that exposes only public UI interactions."""

    FIELD_LABELS = {
        "name": "联系人",
        "phone": "手机号码",
        "detail": "详细地址",
        "postcode": "邮政编码",
    }

    def __init__(self, address_book=()):
        super().__init__()
        self.screen = "checkout"
        self.address_book = list(address_book)
        self.selected_address = ""
        self.address_form_values = {}
        self.page_source = "提交订单 请选择收货地址"

    @classmethod
    def with_address_book(cls, address_book):
        return cls(address_book)

    def _show_address_book(self):
        self.screen = "address_book"
        self.page_source = "选择收货地址 新增地址 " + " ".join(self.address_book)

    def _show_address_form(self):
        self.screen = "address_form"
        self.page_source = "新增地址 联系人 手机号码 国家 城市 详细地址 邮政编码 保存"

    def _select_address(self, address):
        self.selected_address = address
        self.screen = "checkout"
        self.page_source = "提交订单 收货地址 " + address

    def _save_address(self):
        values = self.address_form_values
        address = "{name} {phone} {city} {detail}".format(
            name=values.get("name", ""),
            phone=values.get("phone", ""),
            city=values.get("city", ""),
            detail=values.get("detail", ""),
        ).strip()
        self.address_book.append(address)
        self._show_address_book()

    def find_elements(self, by, value):
        exact_labels = {
            self._text_selector("请选择收货地址"): FakeAddressElement(
                self, "请选择收货地址", self._show_address_book
            ),
            self._text_selector("收货地址"): FakeAddressElement(
                self, "收货地址", self._show_address_book
            ),
            self._text_selector("配送地址"): FakeAddressElement(
                self, "配送地址", self._show_address_book
            ),
            self._text_selector("新增地址"): FakeAddressElement(
                self, "新增地址", self._show_address_form
            ),
            self._text_selector("添加地址"): FakeAddressElement(
                self, "添加地址", self._show_address_form
            ),
            self._text_selector("保存"): FakeAddressElement(self, "保存", self._save_address),
            self._text_selector("菲律宾"): FakeAddressElement(self, "菲律宾"),
            self._text_selector("Manila"): FakeAddressElement(self, "Manila"),
        }
        if value in exact_labels:
            element = exact_labels[value]
            if self.screen == "checkout" and element.text in {"请选择收货地址", "收货地址", "配送地址"}:
                return [element]
            if self.screen == "address_book" and element.text in {"新增地址", "添加地址"}:
                return [element]
            if self.screen == "address_form" and element.text in {"保存", "菲律宾", "Manila"}:
                return [element]
            return []
        if self.screen == "address_book" and "contains(@text" in value:
            requested = re.findall(r'contains\(@(?:text|content-desc),"([^"]+)"\)', value)
            return [
                FakeAddressElement(self, address, lambda a=address: self._select_address(a))
                for address in self.address_book
                if any(match in address for match in requested)
            ]
        if self.screen == "address_form":
            for field, label in self.FIELD_LABELS.items():
                if label in value:
                    return [FakeAddressField(self, field)]
        return super().find_elements(by, value)


def complete_address(**overrides):
    values = {
        "match": "0994",
        "name": "Tester",
        "phone": "+639621170994",
        "country": "菲律宾",
        "city": "Manila",
        "detail": "100 Test Street",
        "postcode": "1000",
    }
    values.update(overrides)
    return AddressData(**values)


def test_existing_policy_requires_match_before_clicking():
    driver = FakeAddressShippingDriver()
    page = ShippingPage(driver)

    with pytest.raises(ValueError, match="SHIPPING_ADDRESS_MATCH"):
        page.ensure_shipping_address(AddressPolicy.EXISTING, AddressData())

    assert driver.clicks == []


def test_add_policy_requires_complete_fields_before_clicking():
    driver = FakeAddressShippingDriver()
    page = ShippingPage(driver)

    with pytest.raises(ValueError, match="phone,country,city,detail,postcode"):
        page.ensure_shipping_address(AddressPolicy.ADD, AddressData(name="Tester"))

    assert driver.clicks == []


def test_auto_selects_matching_existing_address_without_adding():
    driver = FakeAddressShippingDriver.with_address_book(["Tester +63******0994 Manila"])
    page = ShippingPage(driver)

    assert page.ensure_shipping_address(AddressPolicy.AUTO, complete_address()) is True
    assert "新增地址" not in driver.clicks
    assert driver.selected_address == "Tester +63******0994 Manila"


def test_auto_adds_when_matching_address_is_absent():
    driver = FakeAddressShippingDriver.with_address_book(["Other +63******0000 Cebu"])
    page = ShippingPage(driver)
    data = complete_address()

    assert page.ensure_shipping_address(AddressPolicy.AUTO, data) is True
    assert "新增地址" in driver.clicks
    assert driver.address_form_values["phone"] == "+639621170994"


def test_address_form_failures_capture_sensitive_diagnostics(monkeypatch):
    driver = FakeAddressShippingDriver()
    page = ShippingPage(driver)
    calls = []
    monkeypatch.setattr(
        page, "capture_shipping_failure", lambda stage, sensitive=False: calls.append((stage, sensitive))
    )

    with pytest.raises(AssertionError, match="未找到国家"):
        page.ensure_shipping_address(
            AddressPolicy.ADD, complete_address(country="不存在的国家")
        )

    assert calls == [("shipping_address_country_missing", True)]


def test_applied_address_logs_a_masked_phone_without_detail(monkeypatch):
    driver = FakeAddressShippingDriver.with_address_book(["Tester +63******0994 Manila"])
    messages = []
    monkeypatch.setattr(shipping_address_mixin_module.logger, "info", lambda *args: messages.append(args))

    assert ShippingPage(driver).ensure_shipping_address(AddressPolicy.AUTO, complete_address()) is True

    rendered = repr(messages)
    assert "+639621170994" not in rendered
    assert "100 Test Street" not in rendered
    assert "******0994" in rendered


def _record_capture(monkeypatch):
    class CaptureCalls(list):
        artifacts = []

    calls = CaptureCalls()

    def capture(driver, stage, artifacts_dir, include_screenshot=True):
        calls.append((driver, stage, artifacts_dir, include_screenshot))
        artifacts = SimpleNamespace(
            screenshot=f"artifacts/{stage}.png" if include_screenshot else None,
            page_source=f"artifacts/{stage}.xml",
        )
        calls.artifacts.append(artifacts)
        return artifacts

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
    assert calls.artifacts[0].screenshot is None
    assert secret not in calls.artifacts[0].page_source
    assert secret not in calls[0][1]
    assert secret not in repr(logged[0][2:])


@pytest.mark.parametrize(
    ("stage", "secret"),
    [
        ("Checkout Pay_Password=123456/Retry", "123456"),
        ("Refresh Access_Token:abc/Retry", "abc"),
    ],
)
def test_composite_stage_secrets_are_absent_from_non_sensitive_artifact_paths(
    monkeypatch, stage, secret
):
    calls = _record_capture(monkeypatch)

    ShippingPage(FakeShippingDriver()).capture_shipping_failure(stage)

    assert calls.artifacts[0].screenshot is not None
    assert secret not in calls.artifacts[0].screenshot
    assert secret not in calls.artifacts[0].page_source
