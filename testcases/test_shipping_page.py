import re
from datetime import date
from types import SimpleNamespace

import pytest

import pages.shipping_address_mixin as shipping_address_mixin_module
import pages.shipping_page as shipping_page_module

from pages.shipping_page import ShippingPage
from pages.shipping_types import AddressData, AddressPolicy


class FakeElement:
    def __init__(
        self,
        driver,
        text="",
        on_click=None,
        *,
        enabled=True,
        clickable="true",
        content_desc="",
        attributes=None,
    ):
        self.driver = driver
        self.text = text
        self.on_click = on_click
        self.enabled = enabled
        self.clickable = clickable
        self.content_desc = content_desc
        self.attributes = attributes or {}

    def is_displayed(self):
        return True

    def is_enabled(self):
        return self.enabled

    def get_attribute(self, name):
        values = {
            "text": self.text,
            "content-desc": self.content_desc,
            "enabled": "true" if self.enabled else "false",
            "clickable": self.clickable,
        }
        return self.attributes.get(name, values.get(name, ""))

    def click(self):
        self.driver.clicks.append(self.text)
        if self.on_click:
            self.on_click()


class FakeShippingDriver:
    def __init__(self):
        self._page_source = ""
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
        self.delivery_slots = []
        self.delivery_date_controls = []
        self.delivery_time_controls = []
        self.delayed_time_controls = []
        self.time_slots_visible_after_checks = None
        self.time_slot_checks = 0
        self.unrelated_picker_elements = []
        self.pending_delivery_slot = ""
        self.checkout_delivery_text = ""
        self.confirm_available = True
        self.confirm_responsive = True
        self.auto_close_after_checks = None
        self.auto_close_checks = 0

    @property
    def page_source(self):
        if (
            self.screen == "delivery_picker"
            and self.pending_delivery_slot
            and self.auto_close_after_checks is not None
        ):
            self.auto_close_checks += 1
            if self.auto_close_checks >= self.auto_close_after_checks:
                self._confirm_delivery_slot()
        return self._page_source

    @page_source.setter
    def page_source(self, value):
        self._page_source = value

    @classmethod
    def with_delivery_dates(cls, labels, disabled_labels=(), time_ranges=()):
        driver = cls()
        driver.screen = "checkout"
        driver.page_source = "提交订单 预约配送"
        disabled = set(disabled_labels)
        for label in labels:
            element = FakeElement(
                driver,
                label,
                lambda selected=label: driver._select_delivery_slot(selected),
                enabled=label not in disabled,
                clickable="true" if label not in disabled else "false",
                attributes={
                    "class": "disabled" if label in disabled else "",
                    "resource-id": "shipping_delivery_slot",
                },
            )
            if cls._is_time_range(label):
                driver.delivery_time_controls.append(element)
            elif cls._is_combined_slot(label):
                driver.delivery_slots.append(element)
            else:
                driver.delivery_date_controls.append(element)
        driver.delivery_time_controls.extend(
            FakeElement(
                driver,
                label,
                lambda selected=label: driver._select_delivery_slot(selected),
                attributes={"resource-id": "shipping_delivery_slot"},
            )
            for label in time_ranges
        )
        return driver

    @classmethod
    def with_checkout_delivery_text(cls, label):
        driver = cls()
        driver.screen = "checkout"
        driver.checkout_delivery_text = label
        driver.page_source = f"提交订单 预约配送 {label}"
        return driver

    @staticmethod
    def _is_time_range(label):
        return bool(re.search(r"\d{2}:\d{2}\s*-\s*\d{2}:\d{2}", label)) and not any(
            marker in label for marker in ("今天", "明天", "后天", "月")
        )

    @classmethod
    def _is_combined_slot(cls, label):
        return cls._is_time_range(label) is False and bool(
            re.search(r"\d{2}:\d{2}\s*-\s*\d{2}:\d{2}", label)
        )

    @staticmethod
    def _text_selector(label):
        return f'//*[@text="{label}" or @content-desc="{label}"]'

    def find_elements(self, by, value):
        if self.screen == "checkout" and value == self._text_selector("预约配送"):
            return [FakeElement(self, "预约配送", self._show_delivery_picker)]
        if self.screen == "delivery_picker" and self.confirm_available and value in {
            self._text_selector("确定"),
            self._text_selector("确认"),
        }:
            action = self._confirm_delivery_slot if self.confirm_responsive else None
            return [FakeElement(self, "确定", action)]
        if self.screen == "delivery_picker" and value == "//*[@text or @content-desc]":
            return (
                self.unrelated_picker_elements
                + self.delivery_slots
                + self.delivery_date_controls
                + self.delivery_time_controls
            )
        if self.screen == "delivery_picker" and "resource-id" in value:
            time_controls = self.delivery_time_controls
            if self.pending_delivery_slot and self.delayed_time_controls:
                self.time_slot_checks += 1
                if self.time_slot_checks >= self.time_slots_visible_after_checks:
                    time_controls = time_controls + self.delayed_time_controls
            return self.delivery_slots + self.delivery_date_controls + time_controls
        if self.screen == "checkout" and "resource-id" in value and self.checkout_delivery_text:
            return [
                FakeElement(
                    self,
                    self.checkout_delivery_text,
                    attributes={"resource-id": "shipping_delivery_time"},
                )
            ]
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

    def _show_delivery_picker(self):
        self.screen = "delivery_picker"
        self.page_source = "选择配送时间 " + " ".join(
            slot.text
            for slot in (
                self.unrelated_picker_elements
                + self.delivery_slots
                + self.delivery_date_controls
                + self.delivery_time_controls
            )
        )

    def _select_delivery_slot(self, label):
        if self._is_time_range(label) and self.pending_delivery_slot:
            self.pending_delivery_slot = f"{self.pending_delivery_slot} {label}"
        else:
            self.pending_delivery_slot = label

    def _confirm_delivery_slot(self):
        self.screen = "checkout"
        self.checkout_delivery_text = self.pending_delivery_slot
        self.page_source = f"提交订单 预约配送 {self.checkout_delivery_text}"

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
        self.save_applies_directly = False
        self.address_searches = 0
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
        if self.save_applies_directly:
            self._select_address(address)
        else:
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
            self._text_selector("菲律宾"): FakeAddressElement(
                self,
                "菲律宾",
                lambda: self.address_form_values.__setitem__("country", "菲律宾"),
            ),
            self._text_selector("Manila"): FakeAddressElement(
                self,
                "Manila",
                lambda: self.address_form_values.__setitem__("city", "Manila"),
            ),
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
            self.address_searches += 1
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


def test_device_today_uses_appium_device_clock():
    driver = FakeShippingDriver()
    driver.get_device_time = lambda: "2026-08-10T21:30:00+08:00"

    assert ShippingPage(driver).device_today() == date(2026, 8, 10)


def test_device_today_fails_closed_when_clock_is_unavailable():
    driver = FakeShippingDriver()
    driver.get_device_time = lambda: (_ for _ in ()).throw(RuntimeError("offline"))

    with pytest.raises(AssertionError, match="无法读取设备日期"):
        ShippingPage(driver).device_today()


def test_delivery_picker_selects_earliest_future_not_today():
    driver = FakeShippingDriver.with_delivery_dates(
        ["今天 19:15-19:45", "8月12日 20:15-20:45", "明天 19:45-20:15"]
    )

    selected = ShippingPage(driver).select_earliest_future_delivery(today=date(2026, 8, 10))

    assert selected == date(2026, 8, 11)
    assert "明天 19:45-20:15" in driver.clicks
    assert "今天 19:15-19:45" not in driver.clicks


def test_delivery_picker_rejects_disabled_earlier_future_slot():
    driver = FakeShippingDriver.with_delivery_dates(
        ["明天 19:15-19:45", "后天 19:45-20:15"], disabled_labels={"明天 19:15-19:45"}
    )

    selected = ShippingPage(driver).select_earliest_future_delivery(today=date(2026, 8, 10))

    assert selected == date(2026, 8, 12)
    assert "后天 19:45-20:15" in driver.clicks
    assert "明天 19:15-19:45" not in driver.clicks


def test_delivery_picker_rejects_boolean_false_clickable_slot():
    driver = FakeShippingDriver.with_delivery_dates(
        ["明天 19:15-19:45", "后天 19:45-20:15"]
    )
    driver.delivery_slots[0].clickable = False

    selected = ShippingPage(driver).select_earliest_future_delivery(today=date(2026, 8, 10))

    assert selected == date(2026, 8, 12)
    assert "后天 19:45-20:15" in driver.clicks
    assert "明天 19:15-19:45" not in driver.clicks


def test_delivery_picker_ignores_unrelated_date_bearing_picker_control():
    driver = FakeShippingDriver.with_delivery_dates(["后天 19:45-20:15"])
    driver.unrelated_picker_elements = [
        FakeElement(
            driver,
            "明天 08:00-08:30",
            lambda: driver._select_delivery_slot("明天 08:00-08:30"),
            attributes={"resource-id": "calendar_event_date"},
        )
    ]

    selected = ShippingPage(driver).select_earliest_future_delivery(today=date(2026, 8, 10))

    assert selected == date(2026, 8, 12)
    assert "后天 19:45-20:15" in driver.clicks
    assert "明天 08:00-08:30" not in driver.clicks


def test_delivery_picker_rejects_visible_full_slot_marker():
    driver = FakeShippingDriver.with_delivery_dates(
        ["明天 已满 19:15-19:45", "后天 19:45-20:15"]
    )

    selected = ShippingPage(driver).select_earliest_future_delivery(today=date(2026, 8, 10))

    assert selected == date(2026, 8, 12)
    assert "后天 19:45-20:15" in driver.clicks
    assert "明天 已满 19:15-19:45" not in driver.clicks


def test_delivery_picker_selects_date_then_first_enabled_time_range():
    driver = FakeShippingDriver.with_delivery_dates(
        ["今天", "明天"], time_ranges=["19:15-19:45", "20:15-20:45"]
    )

    selected = ShippingPage(driver).select_earliest_future_delivery(today=date(2026, 8, 10))

    assert selected == date(2026, 8, 11)
    assert "明天" in driver.clicks
    assert "19:15-19:45" in driver.clicks


def test_delivery_picker_waits_for_time_range_after_date_selection():
    driver = FakeShippingDriver.with_delivery_dates(["明天"])
    driver.delayed_time_controls = [
        FakeElement(
            driver,
            "19:15-19:45",
            lambda: driver._select_delivery_slot("19:15-19:45"),
            attributes={"resource-id": "shipping_delivery_slot"},
        )
    ]
    driver.time_slots_visible_after_checks = 2

    selected = ShippingPage(driver).select_earliest_future_delivery(today=date(2026, 8, 10))

    assert selected == date(2026, 8, 11)
    assert "19:15-19:45" in driver.clicks
    assert driver.time_slot_checks >= 2


def test_delivery_picker_waits_for_delayed_auto_close_before_confirming():
    driver = FakeShippingDriver.with_delivery_dates(["明天 19:15-19:45"])
    driver.confirm_available = False
    driver.auto_close_after_checks = 3

    selected = ShippingPage(driver).select_earliest_future_delivery(today=date(2026, 8, 10))

    assert selected == date(2026, 8, 11)
    assert driver.screen == "checkout"
    assert driver.auto_close_checks >= 3


@pytest.mark.parametrize(
    ("confirm_available", "confirm_responsive"), [(False, True), (True, False)]
)
def test_delivery_picker_fails_without_a_confirmed_checkout_transition(
    confirm_available, confirm_responsive
):
    driver = FakeShippingDriver.with_delivery_dates(["明天 19:15-19:45"])
    driver.confirm_available = confirm_available
    driver.confirm_responsive = confirm_responsive

    with pytest.raises(AssertionError, match="确认|提交订单"):
        ShippingPage(driver).select_earliest_future_delivery(today=date(2026, 8, 10))


def test_delivery_readback_rejects_today_after_picker_click():
    driver = FakeShippingDriver.with_checkout_delivery_text("8月10日 19:15-19:45")

    with pytest.raises(AssertionError, match="严格晚于今天"):
        ShippingPage(driver).verify_selected_delivery_date(
            date(2026, 8, 10), date(2026, 8, 10)
        )


def test_delivery_readback_rejects_unparseable_text():
    driver = FakeShippingDriver.with_checkout_delivery_text("已预约")

    with pytest.raises(AssertionError, match="无法解析"):
        ShippingPage(driver).verify_selected_delivery_date(
            date(2026, 8, 11), date(2026, 8, 10)
        )


def test_delivery_readback_uses_checkout_field_instead_of_page_source():
    driver = FakeShippingDriver.with_checkout_delivery_text("明天 19:15-19:45")
    driver.page_source = "提交订单 预约配送 今天 09:00-09:30"

    assert ShippingPage(driver).verify_selected_delivery_date(
        date(2026, 8, 11), date(2026, 8, 10)
    ) is True


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


def test_public_add_rejects_incomplete_data_before_clicking_address_form():
    driver = FakeAddressShippingDriver()

    with pytest.raises(ValueError, match="phone,country,city,detail,postcode"):
        ShippingPage(driver).add_shipping_address(AddressData(name="Tester"))

    assert driver.clicks == []


def test_auto_verifies_an_address_saved_directly_to_checkout_without_reselecting():
    driver = FakeAddressShippingDriver.with_address_book(["Other +63******0000 Cebu"])
    driver.save_applies_directly = True

    assert ShippingPage(driver).ensure_shipping_address(AddressPolicy.AUTO, complete_address()) is True
    assert driver.selected_address.endswith("Manila 100 Test Street")
    assert driver.address_searches == 4


def test_address_form_failures_capture_sensitive_diagnostics(monkeypatch):
    driver = FakeAddressShippingDriver()
    page = ShippingPage(driver)
    calls = []
    monkeypatch.setattr(
        page,
        "capture_shipping_failure",
        lambda stage, sensitive=False, redact_values=(): calls.append(
            (stage, sensitive, redact_values)
        ),
    )

    with pytest.raises(AssertionError, match="未找到国家"):
        page.ensure_shipping_address(
            AddressPolicy.ADD, complete_address(country="不存在的国家")
        )

    assert calls == [
        (
            "shipping_address_country_missing",
            True,
            (
                "0994",
                "Tester",
                "+639621170994",
                "不存在的国家",
                "Manila",
                "100 Test Street",
                "1000",
            ),
        )
    ]


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

    def capture(driver, stage, artifacts_dir, include_screenshot=True, redact_values=()):
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
